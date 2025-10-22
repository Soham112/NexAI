#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Greenhouse-only scraper — salary-aware + fixed S3 paths

Outputs (local OR S3):
  links_all_all.jsonl      → links (url list)
  raw_all_all.jsonl        → raw (full html/text per job)
  extracted_all_all.jsonl  → extracted (structured summary incl. salary_*)

Write to S3 (fixed keys):
  s3://<bucket>/links/links_all_all.jsonl
  s3://<bucket>/raw/raw_all_all.jsonl
  s3://<bucket>/extracted/extracted_all_all.jsonl

Examples
--------
Local:
  python3 job_scrape.py --limit -1

S3:
  python3 job_scrape.py --limit -1 \
    --s3 --s3-bucket nexai-job-market-data --aws-region us-east-1
"""

import os
import re
import io
import json
import time
import argparse
import logging
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Iterable, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# =========================
# Config / HTTP session
# =========================
DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": DEFAULT_UA})

HERE = os.path.dirname(__file__)
OUTPUT_DIR = os.path.join(HERE, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# =========================
# Models
# =========================
@dataclass
class RawJob:
    url: str
    company: Optional[str]
    title: Optional[str]
    location: Optional[str]
    html: str
    text: str

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

@dataclass
class ExtractedJob:
    url: str
    company: Optional[str]
    title: Optional[str]
    location: Optional[str]
    work_mode: Optional[str] = None
    employment_type: Optional[str] = None
    skills: Optional[List[str]] = None
    responsibilities: Optional[List[str]] = None
    qualifications: Optional[List[str]] = None
    # Inferred seniority / sector (sector optional if you later map by company)
    experience_level: Optional[str] = None
    sector: Optional[str] = None
    # Location enrichment
    country: Optional[str] = None
    city_state: Optional[str] = None
    # Salary enrichment
    salary_min: Optional[int] = None   # numeric, e.g. 164000
    salary_max: Optional[int] = None
    salary_unit: Optional[str] = None  # 'year' | 'hour'
    salary_currency: Optional[str] = None  # 'USD', etc.

    def to_json(self) -> str:
        obj = asdict(self)
        for k in ("skills", "responsibilities", "qualifications"):
            if obj.get(k) is None:
                obj[k] = []
        return json.dumps(obj, ensure_ascii=False)

# =========================
# Helpers
# =========================
def fetch(url: str, retries: int = 3, backoff: float = 1.5) -> Optional[str]:
    for i in range(retries):
        try:
            r = SESSION.get(url, timeout=30)
            if r.status_code == 200 and r.text:
                return r.text
            if r.status_code in (403, 429):
                time.sleep(backoff * (i + 1))
        except Exception as e:
            logging.debug(f"Fetch error on {url}: {e}")
        time.sleep(backoff * (i + 1))
    return None

def soup_text(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    txt = soup.get_text("\n")
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in txt.splitlines()]
    return "\n".join([ln for ln in lines if ln])

def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()

# =========================
# Seniority inference (title-based)
# =========================
LEVEL_PATTERNS = [
    ("intern",   r"\b(intern|co-?op|apprentice(ship)?)\b"),
    ("entry",    r"\b(junior|jr\.?|new grad|newgrad|graduate)\b"),
    ("manager",  r"\b(manager|managing|lead|head of|director|vp|vice president)\b"),
    ("staff",    r"\b(staff|principal|distinguished|fellow)\b"),
    ("senior",   r"\b(senior|sr\.?)\b"),
    # default -> "mid"
]
LEVEL_RX = [(lbl, re.compile(rx, re.I)) for lbl, rx in LEVEL_PATTERNS]

def infer_level(title: str | None) -> str:
    t = (title or "").lower()
    if not t:
        return "unknown"
    for lbl, rx in LEVEL_RX:
        if rx.search(t):
            return lbl
    return "mid"

# =========================
# Location & country inference
# =========================
US_STATES = {
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS","KY","LA","ME","MD",
    "MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC",
    "SD","TN","TX","UT","VT","VA","WA","WV","WI","WY"
}
CITY_STATE_RE = re.compile(r"([A-Za-z .'&/-]+),\s*(%s)\b" % "|".join(US_STATES))
US_KEYWORDS_RE = re.compile(r"\b(united states|u\.s\.a|usa|u\.s\.|remote\s*[-–]?\s*us|remote\s+usa)\b", re.I)

def infer_country_and_citystate(location: Optional[str], text: str) -> Tuple[Optional[str], Optional[str]]:
    srcs = []
    if location:
        srcs.append(location)
    if text:
        head = "\n".join(text.split("\n")[:30])
        srcs.append(head)

    for s in srcs:
        s_low = s.lower()
        if US_KEYWORDS_RE.search(s_low):
            mrem = re.search(r"(remote\s*[-–]?\s*us[a]?)", s_low, re.I)
            return ("United States", "Remote - US" if mrem else None)
        m = CITY_STATE_RE.search(s)
        if m:
            return ("United States", f"{m.group(1).strip()}, {m.group(2)}")
        if ";" in s:
            parts = [p.strip() for p in s.split(";") if p.strip()]
            for p in parts:
                m2 = CITY_STATE_RE.search(p)
                if m2:
                    return ("United States", f"{m2.group(1).strip()}, {m2.group(2)}")
        if "united states" in s_low:
            return ("United States", None)
    return (None, None)

# =========================
# Salary parsing (robust, context-aware)
# =========================
SALARY_RANGE_RE = re.compile(
    r"""
    (?P<cur1>\$|US\$|USD)?\s*
    (?P<lo>\d[\d,]*\s*[kK]?)                 # low number
    \s*(?:-|–|—|\bto\b)\s*                   # separator
    (?P<cur2>\$|US\$|USD)?\s*
    (?P<hi>\d[\d,]*\s*[kK]?)                 # high number
    (?:\s*(?:per|/)?\s*(?P<unit>\byears?\b|yr|year|annual|annum|hour|hr))?
    """,
    re.I | re.X,
)

SALARY_SINGLE_RE = re.compile(
    r"""
    (?P<cur>\$|US\$|USD)?\s*
    (?P<val>\d[\d,]*\s*[kK]?)                 # single number
    (?:\s*(?:per|/)?\s*(?P<unit>\byears?\b|yr|year|annual|annum|hour|hr))    # with unit
    """,
    re.I | re.X,
)

CURRENCY_WORD_RE = re.compile(r"\b(USD|US\$|CAD|EUR|GBP|AUD)\b", re.I)

def _sal_to_number(num_str: str) -> Optional[int]:
    if not num_str:
        return None
    s = num_str.strip().lower().replace(",", "")
    if s.endswith("k"):
        s = s[:-1]
        try:
            return int(float(s) * 1000)
        except Exception:
            return None
    try:
        return int(float(s))
    except Exception:
        return None

def _sal_norm_unit(u: Optional[str]) -> Optional[str]:
    if not u:
        return None
    u = u.lower()
    if u in ("hour", "hr"):
        return "hour"
    if u.startswith("year") or u.startswith("yr") or u in ("annual", "annum"):
        return "year"
    return None

def _pick_currency(full_text: str, groups: list[str]) -> Optional[str]:
    txt = full_text or ""
    m = CURRENCY_WORD_RE.search(txt)
    if m:
        token = m.group(1).upper()
        if token in ("US$", "USD"):
            return "USD"
        return token
    if "$" in txt:
        return "USD"
    for g in groups:
        if not g:
            continue
        g2 = g.upper()
        if g2 in ("$", "US$", "USD"):
            return "USD"
    return None

def _is_money_context(text: str, mstart: int, mend: int) -> bool:
    lo = max(0, mstart - 40)
    hi = min(len(text), mend + 40)
    ctx = text[lo:hi].lower()
    if "$" in ctx or "usd" in ctx:
        return True
    for kw in ("salary", "compensation", "base pay", "base salary", "pay range", "annual"):
        if kw in ctx:
            return True
    return False

def _reject_bad_context(text: str, mstart: int, mend: int) -> bool:
    lo = max(0, mstart - 30)
    hi = min(len(text), mend + 30)
    ctx = text[lo:hi].lower()
    if any(k in ctx for k in ("experience", "experiences", "yrs", "years")) and not _is_money_context(text, mstart, mend):
        return True
    if "%" in ctx and not _is_money_context(text, mstart, mend):
        return True
    return False

def parse_salary(text: str) -> tuple[Optional[int], Optional[int], Optional[str], Optional[str]]:
    if not text:
        return (None, None, None, None)

    lows, highs, units, cur_groups = [], [], set(), []

    # Range matches
    for m in SALARY_RANGE_RE.finditer(text):
        lo = _sal_to_number(m.group("lo"))
        hi = _sal_to_number(m.group("hi"))
        unit = _sal_norm_unit(m.group("unit"))
        if lo is None and hi is None:
            continue
        if _reject_bad_context(text, m.start(), m.end()):
            continue
        money_ctx = _is_money_context(text, m.start(), m.end())
        if unit == "year":
            if max(x for x in (lo or 0, hi or 0)) < 1000 and not money_ctx:
                continue
        elif unit == "hour":
            if any(x is not None and (x < 8 or x > 5000) for x in (lo, hi)) and not money_ctx:
                continue
        else:
            if not money_ctx and max(x for x in (lo or 0, hi or 0)) < 1000:
                continue
        if lo is not None: lows.append(lo)
        if hi is not None: highs.append(hi)
        units.add(unit or ("year" if money_ctx else None))
        cur_groups.extend([m.group("cur1") or "", m.group("cur2") or ""])

    # Fallback: single value w/ unit
    if not lows and not highs:
        for m in SALARY_SINGLE_RE.finditer(text):
            val = _sal_to_number(m.group("val"))
            unit = _sal_norm_unit(m.group("unit"))
            if val is None:
                continue
            if _reject_bad_context(text, m.start(), m.end()):
                continue
            money_ctx = _is_money_context(text, m.start(), m.end())
            if unit == "year":
                if val < 1000 and not money_ctx:
                    continue
            elif unit == "hour":
                if (val < 8 or val > 5000) and not money_ctx:
                    continue
            else:
                if not money_ctx and val < 1000:
                    continue
            lows.append(val); highs.append(val); units.add(unit or ("year" if money_ctx else None))
            cur_groups.append(m.group("cur") or "")
            break

    if not lows and not highs:
        return (None, None, None, _pick_currency(text, cur_groups))

    agg_min = min(lows) if lows else None
    agg_max = max(highs) if highs else (max(lows) if lows else None)
    unit_final = "year" if "year" in units else ("hour" if "hour" in units else None)
    currency = _pick_currency(text, cur_groups)
    return (agg_min, agg_max, unit_final, currency)

# =========================
# Greenhouse scraper
# =========================
class GreenhouseScraper:
    BASES = [
        "https://boards.greenhouse.io/",
        "https://job-boards.greenhouse.io/",
    ]

    def resolve_board(self, company: str) -> Tuple[Optional[str], Optional[str]]:
        comp = company.lower().strip()
        for base in self.BASES:
            url = urljoin(base, comp)
            html = fetch(url)
            if html:
                return url, html
        return None, None

    def extract_links_from_board(self, html: str, board_url: str) -> List[str]:
        soup = BeautifulSoup(html, "html.parser")
        links: List[str] = []
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href:
                continue
            if re.search(r"(/job|/jobs/|gh_jid=|embed/job_app)", href):
                links.append(urljoin(board_url, href))
        out, seen = [], set()
        for u in links:
            if "greenhouse.io" not in u:
                continue
            if u not in seen:
                seen.add(u)
                out.append(u)
        return out

    def _title_matches(self, soup: BeautifulSoup, role: str) -> bool:
        title_el = soup.find(["h1", "h2"]) or soup.find("title")
        title_txt = (title_el.get_text(" ", strip=True).lower() if title_el else "")
        return all(tok in title_txt for tok in role.lower().split())

    def _location_text(self, soup: BeautifulSoup) -> str:
        for cand in soup.select(".location, .posting-categories, [data-company-location], .app-title"):
            txt = cand.get_text(" ", strip=True)
            if txt:
                return txt
        return ""

    def filter_links(self, links: Iterable[str], role: str, city: Optional[str], strict: bool) -> List[str]:
        role_all = not role or role.strip().lower() == "all"
        out: List[str] = []
        city_q = (city or "").lower()
        for url in links:
            html = fetch(url)
            if not html:
                continue
            soup = BeautifulSoup(html, "html.parser")

            if not role_all and not self._title_matches(soup, role):
                continue

            if city:
                loc = self._location_text(soup).lower()
                if strict:
                    if city_q not in loc:
                        continue
                else:
                    if city_q and city_q.split(",")[0] not in loc:
                        continue

            out.append(url)
            time.sleep(0.2)
        return out

    def get_all_job_urls(self, role: str, city: Optional[str], strict: bool,
                         companies: List[str], limit: int) -> List[str]:
        urls: List[str] = []
        for comp in companies:
            board_url, html = self.resolve_board(comp)
            if not html:
                logging.info(f"No board found for {comp}")
                continue
            raw_links = self.extract_links_from_board(html, board_url)
            flinks = self.filter_links(raw_links, role, city, strict)
            urls.extend(flinks)
            logging.info(f"{comp}: {len(flinks)} matches")
            if limit > 0 and len(urls) >= limit:
                break
            time.sleep(0.6)
        seen, dedup = set(), []
        for u in urls:
            if u not in seen:
                seen.add(u)
                dedup.append(u)
        return dedup if limit <= 0 else dedup[:limit]

    def parse_job(self, url: str) -> Optional[RawJob]:
        html = fetch(url)
        if not html:
            return None
        soup = BeautifulSoup(html, "html.parser")
        title_el = soup.find("h1") or soup.find("h2")
        title = title_el.get_text(strip=True) if title_el else None

        company = None
        og = soup.find("meta", attrs={"property": "og:site_name"})
        if og and og.get("content"):
            company = og["content"].strip() or None
        if not company:
            path = urlparse(url).path.strip("/").split("/")
            company = path[0] if path else None

        location = None
        loc_el = soup.select_one(".location, .posting-categories, [data-company-location]")
        if loc_el:
            location = loc_el.get_text(" ", strip=True)
        if not location:
            header = soup.select_one(".app-title, .opening, .opening-header, .opening-title")
            if header:
                maybe_loc = _norm(header.get_text(" ", strip=True))
                if ";" in maybe_loc or "," in maybe_loc:
                    location = maybe_loc

        text = soup_text(soup)
        return RawJob(url=url, company=company, title=title, location=location, html=html, text=text)

# =========================
# Storage backends
# =========================
class LocalStorage:
    def __init__(self, out_dir: str = OUTPUT_DIR):
        self.out_dir = out_dir
        os.makedirs(self.out_dir, exist_ok=True)

    def write_links(self, links: Dict[str, List[str]], role: str, city: str) -> str:
        path = os.path.join(self.out_dir, "links_all_all.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            for source, urls in links.items():
                for u in urls:
                    f.write(json.dumps({"source": source, "url": u}, ensure_ascii=False) + "\n")
        return path

    def write_raw(self, jobs: List["RawJob"], role: str, city: str) -> str:
        path = os.path.join(self.out_dir, "raw_all_all.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            for j in jobs:
                f.write(j.to_json() + "\n")
        return path

    def write_extracted(self, jobs: List["ExtractedJob"], role: str, city: str) -> str:
        path = os.path.join(self.out_dir, "extracted_all_all.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            for j in jobs:
                f.write(j.to_json() + "\n")
        return path


class S3Storage:
    """
    Write JSONL files to fixed keys:
      links/links_all_all.jsonl
      raw/raw_all_all.jsonl
      extracted/extracted_all_all.jsonl
    """
    def __init__(self, bucket: str, region: str | None = None):
        try:
            import boto3
        except ImportError:
            raise SystemExit("boto3 is required for S3 mode. Install with: pip install boto3")
        self.bucket = bucket
        self.s3 = boto3.client("s3", region_name=region)

    def _put_lines(self, key: str, lines_iter) -> str:
        buf = io.StringIO()
        for line in lines_iter:
            buf.write(line)
            if not line.endswith("\n"):
                buf.write("\n")
        body = buf.getvalue().encode("utf-8")
        self.s3.put_object(Bucket=self.bucket, Key=key, Body=body)
        return f"s3://{self.bucket}/{key}"

    def write_links(self, links: Dict[str, List[str]], role: str, city: str) -> str:
        key = "links/links_all_all.jsonl"
        def gen():
            for source, urls in links.items():
                for u in urls:
                    yield json.dumps({"source": source, "url": u}, ensure_ascii=False)
        return self._put_lines(key, gen())

    def write_raw(self, jobs: List["RawJob"], role: str, city: str) -> str:
        key = "raw/raw_all_all.jsonl"
        def gen():
            for j in jobs:
                yield j.to_json()
        return self._put_lines(key, gen())

    def write_extracted(self, jobs: List["ExtractedJob"], role: str, city: str) -> str:
        key = "extracted/extracted_all_all.jsonl"
        def gen():
            for j in jobs:
                yield j.to_json()
        return self._put_lines(key, gen())

# =========================
# Extraction (HTML-aware) + salary/location
# =========================
RESP_HDRS = [
    "responsibilities", "what you'll do", "what you will do",
    "in this role", "your impact", "what you’ll do"
]
QUAL_HDRS = [
    "qualifications", "requirements", "what you'll bring",
    "who you are", "about you", "what we’re looking for", "what we're looking for"
]
BENEFITS_HDRS = ["benefits", "perks", "what we offer"]
ALL_SECTION_HDRS = set([*RESP_HDRS, *QUAL_HDRS, *BENEFITS_HDRS])

def _is_section_header(text: str, header_aliases) -> bool:
    t = _norm(text).lower()
    return any(t == h for h in (a.lower() for a in header_aliases))

def _looks_like_header(text: str) -> bool:
    t = _norm(text)
    if not t or len(t) > 120:
        return False
    if re.search(r"[.:;]$", t):
        return False
    words = t.split()
    capsish = sum(1 for w in words if re.match(r"^[A-Z][A-Za-z'&/+-]*$", w) or w.isupper())
    return capsish >= max(2, len(words) // 2)

def _collect_until_next_header(start_node, stop_headers_lower) -> list[str]:
    out: list[str] = []
    node = start_node
    while node:
        node = node.next_sibling
        if not node:
            break
        if getattr(node, "name", None):
            if node.name in ("h1", "h2", "h3", "h4"):
                t = _norm(node.get_text(" ", strip=True)).lower()
                if t in stop_headers_lower or _looks_like_header(t):
                    break
            for li in node.find_all("li"):
                txt = _norm(li.get_text(" ", strip=True))
                if txt:
                    out.append(txt)
            if not node.find_all("li"):
                for p in node.find_all(["p", "div"]):
                    txt = _norm(p.get_text(" ", strip=True))
                    if txt and len(txt) <= 300:
                        out.append(txt)
    seen, dedup = set(), []
    for x in out:
        if x not in seen:
            seen.add(x)
            dedup.append(x)
    return dedup

def extract_section_from_html(html: str, header_aliases: list[str]) -> list[str] | None:
    soup = BeautifulSoup(html, "html.parser")
    stop_lower = {h.lower() for h in ALL_SECTION_HDRS}
    for h in soup.find_all(["h2", "h3", "h4"]):
        if _is_section_header(h.get_text(" ", strip=True), header_aliases):
            items = _collect_until_next_header(h, stop_lower)
            if items:
                return items

    for h in soup.find_all(["h2", "h3", "h4"]):
        t = _norm(h.get_text(" ", strip=True)).lower()
        if any(a.lower() in t for a in header_aliases):
            items = _collect_until_next_header(h, stop_lower)
            if items:
                return items

    # Fallback: plain-text with safe stops
    soup2 = BeautifulSoup(html, "html.parser")
    text = soup_text(soup2)
    header_re = re.compile(r"^(?:" + "|".join([re.escape(h) for h in header_aliases]) + r")[\s:]*$", re.I)

    out, capturing = [], False
    for ln in text.split("\n"):
        ls = _norm(ln)
        if not ls:
            continue
        if header_re.match(ls):
            capturing = True
            continue
        if capturing:
            low = ls.lower()
            if any(low == h for h in (hh.lower() for hh in ALL_SECTION_HDRS)) or \
               any(h in low for h in (hh.lower() for hh in ALL_SECTION_HDRS)):
                break
            parts = re.split(r"\s*[•\-\u2022\*]\s+", ls)
            if len(parts) > 1:
                for p in parts:
                    p = p.strip(" -•\t")
                    if p:
                        out.append(p)
            else:
                if 3 <= len(ls) <= 300:
                    out.append(ls)

    seen, dedup = set(), []
    for x in out:
        if x not in seen:
            seen.add(x)
            dedup.append(x)
    return dedup or None

def heuristic_extract(r: RawJob) -> ExtractedJob:
    txt_low = r.text.lower()
    work_mode = (
        "Remote" if " remote" in txt_low
        else ("Hybrid" if "hybrid" in txt_low
        else ("On-site" if r.location else None))
    )
    emp_type = None
    m = re.search(r"(full[- ]?time|part[- ]?time|contract|internship)", txt_low)
    if m:
        emp_type = m.group(1).title()

    responsibilities = extract_section_from_html(r.html, RESP_HDRS) or []
    qualifications  = extract_section_from_html(r.html, QUAL_HDRS) or []
    _ = extract_section_from_html(r.html, BENEFITS_HDRS)

    skills = None
    ms = re.search(r"skills?[:\-]\s*([A-Za-z0-9,\./ +#\-]{8,300})", r.text, re.I)
    if ms:
        skills = [s.strip()] if (s := ms.group(1)) else None

    level = infer_level(r.title)
    country, city_state = infer_country_and_citystate(r.location, r.text)

    sal_min, sal_max, sal_unit, sal_cur = parse_salary(r.text)

    return ExtractedJob(
        url=r.url,
        company=r.company,
        title=r.title,
        location=r.location,
        work_mode=work_mode,
        employment_type=emp_type,
        responsibilities=responsibilities or None,
        qualifications=qualifications or None,
        skills=skills,
        experience_level=level,
        sector=None,
        country=country,
        city_state=city_state,
        salary_min=sal_min,
        salary_max=sal_max,
        salary_unit=sal_unit,
        salary_currency=sal_cur,
    )

# =========================
# CLI
# =========================
def main():
    ap = argparse.ArgumentParser(description="Greenhouse-only scraper (role/location optional)")
    ap.add_argument("--role", default="all", help="Role keywords (use 'all' to skip title filtering)")
    ap.add_argument("--city", default="all", help="City text to match, or 'all' (skipped by default)")
    ap.add_argument("--strict-location", action="store_true", help="Exact city substring match (if --city provided)")
    ap.add_argument("--limit", type=int, default=-1, help="Max URLs to fetch overall (<=0 = unlimited)")
    ap.add_argument("--log", default="INFO")

    # S3 options
    ap.add_argument("--s3", action="store_true", help="Write outputs to S3 instead of local disk")
    ap.add_argument("--s3-bucket", default="nexai-job-market-data", help="Target S3 bucket name")
    ap.add_argument("--aws-region", default="us-east-1", help="AWS region for S3 client")

    args = ap.parse_args()
    logging.basicConfig(level=getattr(logging, args.log.upper(), logging.INFO), format="%(levelname)s: %(message)s")

    # Storage
    if args.s3:
        store = S3Storage(bucket=args.s3_bucket, region=args.aws_region)
        print(f"🪣 Using S3 storage → s3://{args.s3_bucket}/(links|raw|extracted)/...")
    else:
        store = LocalStorage()
        print(f"💾 Using local storage → {OUTPUT_DIR}/")

    # --- Scrape list of companies (Greenhouse boards) ---
    # If you want to limit to your YAML list, you can hardcode or load it here.
    # For now, we’ll infer companies from live pages you feed via BASES.
    # Typically, you'd maintain a list; here’s a tiny sample to prove flow:
    companies = [
        # Add/replace with your slugs (from companies.yaml if you prefer to load it)
        "figma", "gitlab","robinhood","airtable","affirm","carta","checkr","earnin","gusto","mercury","buildkite","airbyte",
        "anthropic","honehealth","springhealth66","vivian","stellarhealth","quince","mejuri","doordashusa","aninebing",
        "coursera","degreed","cc","aircompany","weee","acommerce","bringg","oliverusa","6sense","demandbase","amplitude",
        "dovetail","clutch","automatticcareers","netdocuments","xai","ethoslife","pieinsurance","constrafor","apeel",
        "agoda","blockchain","fireblocks","algolia"
    ]

    role = args.role.strip() if args.role else "all"
    city = None if (args.city or "all").lower() == "all" else args.city.strip()

    gh = GreenhouseScraper()

    print("\n" + "=" * 78)
    print("GREENHOUSE SCRAPER — ROLE AGNOSTIC")
    print("=" * 78)
    print(f"\n[1/4] Scanning {len(companies)} Greenhouse boards…")

    urls: List[str] = []
    for comp in companies:
        board_url, html = gh.resolve_board(comp)
        if not html:
            logging.info(f"No board found for {comp}")
            continue
        raw_links = gh.extract_links_from_board(html, board_url)
        flinks = gh.filter_links(raw_links, role, city, args.strict_location)
        urls.extend(flinks)
        logging.info(f"{comp}: {len(flinks)} matches")
        if args.limit > 0 and len(urls) >= args.limit:
            break
        time.sleep(0.4)

    # de-dup and apply limit
    seen, dedup = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u)
            dedup.append(u)
    if args.limit > 0:
        dedup = dedup[:args.limit]

    links = {"greenhouse": dedup}
    print(f"   → {len(dedup)} URLs matched")
    links_path = store.write_links(links, role or "all", city or "all")
    print(f"   saved: {links_path}")

    if not dedup:
        print("No matches. Exiting.")
        return

    # [2/4] Raw scrape
    print(f"\n[2/4] Downloading {len(dedup)} postings…")
    raw: List[RawJob] = []
    for i, u in enumerate(dedup, 1):
        rj = gh.parse_job(u)
        if rj:
            raw.append(rj)
            print(f"   [{i}/{len(dedup)}] ✓ {rj.company or 'Unknown'} | {rj.title or 'Untitled'}")
        time.sleep(0.25)
    raw_path = store.write_raw(raw, role or "all", city or "all")
    print(f"   saved: {raw_path}")

    # [3/4] Extract
    print(f"\n[3/4] Extracting lightweight structure…")
    extracted = [heuristic_extract(r) for r in raw]

    # [4/4] Write extracted
    print(f"\n[4/4] Writing JSON…")
    out_path = store.write_extracted(extracted, role or "all", city or "all")
    print(f"   saved: {out_path}")

    print("\n" + "=" * 78)
    print("DONE")
    print("=" * 78)
    print(f"Links:     {links_path}")
    print(f"Raw HTML:  {raw_path}")
    print(f"Extracted: {out_path}")

if __name__ == "__main__":
    main()
