#!/usr/bin/env python3

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

# ======== AWS S3 storage ==========
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

# ========== Data models ============
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
    experience_level: Optional[str] = None
    sector: Optional[str] = None
    country: Optional[str] = None
    city_state: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_unit: Optional[str] = None
    salary_currency: Optional[str] = None

    def to_json(self) -> str:
        obj = asdict(self)
        for k in ("skills", "responsibilities", "qualifications"):
            if obj.get(k) is None:
                obj[k] = []
        return json.dumps(obj, ensure_ascii=False)

# ========== Scraping logic & helpers =============
DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": DEFAULT_UA})

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

LEVEL_PATTERNS = [
    ("intern", r"\b(intern|co-?op|apprentice(ship)?)\b"),
    ("entry", r"\b(junior|jr\.?|new grad|newgrad|graduate)\b"),
    ("manager", r"\b(manager|managing|lead|head of|director|vp|vice president)\b"),
    ("staff", r"\b(staff|principal|distinguished|fellow)\b"),
    ("senior", r"\b(senior|sr\.?)\b"),
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

US_STATES = {"AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA",
    "KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM",
    "NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA",
    "WV","WI","WY"}
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

# Heuristic extractor
def heuristic_extract(raw: RawJob) -> ExtractedJob:
    desc = raw.text if hasattr(raw, "text") else ""
    title = raw.title
    company = raw.company
    location = raw.location
    salary_min, salary_max, salary_unit, salary_currency = None, None, None, None
    sal_match = re.search(r"\$([0-9,]+)", desc)
    if sal_match:
        salary_min = int(sal_match.group(1).replace(",", ""))
        salary_unit = "annual"
        salary_currency = "USD"
    experience_level = infer_level(title)
    country, city_state = infer_country_and_citystate(location, desc)
    return ExtractedJob(
        url=raw.url,
        company=company,
        title=title,
        location=location,
        experience_level=experience_level,
        salary_min=salary_min,
        salary_max=salary_max,
        salary_unit=salary_unit,
        salary_currency=salary_currency,
        sector=None,
        country=country,
        city_state=city_state,
        skills=[],
        responsibilities=[],
        qualifications=[]
    )

# Main Greenhouse scraper
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

# ============ Main CLI =============
def main():
    ap = argparse.ArgumentParser(description="Greenhouse-only scraper (role/location optional)")
    ap.add_argument("--role", default="all", help="Role keywords (use 'all' to skip title filtering)")
    ap.add_argument("--city", default="all", help="City text to match, or 'all' (skipped by default)")
    ap.add_argument("--strict-location", action="store_true", help="Exact city substring match (if --city provided)")
    ap.add_argument("--limit", type=int, default=-1, help="Max URLs to fetch overall (<=0 = unlimited)")
    ap.add_argument("--log", default="INFO")
    ap.add_argument("--s3-bucket", default="nexai-job-market-data", help="Target S3 bucket name")
    ap.add_argument("--aws-region", default="us-east-1", help="AWS region for S3 client")
    args = ap.parse_args()
    logging.basicConfig(level=getattr(logging, args.log.upper(), logging.INFO), format="%(levelname)s: %(message)s")
    store = S3Storage(bucket=args.s3_bucket, region=args.aws_region)
    print(f"🪣 Using S3 storage → s3://{args.s3_bucket}/(links|raw|extracted)/...")

    companies = [
        "figma", "gitlab","robinhood","airtable","affirm","carta","checkr","earnin","gusto","mercury","buildkite","airbyte",
        "anthropic","honehealth","springhealth66","vivian","stellarhealth","quince","mejuri","doordashusa","aninebing",
        "coursera","degreed","cc","aircompany","weee","acommerce","bringg","oliverusa","6sense","demandbase","amplitude",
        "dovetail","clutch","automatticcareers","netdocuments","xai","ethoslife","pieinsurance","constrafor","apeel",
        "agoda","blockchain","fireblocks","algolia","bgeinccampus","bgeinc","dlrgroup","northmarq",
        "dlrgroup","dataiku","point72","lilasciences","integrainterns","aef","strongholdim","samsungsemiconductor","xpengmotors",
        "scaleai","sonyinteractiveentertainmentglobal","gofundme","spacex","lokajobs","mirakl" # Add your companies here, e.g., "figma", "gitlab", etc.
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
    seen, dedup = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u)
            dedup.append(u)
    if args.limit > 0:
        dedup = dedup[:args.limit]
    links = {"greenhouse": dedup}
    print(f" → {len(dedup)} URLs matched")
    links_path = store.write_links(links, role or "all", city or "all")
    print(f" saved: {links_path}")

    if not dedup:
        print("No matches. Exiting.")
        return

    print(f"\n[2/4] Downloading {len(dedup)} postings…")
    raw: List[RawJob] = []
    for i, u in enumerate(dedup, 1):
        rj = gh.parse_job(u)
        if rj:
            raw.append(rj)
            print(f" [{i}/{len(dedup)}] ✓ {rj.company or 'Unknown'} | {rj.title or 'Untitled'}")
        time.sleep(0.25)
    raw_path = store.write_raw(raw, role or "all", city or "all")
    print(f" saved: {raw_path}")

    print(f"\n[3/4] Extracting lightweight structure…")
    extracted = [heuristic_extract(r) for r in raw]

    print(f"\n[4/4] Writing JSON…")
    out_path = store.write_extracted(extracted, role or "all", city or "all")
    print(f" saved: {out_path}")

    print("\n" + "=" * 78)
    print("DONE")
    print("=" * 78)
    print(f"Links: {links_path}")
    print(f"Raw HTML: {raw_path}")
    print(f"Extracted: {out_path}")

if __name__ == "__main__":
    main()
