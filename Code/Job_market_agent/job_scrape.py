#!/usr/bin/env python3
"""
Greenhouse-only scraper — role/location optional

Adds:
• experience_level (intern/entry/mid/senior/staff/manager/unknown) — inferred from title
• sector (category from config/companies.yaml)
• country + city_state — inferred from location/text
• salary_* (min/max/unit/currency) — parsed from raw text
• --us-only flag to keep only U.S. postings
• --enrich-existing to backfill fields into an existing extracted_*.jsonl using raw_*.jsonl
• OPTIONAL S3 storage: --s3, --s3-bucket, --s3-prefix, --aws-region

Run:
  python3 job_scrape.py --role all
  python3 job_scrape.py --role "Data Scientist" --us-only

S3 example:
  python3 job_scrape.py --role all --us-only \
    --s3 --s3-bucket nexai-job-market-data --s3-prefix job_market --aws-region us-east-1

Backfill existing outputs:
  python3 job_scrape.py --enrich-existing \
      --raw output/raw_all_all.jsonl \
      --extracted output/extracted_all_all.jsonl \
      --out output/enriched_extracted_all_all.jsonl
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
from datetime import datetime

import requests
from bs4 import BeautifulSoup

# --- inline YAML loader for companies & sectors ---
try:
    import yaml  # pip install pyyaml
except ImportError:
    raise SystemExit("PyYAML is required. Install with: pip install pyyaml")

def _flatten(x):
    if isinstance(x, dict):
        for v in x.values(): yield from _flatten(v)
    elif isinstance(x, list):
        for i in x: yield from _flatten(i)
    elif x is not None:
        yield str(x)

def load_greenhouse_companies(path: str | None = None) -> List[str]:
    here = os.path.dirname(__file__)
    if path is None:
        path = os.path.join(here, "config", "companies.yaml")
    if not os.path.exists(path):
        raise FileNotFoundError(f"companies.yaml not found at {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    companies = sorted({s.strip().lower() for s in _flatten(data) if str(s).strip()})
    print(f"✅ Loaded {len(companies)} companies from {os.path.relpath(path, here)}")
    return companies

def load_company_sectors(path: str | None = None) -> dict[str, str]:
    """Return { 'airtable': 'Major_Tech', ... } from companies.yaml categories."""
    here = os.path.dirname(__file__)
    if path is None:
        path = os.path.join(here, "config", "companies.yaml")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    sector_by_company: dict[str, str] = {}
    if isinstance(data, dict):
        for sector, arr in data.items():
            if not isinstance(arr, list): continue
            for name in arr:
                slug = str(name).strip().lower()
                if slug:
                    sector_by_company.setdefault(slug, str(sector))
    return sector_by_company
# --- end loader ---

# =========================
# Config
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

def _now_date_str():
    return datetime.utcnow().strftime("%Y-%m-%d")

def _join_s3_key(*parts: str) -> str:
    parts2 = [p.strip("/").replace("\\", "/") for p in parts if p and p.strip("/")]
    return "/".join(parts2)

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
    # NEW:
    experience_level: Optional[str] = None
    sector: Optional[str] = None
    # NEW location enrichment:
    country: Optional[str] = None
    city_state: Optional[str] = None
    # NEW salary enrichment:
    salary_min: Optional[int] = None   # in currency units
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
    """
    Return (country, city_state) using location first, then text fallback.
    """
    srcs = []
    if location:
        srcs.append(location)
    if text:
        head = "\n".join(text.split("\n")[:30])
        srcs.append(head)

    for s in srcs:
        s_low = s.lower()
        # direct US phrases
        if US_KEYWORDS_RE.search(s_low):
            mrem = re.search(r"(remote\s*[-–]?\s*us[a]?)", s_low, re.I)
            return ("United States", "Remote - US" if mrem else None)
        # city, ST capture
        m = CITY_STATE_RE.search(s)
        if m:
            return ("United States", f"{m.group(1).strip()}, {m.group(2)}")

        # lists like: "San Francisco, CA; New York City, NY; Austin, TX"
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
# Salary parsing
# =========================
SALARY_BLOCK_RE = re.compile(
    r"(?:\$|usd\s*)?\s*([0-9][0-9,]*\s*[kK]?)\s*(?:[-–—to]{1,3}\s*(?:\$|usd\s*)?\s*([0-9][0-9,]*\s*[kK]?))?"
    r"(?:\s*(?:per|/)?\s*(year|yr|annual|annum|hour|hr))?",
    re.I
)
CURRENCY_RE = re.compile(r"\b(usd|cad|eur|gbp|aud)\b", re.I)

def _to_number(num_str: str) -> Optional[int]:
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

def parse_salary(text: str) -> Tuple[Optional[int], Optional[int], Optional[str], Optional[str]]:
    """
    Returns (min, max, unit, currency)
    unit ∈ {'year','hour'} ; currency defaults to 'USD' if $ present and no other found
    """
    if not text:
        return (None, None, None, None)

    currency = None
    if "$" in text:
        currency = "USD"
    mcur = CURRENCY_RE.search(text)
    if mcur:
        cur = mcur.group(1).upper()
        currency = {"USD":"USD","CAD":"CAD","EUR":"EUR","GBP":"GBP","AUD":"AUD"}.get(cur, currency or cur)

    for m in SALARY_BLOCK_RE.finditer(text):
        lo_raw, hi_raw, unit_raw = m.group(1), m.group(2), m.group(3)
        lo = _to_number(lo_raw)
        hi = _to_number(hi_raw) if hi_raw else None
        if not lo and not hi:
            continue
        unit = None
        if unit_raw:
            unit_raw = unit_raw.lower()
            if "hour" in unit_raw or "hr" in unit_raw:
                unit = "hour"
            else:
                unit = "year"
        if not unit:
            unit = "year" if (hi or lo or 0) >= 50000 else "hour"
        return (lo, hi, unit, currency)
    return (None, None, None, currency)

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
            if len(urls) >= limit:
                break
            time.sleep(0.6)
        seen, dedup = set(), []
        for u in urls:
            if u not in seen:
                seen.add(u)
                dedup.append(u)
        return dedup[:limit]

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

    def _slug(self, s: str) -> str:
        return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")

    def paths(self, role: str, city: str) -> Dict[str, str]:
        r, c = self._slug(role or "all"), self._slug(city or "all")
        return {
            "links": os.path.join(self.out_dir, f"links_{r}_{c}.jsonl"),
            "raw": os.path.join(self.out_dir, f"raw_{r}_{c}.jsonl"),
            "extracted": os.path.join(self.out_dir, f"extracted_{r}_{c}.jsonl"),
        }

    def write_links(self, links: Dict[str, List[str]], role: str, city: str) -> str:
        p = self.paths(role, city)["links"]
        with open(p, "w", encoding="utf-8") as f:
            for k, urls in links.items():
                for u in urls:
                    f.write(json.dumps({"source": k, "url": u}) + "\n")
        return p

    def write_raw(self, jobs: List[RawJob], role: str, city: str) -> str:
        p = self.paths(role, city)["raw"]
        with open(p, "w", encoding="utf-8") as f:
            for j in jobs:
                f.write(j.to_json() + "\n")
        return p

    def write_extracted(self, jobs: List["ExtractedJob"], role: str, city: str) -> str:
        p = self.paths(role, city)["extracted"]
        with open(p, "w", encoding="utf-8") as f:
            for j in jobs:
                f.write(j.to_json() + "\n")
        return p

class S3Storage:
    """Write JSONL outputs to S3 with date-based prefix."""
    def __init__(self, bucket: str, prefix: str = "job_market", region: str | None = None):
        try:
            import boto3  # pip install boto3
        except ImportError:
            raise SystemExit("boto3 is required for S3 mode. Install with: pip install boto3")
        self.bucket = bucket
        # e.g. job_market/2025-10-21/
        self.prefix = _join_s3_key(prefix, _now_date_str())
        self.s3 = boto3.client("s3", region_name=region)

    def _slug(self, s: str) -> str:
        return re.sub(r"[^a-z0-9]+", "_", (s or "all").lower()).strip("_")

    def paths(self, role: str, city: str) -> Dict[str, str]:
        r, c = self._slug(role), self._slug(city)
        return {
            "links": _join_s3_key(self.prefix, f"links_{r}_{c}.jsonl"),
            "raw": _join_s3_key(self.prefix, f"raw_{r}_{c}.jsonl"),
            "extracted": _join_s3_key(self.prefix, f"extracted_{r}_{c}.jsonl"),
        }

    def _put_lines(self, key: str, lines_iter):
        buf = io.StringIO()
        for line in lines_iter:
            buf.write(line)
            if not line.endswith("\n"):
                buf.write("\n")
        body = buf.getvalue().encode("utf-8")
        self.s3.put_object(Bucket=self.bucket, Key=key, Body=body)
        return f"s3://{self.bucket}/{key}"

    def write_links(self, links: Dict[str, List[str]], role: str, city: str) -> str:
        paths = self.paths(role, city)
        def gen():
            for source, urls in links.items():
                for u in urls:
                    yield json.dumps({"source": source, "url": u}, ensure_ascii=False)
        return self._put_lines(paths["links"], gen())

    def write_raw(self, jobs: List["RawJob"], role: str, city: str) -> str:
        paths = self.paths(role, city)
        def gen():
            for j in jobs:
                yield j.to_json()
        return self._put_lines(paths["raw"], gen())

    def write_extracted(self, jobs: List["ExtractedJob"], role: str, city: str) -> str:
        paths = self.paths(role, city)
        def gen():
            for j in jobs:
                yield j.to_json()
        return self._put_lines(paths["extracted"], gen())

# =========================
# Heuristic extractor (HTML-aware) + location/salary
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

    # Fallback: text-mode with safer stops
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

    # skills (simple)
    skills = None
    ms = re.search(r"skills?[:\-]\s*([A-Za-z0-9,\./ +#\-]{8,300})", r.text, re.I)
    if ms:
        skills = [s.strip() for s in ms.group(1).split(",") if s.strip()][:30]

    # level
    level = infer_level(r.title)

    # location enrichment
    country, city_state = infer_country_and_citystate(r.location, r.text)

    # salary parsing from raw text
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
        sector=None,  # filled in main() via sector map
        country=country,
        city_state=city_state,
        salary_min=sal_min,
        salary_max=sal_max,
        salary_unit=sal_unit,
        salary_currency=sal_cur,
    )

# =========================
# Enrichment helpers (for existing files)
# =========================
def _load_raw_by_url(raw_path: str) -> dict:
    by = {}
    with open(raw_path, encoding="utf-8") as f:
        for line in f:
            try:
                rec = json.loads(line)
            except Exception:
                continue
            url = rec.get("url")
            if url:
                by[url] = rec
    return by

def enrich_existing(raw_path: str, extracted_path: str, companies_yaml: str | None, out_path: str | None) -> str:
    sector_map = load_company_sectors(companies_yaml)
    raw_by_url = _load_raw_by_url(raw_path)
    out_path = out_path or os.path.join(
        os.path.dirname(extracted_path), "enriched_" + os.path.basename(extracted_path)
    )
    count = 0
    with open(extracted_path, encoding="utf-8") as fin, open(out_path, "w", encoding="utf-8") as fout:
        for line in fin:
            try:
                rec = json.loads(line)
            except Exception:
                continue

            raw_rec = raw_by_url.get(rec.get("url"), {})
            title = rec.get("title") or raw_rec.get("title")
            text = raw_rec.get("text") or ""
            location = rec.get("location") or raw_rec.get("location")

            # level
            rec["experience_level"] = rec.get("experience_level") or infer_level(title)

            # sector
            comp = (rec.get("company") or "").lower()
            if comp in sector_map:
                rec["sector"] = sector_map[comp]

            # location enrichment
            if not rec.get("country") or not rec.get("city_state"):
                country, city_state = infer_country_and_citystate(location, text)
                if country: rec["country"] = country
                if city_state: rec["city_state"] = city_state

            # salary enrichment
            if not any(rec.get(k) for k in ("salary_min","salary_max","salary_unit","salary_currency")):
                sal_min, sal_max, sal_unit, sal_cur = parse_salary(text)
                if sal_min is not None: rec["salary_min"] = sal_min
                if sal_max is not None: rec["salary_max"] = sal_max
                if sal_unit: rec["salary_unit"] = sal_unit
                if sal_cur: rec["salary_currency"] = sal_cur

            fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
            count += 1
    print(f"✅ Enriched {count} records → {out_path}")
    return out_path

# =========================
# CLI
# =========================
def main():
    ap = argparse.ArgumentParser(description="Greenhouse-only scraper (role/location optional)")
    ap.add_argument("--role", default="all", help="Role keywords (use 'all' to skip title filtering)")
    ap.add_argument("--city", default="all", help="City text to match, or 'all' (skipped by default)")
    ap.add_argument("--strict-location", action="store_true", help="Exact city substring match (if --city provided)")
    ap.add_argument("--limit", type=int, default=-1, help="Max URLs to fetch overall")
    ap.add_argument("--log", default="INFO")
    ap.add_argument("--companies-yaml", default=None, help="Path to config/companies.yaml (optional)")
    ap.add_argument("--us-only", action="store_true", help="Filter to United States jobs only")

    # Enrichment mode
    ap.add_argument("--enrich-existing", action="store_true", help="Backfill new fields into an existing extracted_*.jsonl")
    ap.add_argument("--raw", default=None, help="Path to raw_*.jsonl (required with --enrich-existing)")
    ap.add_argument("--extracted", default=None, help="Path to extracted_*.jsonl (required with --enrich-existing)")
    ap.add_argument("--out", default=None, help="Output path for enriched file (optional)")

    # S3 options
    ap.add_argument("--s3", action="store_true", help="Write outputs to S3 instead of local disk")
    ap.add_argument("--s3-bucket", default="nexai-job-market-data", help="Target S3 bucket name")
    ap.add_argument("--s3-prefix", default="job_market", help="Top-level S3 prefix (folder)")
    ap.add_argument("--aws-region", default="us-east-1", help="AWS region for S3 client")

    args = ap.parse_args()
    logging.basicConfig(level=getattr(logging, args.log.upper(), logging.INFO), format="%(levelname)s: %(message)s")

    # Enrichment path (no scraping)
    if args.enrich_existing:
        if not args.raw or not args.extracted:
            raise SystemExit("--enrich-existing requires --raw and --extracted")
        enrich_existing(args.raw, args.extracted, args.companies_yaml, args.out)
        return

    role = args.role.strip() if args.role else "all"
    city = None if args.city.lower() == "all" else args.city.strip()

    companies = load_greenhouse_companies(args.companies_yaml)
    sector_map = load_company_sectors(args.companies_yaml)

    gh = GreenhouseScraper()
    if args.s3:
        store = S3Storage(bucket=args.s3_bucket, prefix=args.s3_prefix, region=args.aws_region)
        print(f"🪣 Using S3 storage → s3://{args.s3_bucket}/{_join_s3_key(args.s3_prefix, _now_date_str())}/")
    else:
        store = LocalStorage()
        print(f"💾 Using local storage → {OUTPUT_DIR}/")

    print("\n" + "=" * 78)
    print("GREENHOUSE SCRAPER — ROLE AGNOSTIC")
    print("=" * 78)

    # 1) Links
    print(f"\n[1/4] Scanning {len(companies)} Greenhouse boards…")
    gh_links = gh.get_all_job_urls(role, city, args.strict_location, companies, args.limit)
    links = {"greenhouse": gh_links}
    total = len(gh_links)
    print(f"   → {total} URLs matched")
    links_path = store.write_links(links, role or "all", city or "all")
    print(f"   saved: {links_path}")

    if total == 0:
        print("No matches. Exiting.")
        return

    # 2) Raw scrape
    print(f"\n[2/4] Downloading {total} postings…")
    raw: List[RawJob] = []
    for i, u in enumerate(gh_links, 1):
        rj = gh.parse_job(u)
        if rj:
            raw.append(rj)
            print(f"   [{i}/{total}] ✓ {rj.company or 'Unknown'} | {rj.title or 'Untitled'}")
        time.sleep(0.35)
    raw_path = store.write_raw(raw, role or "all", city or "all")
    print(f"   saved: {raw_path}")

    # 3) Extract
    print(f"\n[3/4] Extracting lightweight structure…")
    extracted = [heuristic_extract(r) for r in raw]

    # Attach sector using company name
    for ej in extracted:
        comp = (ej.company or "").lower()
        if comp in sector_map:
            ej.sector = sector_map[comp]

    # 🇺🇸 Optional US-only filter
    if args.us_only:
        before = len(extracted)
        extracted = [e for e in extracted if (e.country == "United States" or (e.city_state and CITY_STATE_RE.search(e.city_state)))]
        print(f"   → US-only filter kept {len(extracted)}/{before} jobs")

    # 4) Write extracted
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
