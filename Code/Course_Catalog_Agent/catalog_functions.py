#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ALL-IN-ONE (NON-HEADLESS) PIPELINE:
- Crawl UTD catalog pages (3 targets) → data/raw/catalog/YYYYMMDD/*.html
- Parse course anchors → data/clean/catalog/{courses.jsonl, courses.json}
- Open CourseBook (real Chromium window), let you log in once, then
  scrape every course id (mis6382, buan6320, ...) into:
  data/clean/coursebook/sections_YYYYMMDD.jsonl
- Upload everything to s3://nexai-course-catalog/...

Usage:
  python3 catalog_all_in_one_nonheadless.py --bucket nexai-course-catalog
"""

import os
import re
import json
import time
import argparse
import datetime as dt
import urllib.parse as up
import urllib.robotparser as urp
from typing import List, Dict, Tuple, Optional

import requests
from bs4 import BeautifulSoup, NavigableString, Tag

# =========================
# Config
# =========================
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET_DEFAULT = os.getenv("S3_BUCKET", "nexai-course-catalog")

USER_AGENT = os.getenv("USER_AGENT", "UTD-CatalogBot/1.0 (+mailto:team@example.com)")
CB_USER_AGENT = os.getenv("CB_USER_AGENT", "UTD-CourseBookBot/1.0 (+mailto:team@example.com)")

POLITENESS_DELAY = float(os.getenv("POLITENESS_DELAY", "1.2"))
HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "20"))
MAX_BYTES = 10 * 1024 * 1024  # 10MB cap

COURSE_CODE_RE = re.compile(r"\b([A-Z]{2,5})\s?(\d{4})\b", re.I)

PROGRAM_URLS = [
    "https://catalog.utdallas.edu/2023/graduate/programs/jsom/information-technology-management",
    "https://catalog.utdallas.edu/2024/graduate/programs/jsom/business-analytics",
    "https://catalog.utdallas.edu/2025/graduate/programs/ecs/computer-science",
]

CB_BASE = "https://coursebook.utdallas.edu/search"

# =========================
# Paths
# =========================
def date_stamp() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d")

def iso_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")

def ensure_dirs(out_root: str = "data") -> Tuple[str, str, str]:
    day = date_stamp()
    raw_dir = os.path.join(out_root, "raw", "catalog", day)
    clean_catalog_dir = os.path.join(out_root, "clean", "catalog")
    clean_coursebook_dir = os.path.join(out_root, "clean", "coursebook")
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(clean_catalog_dir, exist_ok=True)
    os.makedirs(clean_coursebook_dir, exist_ok=True)
    return raw_dir, clean_catalog_dir, clean_coursebook_dir

def sections_out_path(out_root: str) -> str:
    return os.path.join(out_root, "clean", "coursebook", f"sections_{date_stamp()}.jsonl")

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
# Fetch / robots
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
# Catalog parsing
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

def crawl_program_pages(program_urls: List[str], raw_dir: str) -> Tuple[List[Dict], List[str]]:
    all_courses: List[Dict] = []
    raw_paths: List[str] = []
    for i, url in enumerate(program_urls, 1):
        print(f"[{i}/{len(program_urls)}] {url}")
        if not robots_allow(url):
            print("  [!] Disallowed by robots.txt — skipping")
            continue
        time.sleep(POLITENESS_DELAY)
        html = fetch(url)
        fname = url_to_flat_filename(url)
        raw_path = os.path.join(raw_dir, fname)
        with open(raw_path, "wb") as f:
            f.write(html)
        raw_paths.append(raw_path)
        rows = parse_program_page(html, url)
        print(f"  ✓ found {len(rows)} course anchors")
        all_courses.extend(rows)
    return all_courses, raw_paths

# =========================
# CourseBook parsing
# =========================
CB_STATUS_RE = re.compile(
    r"Enrollment Status:\s*(?P<status>\w+)"
    r"\s*Available Seats:\s*(?P<available>\d+)"
    r"\s*Enrolled Total:\s*(?P<enrolled>\d+)"
    r"\s*Waitlist:\s*(?P<waitlist>\d+)",
    re.I,
)

def _text(n: Optional[Tag]) -> Optional[str]:
    if not n:
        return None
    t = n.get_text(" ", strip=True)
    return t if t else None

def _kv_cells_to_dict(td: Tag) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for tr in td.select("table.courseinfo__classsubtable tr"):
        tds = tr.find_all("td")
        if len(tds) >= 2:
            k = _text(tds[0]) or ""
            v = _text(tds[1]) or ""
            if k:
                out[k.strip()] = v
        if len(tds) >= 4:
            k2 = _text(tds[2]) or ""
            v2 = _text(tds[3]) or ""
            if k2:
                out[k2.strip()] = v2
    return out

def _parse_meetings(td: Tag):
    meta = {"term": None, "session_type": None, "starts": None, "ends": None}
    meetings: List[Dict[str, str]] = []
    for strong in td.select("strong"):
        label = strong.get_text(" ", strip=True).rstrip(":").lower()
        value = strong.next_sibling.strip() if strong.next_sibling else None
        if not value:
            sib = strong.parent.find_next_sibling(text=True)
            value = sib.strip() if sib else None
        if label == "term":
            meta["term"] = value
        elif label == "type":
            meta["session_type"] = value
        elif label == "starts":
            meta["starts"] = value
        elif label == "ends":
            meta["ends"] = value
    for block in td.select(".courseinfo__meeting-item--multiple, .courseinfo__datestimes"):
        block_text = _text(block)
        room_a = block.find("a", href=True)
        meetings.append({
            "text": block_text,
            "room": _text(room_a),
            "room_href": room_a["href"] if room_a else None,
        })
    return meta, meetings

def _parse_people(td: Tag) -> List[Dict[str, Optional[str]]]:
    people: List[Dict[str, Optional[str]]] = []
    for item in td.select("div[id^='inst-'] div"):
        txt = _text(item) or ""
        email = None
        mail = item.find("a", href=re.compile(r"^mailto:"))
        if mail:
            email = mail["href"].replace("mailto:", "")
        parts = [p.strip() for p in re.split(r"・|\|", txt) if p.strip()]
        name = parts[0] if parts else None
        role = None
        for p in parts[1:]:
            if "instructor" in p.lower() or "assistant" in p.lower():
                role = p
                break
        people.append({"name": name, "email": email, "role": role})
    if not people:
        t = _text(td)
        if t:
            people.append({"name": t, "email": None, "role": None})
    return people

def parse_expanded_overview(expanded_html: str) -> Dict:
    soup = BeautifulSoup(expanded_html or "", "lxml")
    tbl = soup.select_one("table.courseinfo__overviewtable")
    data = {
        "course_title": None,
        "class_section": None,
        "instruction_mode": None,
        "class_level": None,
        "activity_type": None,
        "credit_hours": None,
        "grading": None,
        "add_consent": None,
        "how_often_course_scheduled": None,
        "class_number": None,
        "course_number": None,
        "session_type": None,
        "orion_datetime": None,
        "enrollment_status": None,
        "available_seats": None,
        "enrolled_total": None,
        "waitlist": None,
        "description_html": None,
        "instructors": [],
        "tas": [],
        "term": None,
        "term_meta": {},
        "meetings": [],
        "exam": None,
        "exam_location": None,
        "college": None,
        "college_href": None,
        "evaluation_href": None,
        "syllabus_url": None,
        "orion_register_href": None,
    }
    if not tbl:
        return data
    title = tbl.select_one(".courseinfo__overviewtable__coursetitle")
    data["course_title"] = _text(title)
    for tr in tbl.select("tr"):
        th = _text(tr.find("th"))
        td = tr.find("td")
        if not th or not td:
            continue
        low = th.lower()
        if "class info" in low:
            kvs = _kv_cells_to_dict(td)
            for k, v in kvs.items():
                lk = k.lower()
                if "class section" in lk:
                    data["class_section"] = v
                elif "instruction mode" in lk:
                    data["instruction_mode"] = v
                elif "class level" in lk:
                    data["class_level"] = v
                elif "activity type" in lk:
                    data["activity_type"] = v
                elif "semester credit hours" in lk:
                    data["credit_hours"] = v
                elif "class/course number" in lk:
                    if "/" in v:
                        c1, c2 = v.split("/", 1)
                        data["class_number"] = c1.strip()
                        data["course_number"] = c2.strip()
                    else:
                        data["class_number"] = v
                elif "grading" in lk:
                    data["grading"] = v
                elif "add consent" in lk:
                    data["add_consent"] = v
                elif "how often" in lk:
                    data["how_often_course_scheduled"] = v
                elif "session type" in lk:
                    data["session_type"] = v
                elif "orion date/time" in lk:
                    data["orion_datetime"] = v
        elif "status" in low:
            s = _text(td) or ""
            m = CB_STATUS_RE.search(s)
            if m:
                data["enrollment_status"] = m.group("status")
                data["available_seats"] = int(m.group("available"))
                data["enrolled_total"] = int(m.group("enrolled"))
                data["waitlist"] = int(m.group("waitlist"))
            else:
                data["enrollment_status"] = s
        elif "description" in low:
            data["description_html"] = str(td)
        elif re.search(r"^instructor", low):
            data["instructors"] = _parse_people(td)
        elif re.search(r"^ta/ra", low):
            data["tas"] = _parse_people(td)
        elif "class location and times" in low or "schedule" in low:
            meta, meetings = _parse_meetings(td)
            data["term_meta"] = meta
            data["term"] = meta.get("term")
            data["session_type"] = data["session_type"] or meta.get("session_type")
            data["meetings"] = meetings
        elif "exams" in low:
            txt = _text(td) or ""
            data["exam"] = txt
            a = td.find("a", href=True)
            if a:
                data["exam_location"] = a.get("href")
        elif "college" in low:
            a = td.find("a", href=True)
            data["college"] = _text(a) or _text(td)
            data["college_href"] = a["href"] if a else None
        elif "syllabus" in low:
            a = td.find("a", href=True)
            data["syllabus_url"] = a["href"] if a else None
        elif "evaluation" in low:
            a = td.find("a", href=True)
            data["evaluation_href"] = a["href"] if a else None
    reg = soup.find("a", href=True, string=re.compile("Register for this class on Orion", re.I))
    if reg:
        data["orion_register_href"] = reg["href"]
    return data

# =========================
# CourseBook runner (non-headless)
# =========================
def cb_wait_for_results(page):
    from playwright.sync_api import TimeoutError as PWTimeout
    try:
        page.wait_for_selector("#searchresults", state="visible", timeout=12000); return
    except PWTimeout:
        pass
    try:
        page.wait_for_selector("table >> text=Class Title", timeout=7000); return
    except PWTimeout:
        page.wait_for_timeout(800)

def cb_looks_logged_in(page) -> bool:
    try:
        txt = page.locator("#pauth_menu").inner_text(timeout=1500)
        return "LOGIN" not in (txt or "").upper()
    except Exception:
        return False

def course_ids_from_courses(courses: List[Dict]) -> List[str]:
    seen, out = set(), []
    for r in courses:
        m = COURSE_CODE_RE.search(r.get("course_id", "") or "")
        if not m:
            continue
        dep, num = m.group(1).lower(), m.group(2)
        key = dep + num
        if key not in seen:
            seen.add(key)
            out.append(key)
    return out

def scrape_coursebook_non_headless(ids: List[str], out_root: str, per_id_limit: int = 50, user_dir: str = ".pw-user") -> str:
    """
    Opens a real Chromium window (non-headless), asks you to log in once, then scrapes all IDs.
    Appends each row to data/clean/coursebook/sections_YYYYMMDD.jsonl
    """
    out_jsonl = sections_out_path(out_root)
    os.makedirs(os.path.dirname(out_jsonl), exist_ok=True)

    from pathlib import Path
    from playwright.sync_api import sync_playwright
    Path(user_dir).mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=user_dir,          # persistent profile
            headless=False,
            user_agent=CB_USER_AGENT,
            viewport={"width": 1280, "height": 900},
        )
        page = ctx.new_page()

        # open Search page
        page.goto(CB_BASE, wait_until="domcontentloaded", timeout=30000)
        time.sleep(POLITENESS_DELAY)

        # login flow (manual)
        need_login = (not cb_looks_logged_in(page)) or page.locator("iframe[title='reCAPTCHA']").count() > 0
        if need_login:
            print("\n=== Action Required (one-time) ===")
            print("A Chromium window is open. Please log in with your NetID and pass any reCAPTCHA.")
            input("When you return to the CourseBook search page, press ENTER here to continue... ")
            page.reload(wait_until="domcontentloaded")
            time.sleep(POLITENESS_DELAY)

        # iterate course ids with retries and robust waits
        for i, cid in enumerate(ids, 1):
            query = f"now {cid}"
            print(f"  [{i}/{len(ids)}] {query}")

            success = False
            for attempt in range(2):  # retry up to twice to allow slow loads
                # enter query and submit
                if page.locator("input#srch").count():
                    page.fill("input#srch", query)
                else:
                    page.get_by_placeholder("Search for classes").fill(query)
                page.keyboard.press("Enter")

                cb_wait_for_results(page)
                page.wait_for_timeout(2000)  # let dynamic table populate

                rows = page.locator("#sr table tbody tr.cb-row")
                if rows.count() > 0:
                    success = True
                    break
                else:
                    print(f"    [retry {attempt+1}] No rows yet for {cid}, waiting 3s…")
                    page.wait_for_timeout(3000)

            if not success:
                dbg_dir = os.path.join(out_root, "debug")
                os.makedirs(dbg_dir, exist_ok=True)
                with open(os.path.join(dbg_dir, f"no_rows_{cid}.html"), "w", encoding="utf-8") as f:
                    f.write(page.content())
                print(f"    [!] No rows parsed for {cid} — saved debug HTML.")
                continue

            total = min(rows.count(), per_id_limit)
            print(f"    ✓ Found {total} rows")

            for j in range(total):
                row = rows.nth(j)
                section = row.locator("td").nth(1).inner_text().strip()
                class_title = row.locator("td").nth(3).inner_text().strip()

                # expand Class Detail
                btn = row.locator("button.has-cb-row-action", has_text="Class Detail")
                if btn.count() == 0:
                    btn = row.locator("td button", has_text="Class Detail")
                if btn.count():
                    btn.first.click()
                    page.wait_for_timeout(800)  # longer to allow DOM update

                expanded = row.evaluate_handle(
                    """(r) => { const next = r.nextElementSibling;
                               if(!next) return '';
                               const td = next.querySelector('td'); return td ? td.innerHTML : ''; }"""
                )
                expanded_html = expanded.json_value() if expanded else ""
                details = parse_expanded_overview(expanded_html)

                # ensure syllabus link if lazy
                tab = row.locator("button.has-cb-action.is-tab", has_text=re.compile(r"syllabus", re.I))
                if tab.count():
                    tab.first.click()
                    page.wait_for_timeout(400)
                    expanded2 = row.evaluate_handle(
                        """(r) => { const next = r.nextElementSibling;
                                   if(!next) return '';
                                   const td = next.querySelector('td'); return td ? td.innerHTML : ''; }"""
                    )
                    html2 = expanded2.json_value() if expanded2 else ""
                    if html2:
                        soup2 = BeautifulSoup(html2, "lxml")
                        th = soup2.find("th", string=re.compile(r"^\s*Syllabus\s*:", re.I))
                        if th:
                            a = th.find_next("td").find("a", href=True)
                            if a:
                                details["syllabus_url"] = a["href"]

                row_json = {
                    "query": query,
                    "section": section,         # e.g., MIS 6382.001.25F
                    "class_title": class_title, # includes credits
                    **details
                }
                with open(out_jsonl, "a", encoding="utf-8") as f:
                    f.write(json.dumps(row_json, ensure_ascii=False) + "\n")

            # small settle time between course ids
            page.wait_for_timeout(1500)

        try:
            ctx.close()
        except Exception:
            pass

    print(f"✓ Wrote CourseBook sections → {out_jsonl}")
    return out_jsonl

# =========================
# Writers + S3 upload
# =========================
def write_catalog_json(clean_catalog_dir: str, courses: List[Dict]) -> Tuple[str, str, str]:
    jsonl_path = os.path.join(clean_catalog_dir, "courses.jsonl")
    json_path  = os.path.join(clean_catalog_dir, "courses.json")
    snapshot_path = os.path.join(clean_catalog_dir, "snapshot.json")
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for r in courses:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(courses, f, ensure_ascii=False, indent=2)
    with open(snapshot_path, "w", encoding="utf-8") as f:
        json.dump({
            "program_pages": len(PROGRAM_URLS),
            "courses": len(courses),
            "updated_at": iso_now(),
        }, f, ensure_ascii=False)
    return jsonl_path, json_path, snapshot_path

def upload_many(bucket: str, local_to_key: List[Tuple[str, str]]):
    import boto3
    s3 = boto3.client("s3", region_name=AWS_REGION)
    for local, key in local_to_key:
        s3.upload_file(local, bucket, key)
        print(f"↑ s3://{bucket}/{key}")

def upload_outputs(bucket: str, raw_dir: str, courses_jsonl: str, courses_json: str, snapshot_json: str, sections_jsonl: Optional[str]):
    day = os.path.basename(os.path.normpath(raw_dir))
    pairs: List[Tuple[str, str]] = []
    # raw
    for fname in os.listdir(raw_dir):
        pairs.append((os.path.join(raw_dir, fname), f"raw/catalog/{day}/{fname}"))
    # clean catalog
    pairs.append((courses_jsonl, "clean/catalog/courses.jsonl"))
    pairs.append((courses_json,  "clean/catalog/courses.json"))
    pairs.append((snapshot_json, "curated/catalog/snapshot.json"))
    # coursebook
    if sections_jsonl and os.path.exists(sections_jsonl):
        pairs.append((sections_jsonl, f"clean/coursebook/{os.path.basename(sections_jsonl)}"))
    upload_many(bucket, pairs)

# =========================
# Orchestrator
# =========================
def run_pipeline(out_root: str, bucket: Optional[str], per_id_limit: int = 50, user_dir: str = ".pw-user"):
    raw_dir, clean_catalog_dir, _ = ensure_dirs(out_root)

    # 1) Catalog crawl
    courses, _raws = crawl_program_pages(PROGRAM_URLS, raw_dir)

    # 2) Catalog JSON
    courses_jsonl, courses_json, snapshot_json = write_catalog_json(clean_catalog_dir, courses)

    # 3) CourseBook (non-headless, manual login once)
    ids = course_ids_from_courses(courses)
    print(f"Unique CourseBook IDs: {len(ids)}")
    sections_jsonl = scrape_coursebook_non_headless(ids, out_root=out_root, per_id_limit=per_id_limit, user_dir=user_dir)

    # 4) Upload
    if bucket:
        upload_outputs(bucket=bucket, raw_dir=raw_dir, courses_jsonl=courses_jsonl,
                       courses_json=courses_json, snapshot_json=snapshot_json,
                       sections_jsonl=sections_jsonl)
        print(f"✓ Uploaded to s3://{bucket}/")

    print("✅ All done.")

# =========================
# CLI
# =========================
def main():
    ap = argparse.ArgumentParser(description="UTD Catalog + CourseBook (non-headless) → local + optional S3")
    ap.add_argument("--out-root", default="data", help="Local output root (default: data)")
    ap.add_argument("--bucket", default=S3_BUCKET_DEFAULT, help="S3 bucket (default env/param). Use --no-upload to skip.")
    ap.add_argument("--no-upload", action="store_true", help="Skip S3 upload")
    ap.add_argument("--limit", type=int, default=50, help="Max rows per CourseBook id")
    ap.add_argument("--user-dir", default=".pw-user", help="Playwright persistent profile dir")
    args = ap.parse_args()

    bucket = None if args.no_upload else (args.bucket or None)
    run_pipeline(out_root=args.out_root, bucket=bucket, per_id_limit=args.limit, user_dir=args.user_dir)

if __name__ == "__main__":
    main()
