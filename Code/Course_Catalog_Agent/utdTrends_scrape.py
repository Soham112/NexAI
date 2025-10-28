#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Catalog + UTD Trends Scraper (single script) → S3

STAGE A (Catalog):
- Crawls program pages (configurable) and extracts:
  course_id (e.g., "MIS 6382"), course_name, catalog_url, program_title, program_page, scraped_at
- Writes: data/clean/catalog/courses_<YYYYMMDD>.json

STAGE B (UTD Trends):
- For each course_id, opens UTD Trends dashboard with searchTerms=<DEPT+NUM>
- Extracts the FULL description text (multiple paragraphs; filters UI chrome)
- Writes:
  - data/clean/utdtrends/trends_<YYYYMMDD>.jsonl
  - data/raw/utdtrends/html/<COURSE_ID>.html (per-course snapshot)

S3 Uploads:
- s3://nexai-course-catalog/clean/catalog/courses_<YYYYMMDD>.json
- s3://nexai-course-catalog/clean/utdtrends/trends_<YYYYMMDD>.jsonl
- s3://nexai-course-catalog/raw/utdtrends/html/<COURSE_ID>.html

Deps:
  pip install requests beautifulsoup4 lxml boto3 playwright
  playwright install chromium

Env (or CLI):
  AWS_REGION=us-east-1
  S3_BUCKET=nexai-course-catalog
  USER_AGENT=...
"""

import os
import re
import json
import time
import argparse
import datetime as dt
import urllib.parse as up
import urllib.robotparser as urp
from pathlib import Path
from typing import List, Dict, Tuple, Optional

import requests
from bs4 import BeautifulSoup, NavigableString, Tag

import boto3
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# =========================
# Config
# =========================
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET = os.getenv("S3_BUCKET", "nexai-course-catalog-soh")

USER_AGENT = os.getenv("USER_AGENT", "UTD-CatalogBot/1.0 (+mailto:team@example.com)")
CB_USER_AGENT = os.getenv("CB_USER_AGENT", "UTD-CourseBookBot/1.0 (+mailto:team@example.com)")
TRENDS_UA = os.getenv("TRENDS_USER_AGENT", "UTD-TrendsBot/1.0 (+mailto:team@example.com)")

POLITENESS_DELAY = float(os.getenv("POLITENESS_DELAY", "1.2"))
HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "20"))
MAX_BYTES = 10 * 1024 * 1024  # 10MB cap

COURSE_CODE_RE = re.compile(r"\b([A-Z]{2,5})\s?(\d{4})\b", re.I)

PROGRAM_URLS = [
    "https://catalog.utdallas.edu/2023/graduate/programs/jsom/information-technology-management",
    "https://catalog.utdallas.edu/2024/graduate/programs/jsom/business-analytics",
    "https://catalog.utdallas.edu/2025/graduate/programs/ecs/computer-science",
    "https://catalog.utdallas.edu/2023/graduate/programs/jsom/accounting-analytics-ms",
    "https://catalog.utdallas.edu/2023/graduate/programs/jsom/business-administration",
    "https://catalog.utdallas.edu/2023/graduate/programs/jsom/energy-management",
    "https://catalog.utdallas.edu/2023/graduate/programs/jsom/finance",
    "https://catalog.utdallas.edu/2023/graduate/programs/jsom/financial-technology-and-analytics",
    "https://catalog.utdallas.edu/2023/graduate/programs/jsom/healthcare-management",
    "https://catalog.utdallas.edu/2023/graduate/programs/jsom/innovation-entrepreneurship",
    "https://catalog.utdallas.edu/2023/graduate/programs/jsom/international-management-studies",
    "https://catalog.utdallas.edu/2023/graduate/programs/jsom/management-science",
    "https://catalog.utdallas.edu/2023/graduate/programs/jsom/marketing",
    "https://catalog.utdallas.edu/2023/graduate/programs/jsom/supply-chain-management",
    "https://catalog.utdallas.edu/2023/graduate/programs/jsom/systems-engineering-and-management/ms-sem",
    "https://catalog.utdallas.edu/2023/graduate/programs/jsom/systems-engineering-and-management/executive-ms-sem",
    "https://catalog.utdallas.edu/2023/graduate/programs/jsom/engineering-and-management",
    "https://catalog.utdallas.edu/2023/graduate/programs/jsom/phd#doctor-of-philosophy-in-international-management-studies",
    "https://catalog.utdallas.edu/2023/graduate/programs/jsom/phd#doctor-of-philosophy-in-management-science"
]

TRENDS_BASE = "https://trends.utdnebula.com/dashboard"

# =========================
# Paths / Time
# =========================
def date_stamp() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d")

def iso_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")

def ensure_dirs(out_root: str = "data") -> Dict[str, Path]:
    day = date_stamp()
    raw_dir = Path(out_root) / "raw" / "catalog" / day
    clean_catalog_dir = Path(out_root) / "clean" / "catalog"
    clean_coursebook_dir = Path(out_root) / "clean" / "coursebook"
    clean_trends_dir = Path(out_root) / "clean" / "courseCatalog"
    raw_trends_html = Path(out_root) / "raw" / "courseCatalog" / "html"
    for p in [raw_dir, clean_catalog_dir, clean_coursebook_dir, clean_trends_dir, raw_trends_html]:
        p.mkdir(parents=True, exist_ok=True)
    return {
        "raw_catalog": raw_dir,
        "clean_catalog": clean_catalog_dir,
        "clean_coursebook": clean_coursebook_dir,
        "clean_trends": clean_trends_dir,
        "raw_trends_html": raw_trends_html,
    }

def sections_out_path(out_root: str) -> Path:
    return Path(out_root) / "clean" / "coursebook" / f"sections_{date_stamp()}.jsonl"

def _sanitize(seg: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_." else "-" for ch in seg).strip("-") or "x"

def url_to_flat_filename(url: str) -> str:
    parts = up.urlsplit(url)
    path = parts.path.strip("/") or "index"
    segs = [_sanitize(s) for s in path.split("/")]
    stem = "-".join(segs)
    if parts.query:
        from hashlib import sha1
        stem += "-" + sha1(parts.query.encode()).hexdigest()[:10]
    return stem + ".html"

# =========================
# S3 helpers
# =========================
def s3_client():
    return boto3.client("s3", region_name=AWS_REGION)

def s3_upload(local_path: Path, key: str):
    s3_client().upload_file(str(local_path), S3_BUCKET, key)

# =========================
# Robots & Fetch
# =========================
def robots_allow(url: str) -> bool:
    parts = up.urlsplit(url)
    robots_url = up.urljoin(f"{parts.scheme}://{parts.netloc}", "/robots.txt")
    rp = urp.RobotFileParser()
    try:
        r = requests.get(robots_url, headers={"User-Agent": USER_AGENT}, timeout=HTTP_TIMEOUT)
        if r.status_code == 200:
            rp.parse(r.text.splitlines())
        else:
            rp.parse(["User-agent: *", "Allow: /"])
    except Exception:
        rp.parse(["User-agent: *", "Allow: /"])
    return rp.can_fetch(USER_AGENT, url)

def fetch(url: str) -> bytes:
    r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    if len(r.content) > MAX_BYTES:
        raise RuntimeError(f"{url} exceeded MAX_BYTES")
    return r.content

# =========================
# Catalog parsing (extract_item.py functionality)
# =========================
def _inline_text_after_anchor(a: Tag) -> str:
    pieces: List[str] = []
    node = a.next_sibling

    def is_block_boundary(t) -> bool:
        return isinstance(t, Tag) and t.name in ("h1","h2","h3","h4","p","ul","ol","table","div","br")

    while node is not None:
        if isinstance(node, NavigableString):
            pieces.append(str(node))
        elif isinstance(node, Tag):
            if node.name == "a" or is_block_boundary(node):
                break
            pieces.append(node.get_text(" ", strip=True))
        node = node.next_sibling
    txt = " ".join(" ".join(pieces).split()).lstrip(" -:•·|").strip()
    if txt.lower().startswith("or "):
        txt = txt[3:].lstrip(" -:").strip()
    return txt

def parse_program_page(html: bytes, page_url: str) -> List[Dict]:
    soup = BeautifulSoup(html, "lxml")
    program_title = soup.find("h1").get_text(" ", strip=True) if soup.find("h1") else None
    out: List[Dict] = []
    seen = set()
    for a in soup.find_all("a", href=True):
        text = a.get_text(" ", strip=True)
        m = COURSE_CODE_RE.search(text)
        if not m:
            continue
        dept, num = m.group(1).upper(), m.group(2)
        course_id = f"{dept} {num}"
        leftover = text[m.end():].strip(" -:")
        course_name = leftover or _inline_text_after_anchor(a) or None
        rec = {
            "course_id": course_id,
            "course_name": course_name,
            "catalog_url": up.urljoin(page_url, a["href"]),
            "program_title": program_title,
            "program_page": page_url,
            "scraped_at": iso_now(),
        }
        key = (rec["course_id"], rec["catalog_url"])
        if key not in seen:
            seen.add(key)
            out.append(rec)
    return out

def crawl_program_pages(program_urls: List[str], raw_dir: Path) -> Tuple[List[Dict], List[Path]]:
    all_courses: List[Dict] = []
    raw_paths: List[Path] = []
    for i, url in enumerate(program_urls, 1):
        print(f"[CAT {i}/{len(program_urls)}] {url}")
        if not robots_allow(url):
            print("  [!] Disallowed by robots.txt — skipping")
            continue
        time.sleep(POLITENESS_DELAY)
        html = fetch(url)
        fname = url_to_flat_filename(url)
        raw_path = raw_dir / fname
        raw_path.write_bytes(html)
        raw_paths.append(raw_path)
        rows = parse_program_page(html, url)
        print(f"  ✓ found {len(rows)} course anchors")
        all_courses.extend(rows)
    return all_courses, raw_paths

# =========================
# Trends scraping (FULL description with noise filtering)
# =========================
def course_to_terms(course_id: str) -> Optional[str]:
    m = COURSE_CODE_RE.search(course_id.strip().upper())
    if not m:
        return None
    return f"{m.group(1)}+{m.group(2)}"

def build_trends_url(course_id: str) -> str:
    terms = course_to_terms(course_id) or course_id
    q = {"searchTerms": terms, "availability": "true"}
    return f"{TRENDS_BASE}?{up.urlencode(q)}"

def _collapse_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()

# lines to ignore (UI chrome)
NOISE_PATTERNS = [
    r"\bSearch\b",
    r"\bMy Planner\b",
    r"\bMin Letter Grade\b",
    r"\bMin Rating\b",
    r"\bSemesters\b",
    r"\bAll selected\b",
    r"\bTeaching in\b",
    r"\bSearch Results\b",
    r"\bActions\b",
    r"\bName\b",
    r"\bGrades\b",
    r"\bRating\b",
    r"\(Overall\)$",
]
NOISE_RE = re.compile("|".join(NOISE_PATTERNS), re.I)

def _clean_lines(lines: List[str]) -> List[str]:
    cleaned = []
    for t in lines:
        t = _collapse_spaces(t)
        if not t:
            continue
        if NOISE_RE.search(t):
            continue
        # keep only reasonably informative paragraphs
        if len(t) < 30:
            continue
        cleaned.append(t)
    return cleaned

def extract_visible_blurb(page, course_id: str) -> Dict:
    """
    Grab FULL course description from the Trends 'Class' card:
      - Locate the card containing the exact course code (e.g., "BUAN 6335").
      - Inside that card, collect all <p> up to (but not including) 'Offering Frequency'.
      - Strip UI noise (search controls, filters, ratings axes, etc).
    """
    deptnum = _collapse_spaces(course_id.upper())

    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except PWTimeout:
        pass

    # Prefer the 'Class' card that contains the exact course code
    card = page.locator(f"article:has-text('{deptnum}')").first
    if card.count() == 0:
        # Fallback: any card-like container with the code
        card = page.locator(
            f"[role='article']:has-text('{deptnum}'), .MuiCard-root:has-text('{deptnum}'), .MuiPaper-root:has-text('{deptnum}')"
        ).first

    container = card if card.count() > 0 else page.locator("body")

    # Title (best-effort)
    try:
        title = container.locator("h1, h2, h3").first.inner_text(timeout=1500).strip()
    except Exception:
        title = deptnum

    # Pull all <p> texts within the container
    try:
        paras = container.locator("p").all_inner_texts()
    except Exception:
        paras = []

    # Stop at "Offering Frequency" (don’t include it)
    trimmed = []
    for t in paras:
        t = (t or "").strip()
        if not t:
            continue
        if re.match(r"^\s*Offering Frequency\s*:", t, re.I):
            break
        trimmed.append(t)

    # Clean out page chrome lines and keep full description paragraphs
    desc_lines = _clean_lines(trimmed)

    # If we somehow didn’t get anything, fall back to broader search (still filtered)
    if not desc_lines:
        try:
            body_ps = page.locator("article p, [role='article'] p, .MuiCard-root p, .MuiPaper-root p").all_inner_texts()
        except Exception:
            body_ps = []
        trimmed2 = []
        for t in body_ps:
            t = (t or "").strip()
            if not t or re.match(r"^\s*Offering Frequency\s*:", t, re.I):
                break
            trimmed2.append(t)
        desc_lines = _clean_lines(trimmed2)

    # Join paragraphs into a single description
    description = _collapse_spaces(" ".join(desc_lines))

    return {
        "course_id": deptnum,
        "title": _collapse_spaces(title or deptnum),
        "blurb": description,  # keeping key name for backward-compat
        "url": build_trends_url(course_id),
        "scraped_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    }

def scrape_trends_for_courses(course_ids: List[str],
                              out_dirs: Dict[str, Path],
                              headless: bool = True,
                              limit: Optional[int] = None) -> Path:
    clean_dir = out_dirs["clean_trends"]
    raw_html_dir = out_dirs["raw_trends_html"]
    out_jsonl = clean_dir / f"trends_{date_stamp()}.jsonl"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless,
                                    args=["--disable-dev-shm-usage", "--no-sandbox"])
        ctx = browser.new_context(user_agent=TRENDS_UA, viewport={"width": 1440, "height": 900})
        page = ctx.new_page()

        written = 0
        with out_jsonl.open("w", encoding="utf-8") as f:
            for i, cid in enumerate(course_ids, 1):
                if limit and written >= limit:
                    break
                url = build_trends_url(cid)
                try:
                    page.goto(url, timeout=30000, wait_until="domcontentloaded")
                    try:
                        page.wait_for_load_state("networkidle", timeout=15000)
                    except PWTimeout:
                        pass

                    # Save snapshot for debugging/repro
                    html_path = raw_html_dir / (re.sub(r"[^A-Za-z0-9]+", "_", cid.upper()) + ".html")
                    html_path.write_text(page.content(), encoding="utf-8")

                    rec = extract_visible_blurb(page, cid)
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    f.flush()
                    written += 1
                    print(f"[TRN {i}/{len(course_ids)}] {cid} ✓  → {rec['title'][:80]}")
                except Exception as e:
                    print(f"[TRN {i}/{len(course_ids)}] {cid} ✗  ({e})")
                time.sleep(POLITENESS_DELAY)

        ctx.close(); browser.close()
    return out_jsonl

# =========================
# Utilities
# =========================
def extract_tags(course_id: str, course_name: str, description: str = "") -> List[str]:
    """Extract tags from course information."""
    tags = [course_id]
    
    # Add course name words as tags (excluding common words)
    if course_name:
        stop_words = {"for", "and", "the", "a", "an", "in", "on", "at", "to", "with", "of"}
        words = re.findall(r'\b[A-Z][a-z]+\b', course_name)
        for word in words:
            if word.lower() not in stop_words and len(word) > 3:
                tags.append(word)
    
    # Extract keywords from description (capitalized words)
    if description:
        keywords = re.findall(r'\b[A-Z][a-z]{2,}\b', description)
        for kw in keywords[:5]:  # Limit to 5 keywords
            if kw not in tags:
                tags.append(kw)
    
    return list(set(tags))  # Remove duplicates

def format_course_record(catalog_item: Dict, trends_item: Optional[Dict] = None) -> Dict:
    """Format course data into the requested structure."""
    course_id = catalog_item.get("course_id", "").strip()
    course_id_clean = course_id.replace(" ", "_")
    
    # Build text field
    course_name = catalog_item.get("course_name", "")
    description = trends_item.get("blurb", "") if trends_item else ""
    
    text_parts = [f"{course_id} — {course_name}"]
    if description:
        text_parts.append(description)
    text = ". ".join(text_parts)
    
    # Extract tags
    tags = extract_tags(course_id, course_name, description)
    
    # Build meta
    meta = {
        "url": catalog_item.get("catalog_url", trends_item.get("url", "") if trends_item else ""),
        "scraped_at": catalog_item.get("scraped_at", iso_now()),
        "program_title": catalog_item.get("program_title", ""),
        "program_page": catalog_item.get("program_page", "")
    }
    
    return {
        "id": f"courses:{course_id_clean}",
        "domain": "courses",
        "text": text,
        "tags": tags,
        "meta": meta
    }

def merge_catalog_and_trends(catalog_data: List[Dict], trends_jsonl_path: Path) -> List[Dict]:
    """Merge catalog and trends data, output in new format."""
    # Load trends data into a dict keyed by course_id
    trends_dict = {}
    if trends_jsonl_path.exists():
        with trends_jsonl_path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    item = json.loads(line.strip())
                    cid = item.get("course_id", "").strip()
                    if cid:
                        trends_dict[cid.upper()] = item
    
    # Merge and format
    merged = []
    for catalog_item in catalog_data:
        course_id = catalog_item.get("course_id", "").strip()
        trends_item = trends_dict.get(course_id.upper())
        
        formatted = format_course_record(catalog_item, trends_item)
        merged.append(formatted)
    
    return merged

def save_catalog_courses(courses: List[Dict], clean_dir: Path) -> Path:
    out_path = clean_dir / f"courses_{date_stamp()}.json"
    out_path.write_text(json.dumps(courses, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path

def save_merged_format(merged_data: List[Dict], clean_dir: Path, as_jsonl: bool = False) -> Path:
    """Save in new unified format."""
    if as_jsonl:
        out_path = clean_dir / f"courses_merged_{date_stamp()}.jsonl"
        with out_path.open("w", encoding="utf-8") as f:
            for item in merged_data:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
    else:
        out_path = clean_dir / f"courses_merged_{date_stamp()}.json"
        out_path.write_text(json.dumps(merged_data, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path

def upload_catalog_and_trends(catalog_json: Optional[Path],
                              trends_jsonl: Optional[Path],
                              out_dirs: Dict[str, Path]):
    if catalog_json:
        s3_upload(catalog_json, f"clean/catalog/{catalog_json.name}")
        print(f"S3: s3://{S3_BUCKET}/clean/catalog/{catalog_json.name}")
    if trends_jsonl:
        s3_upload(trends_jsonl, f"clean/coursecatalog/{trends_jsonl.name}")
        print(f"S3: s3://{S3_BUCKET}/clean/coursecatalog/{trends_jsonl.name}")
        # upload raw HTML snapshots
        for p in out_dirs["raw_trends_html"].glob("*.html"):
            s3_upload(p, f"raw/utdtrends/html/{p.name}")

def load_course_ids_from_json(path: Path) -> List[str]:
    text = path.read_text(encoding="utf-8").strip()
    ids: List[str] = []
    data = json.loads(text)
    if isinstance(data, list):
        for row in data:
            cid = (row.get("course_id") or "").strip()
            if cid:
                ids.append(cid)
    # de-dup, preserve order
    seen = set(); uniq = []
    for c in ids:
        u = c.upper()
        if u not in seen:
            seen.add(u); uniq.append(c)
    return uniq

# =========================
# CLI
# =========================
def main():
    ap = argparse.ArgumentParser(description="Crawl UTD Catalog + scrape UTD Trends (single script) → S3")
    ap.add_argument("--out-root", default="data", help="Output root directory (default: data)")
    ap.add_argument("--program-url", action="append",
                    help="Add a program page URL to crawl (can be repeated). If omitted, uses defaults.")
    ap.add_argument("--skip-catalog", action="store_true",
                    help="Skip catalog crawl (use an existing courses.json via --input-courses).")
    ap.add_argument("--input-courses", default=None,
                    help="Path to existing catalog courses JSON (if you skip catalog).")
    ap.add_argument("--no-upload", action="store_true", help="Skip S3 upload.")
    ap.add_argument("--no-headless", action="store_true", help="Run Chromium with a window (debug)")
    ap.add_argument("--limit", type=int, default=None, help="Limit number of courses for trends (debug)")
    ap.add_argument("--jsonl", action="store_true", help="Save merged output as JSONL instead of JSON")
    args = ap.parse_args()

    out_dirs = ensure_dirs(args.out_root)

    # -------- Stage A: Catalog crawl (optional) --------
    catalog_json_path: Optional[Path] = None
    courses: List[Dict] = []

    if not args.skip_catalog:
        urls = args.program_url if args.program_url else PROGRAM_URLS
        courses, _raws = crawl_program_pages(urls, out_dirs["raw_catalog"])
        if not courses:
            raise SystemExit("No courses found from program pages.")
        catalog_json_path = save_catalog_courses(courses, out_dirs["clean_catalog"])
        print(f"Catalog saved → {catalog_json_path}")
    else:
        if not args.input_courses:
            raise SystemExit("--skip-catalog requires --input-courses to point to courses JSON.")
        p = Path(args.input_courses)
        if not p.exists():
            raise SystemExit(f"courses JSON not found: {p}")
        courses = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(courses, list) or not courses:
            raise SystemExit("courses JSON is empty or invalid.")
        print(f"Loaded {len(courses)} courses from {p}")

    # Prepare course IDs
    course_ids = []
    for row in courses:
        cid = (row.get("course_id") or "").strip()
        if cid:
            course_ids.append(cid)
    # de-dup
    seen = set(); uniq = []
    for c in course_ids:
        u = c.upper()
        if u not in seen:
            seen.add(u); uniq.append(c)
    course_ids = uniq
    print(f"Total unique course_ids: {len(course_ids)}")

    # -------- Stage B: UTD Trends scrape --------
    trends_jsonl_path = scrape_trends_for_courses(
        course_ids, out_dirs, headless=not args.no_headless, limit=args.limit
    )
    print(f"Trends saved → {trends_jsonl_path}")

    # -------- Stage C: Merge and save in new format --------
    merged_data = merge_catalog_and_trends(courses, trends_jsonl_path)
    merged_output_path = save_merged_format(merged_data, out_dirs["clean_trends"], as_jsonl=args.jsonl)
    print(f"Merged format saved → {merged_output_path}")

    # -------- Uploads --------
    if not args.no_upload:
        upload_catalog_and_trends(catalog_json_path, trends_jsonl_path, out_dirs)
        # Also upload merged format
        s3_upload(merged_output_path, f"clean/courses_merged_{merged_output_path.name}")
        print(f"S3: s3://{S3_BUCKET}/clean/courses_merged_{merged_output_path.name}")
        print("All uploads complete.")

if __name__ == "__main__":
    main()
