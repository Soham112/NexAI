#!/usr/bin/env python3
import os
import re
import json
import time
import hashlib
import argparse
import datetime as dt
import urllib.parse as up
import urllib.robotparser as urp
from typing import Optional

import requests
from bs4 import BeautifulSoup, NavigableString, Tag

URL_DEFAULT = "https://catalog.utdallas.edu/2023/graduate/programs/jsom/information-technology-management"
USER_AGENT = "UTD-CatalogBot/1.0 (+mailto:team@example.com)"
POLITENESS_DELAY = 1.2           # seconds
TIMEOUT = 20                     # seconds
MAX_BYTES = 10 * 1024 * 1024     # 10 MB
COURSE_CODE_RE = re.compile(r"\b([A-Z]{2,4})\s?(\d{4})\b")
CREDIT_LINE_RE = re.compile(r"\b(\d+)\s+semester\s+credit\s+hours?\b", re.I)


def url_to_filename(url: str, flatten: bool = True) -> str:
    """Stable filename from URL; flatten removes path separators to avoid deep dirs."""
    parts = up.urlsplit(url)
    path = parts.path.strip("/") or "index"
    segs = []
    for seg in path.split("/"):
        seg = "".join(ch if ch.isalnum() or ch in "-_." else "-" for ch in seg).strip("-") or "x"
        segs.append(seg)
    stem = "-".join(segs) if flatten else "/".join(segs)
    if parts.query:
        qh = hashlib.sha1(parts.query.encode("utf-8")).hexdigest()[:10]
        stem = f"{stem}-{qh}"
    return f"{stem}.html"


def robots_allow(url: str, user_agent: str = USER_AGENT, timeout: int = TIMEOUT) -> bool:
    parts = up.urlsplit(url)
    robots_url = up.urljoin(f"{parts.scheme}://{parts.netloc}", "/robots.txt")
    rp = urp.RobotFileParser()
    try:
        resp = requests.get(robots_url, timeout=timeout, headers={"User-Agent": user_agent})
        if resp.status_code == 200:
            rp.parse(resp.text.splitlines())
        else:
            # default allow when robots can't be fetched
            rp.parse(["User-agent: *", "Allow: /"])
    except Exception:
        rp.parse(["User-agent: *", "Allow: /"])
    return rp.can_fetch(user_agent, url)


def fetch_requests(url: str) -> bytes:
    r = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": USER_AGENT})
    r.raise_for_status()
    return r.content


def _inline_text_after_anchor(a: Tag) -> str:
    """
    Collect inline text that immediately follows <a> (within the same line/parent),
    stopping before the next <a> or a block boundary.
    """
    pieces = []
    node = a.next_sibling

    def is_block_boundary(t: Optional[Tag]) -> bool:
        if not isinstance(t, Tag):
            return False
        # rough: break at headings, paragraphs, lists, tables, divs, and <br>
        if t.name in ("h1", "h2", "h3", "h4", "p", "ul", "ol", "table", "div"):
            return True
        return False

    while node is not None:
        if isinstance(node, NavigableString):
            pieces.append(str(node))
        elif isinstance(node, Tag):
            if node.name == "a":
                break  # next course link; stop
            if node.name == "br":
                break
            if is_block_boundary(node):
                break
            # inline tags like <em>, <span>, <strong>
            pieces.append(node.get_text(" ", strip=True))
        node = node.next_sibling

    txt = " ".join(" ".join(pieces).split())  # normalize whitespace
    # trim separators and leading "or"
    txt = txt.lstrip(" -:•·|").strip()
    if txt.lower().startswith("or "):
        txt = txt[3:].lstrip(" -:").strip()
    return txt


def parse_itm_page(html: bytes, url: str) -> dict:
    soup = BeautifulSoup(html, "lxml")

    # Page headings commonly present on UTD catalog pages
    h1 = soup.find("h1")
    h2 = soup.find("h2")

    # Find a credit-hours line like "36 semester credit hours minimum"
    credits_line = None
    for node in soup.find_all(["p", "div", "li"]):
        txt_line = node.get_text(" ", strip=True)
        if CREDIT_LINE_RE.search(txt_line):
            credits_line = txt_line
            break

    # Section harvester: Degree Requirements, Prerequisite, Course Requirements
    def get_section(regex: str):
        h3 = soup.find("h3", id=re.compile(regex, re.I)) or soup.find("h3", string=re.compile(regex, re.I))
        if not h3:
            return None
        chunks = []
        for sib in h3.find_next_siblings():
            if sib.name and sib.name.startswith("h"):
                break  # stop at next heading
            if sib.name in ("p", "ul", "ol", "table"):
                chunks.append(sib.get_text(" ", strip=True))
        return "\n".join(chunks) if chunks else None

    degree_requirements = get_section(r"degree[-\s]?requirements")
    prerequisite = get_section(r"prereq")
    course_requirements = get_section(r"course[-\s]?requirements")

    # Extract course links with code + trailing name
    courses = []
    for a in soup.find_all("a", href=True):
        link_text = a.get_text(" ", strip=True)
        m = COURSE_CODE_RE.fullmatch(link_text) or COURSE_CODE_RE.search(link_text)
        if not m:
            continue

        dept, num = m.groups()
        course_id = f"{dept} {num}"

        # If anchor includes name already, use the remainder; else try inline trailing text
        leftover = link_text[m.end():].strip(" -:")
        if leftover:
            course_name = leftover
        else:
            course_name = _inline_text_after_anchor(a) or None

        courses.append({
            "course_id": course_id,
            "course_name": course_name,
            "full_text": link_text if leftover else f"{link_text} {course_name or ''}".strip(),
            "href": up.urljoin(url, a["href"]),
        })

    # Deduplicate on (course_id, href)
    seen = set()
    deduped = []
    for c in courses:
        key = (c["course_id"], c["href"])
        if key not in seen:
            seen.add(key)
            deduped.append(c)

    return {
        "source_url": url,
        "page_title": h1.get_text(" ", strip=True) if h1 else None,
        "degree_name": h2.get_text(" ", strip=True) if h2 else None,
        "credit_hours_line": credits_line,
        "sections": {
            "degree_requirements": degree_requirements,
            "prerequisite": prerequisite,
            "course_requirements": course_requirements,
        },
        "courses_found": deduped,
    }


def main():
    ap = argparse.ArgumentParser(description="Extract UTD ITM page (requests + BeautifulSoup)")
    ap.add_argument("--url", default=URL_DEFAULT)
    ap.add_argument("--out-root", default="data")
    args = ap.parse_args()

    url = args.url

    # Prepare dirs
    date_str = dt.datetime.utcnow().strftime("%Y%m%d")
    raw_dir = os.path.join(args.out_root, "raw", "catalog", date_str)
    clean_dir = os.path.join(args.out_root, "clean", "catalog")
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(clean_dir, exist_ok=True)

    # robots + polite delay
    if not robots_allow(url):
        print("[!] Disallowed by robots.txt")
        return
    time.sleep(POLITENESS_DELAY)

    # Fetch
    t0 = time.time()
    html = fetch_requests(url)
    elapsed_ms = int((time.time() - t0) * 1000)
    if len(html) > MAX_BYTES:
        raise RuntimeError("Downloaded HTML exceeds MAX_BYTES")

    # Save raw (flattened filename so no deep folders)
    fname = url_to_filename(url, flatten=True)
    raw_path = os.path.join(raw_dir, fname)
    os.makedirs(os.path.dirname(raw_path), exist_ok=True)
    with open(raw_path, "wb") as f:
        f.write(html)

    # Parse -> JSON
    parsed = parse_itm_page(html, url)
    parsed["download_elapsed_ms"] = elapsed_ms
    clean_path = os.path.join(clean_dir, "itm_page.json")
    with open(clean_path, "w", encoding="utf-8") as f:
        json.dump(parsed, f, ensure_ascii=False, indent=2)

    print("✓ Saved raw HTML:", raw_path)
    print("✓ Wrote parsed JSON:", clean_path)


if __name__ == "__main__":
    main()
