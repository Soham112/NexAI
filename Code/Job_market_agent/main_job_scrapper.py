#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Greenhouse Job Scraper — S3 Enabled Version
Collects postings from multiple companies, saves locally and/or uploads to S3.

Usage (to write at bucket root under links/, raw/, extracted/):
  python3 job_scrape.py --limit -1 --s3 \
    --s3-bucket nexai-job-market-data \
    --s3-prefix "" \
    --aws-region us-east-1
"""

import os, re, io, sys, json, time, argparse, datetime as dt, boto3, requests
from typing import List, Dict, Optional
from pathlib import Path
from bs4 import BeautifulSoup

# ======================================================================
# CONFIG / CONSTANTS
# ======================================================================

DATE_STR = dt.date.today().strftime("%Y-%m-%d")

# ======================================================================
# UTILITY FUNCTIONS
# ======================================================================

def resolve_companies_yaml(cli_value: Optional[str]) -> str:
    """
    Locate companies.yaml even if the script is run from another directory.
    Priority:
      1) --companies-yaml value (if provided)
      2) <this_file_dir>/config/companies.yaml
      3) CWD/companies.yaml
      4) CWD/config/companies.yaml
    """
    if cli_value:
        p = Path(cli_value).expanduser().resolve()
        if not p.exists():
            raise FileNotFoundError(f"--companies-yaml not found: {p}")
        return str(p)

    here = Path(__file__).parent.resolve()
    candidates = [
        here / "config" / "companies.yaml",      # Job_market_agent/config/companies.yaml
        Path.cwd() / "companies.yaml",
        Path.cwd() / "config" / "companies.yaml",
    ]
    for c in candidates:
        if c.exists():
            return str(c.resolve())

    raise FileNotFoundError(
        "companies.yaml not found. Place it in Job_market_agent/config/ or pass --companies-yaml <path>."
    )

def load_companies(yaml_path: str) -> List[str]:
    """Load company list from YAML file (supports categories)."""
    import yaml
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    companies: List[str] = []
    for _, items in data.items():
        if isinstance(items, list):
            companies += items
        elif isinstance(items, dict):
            for _, vals in items.items():
                if isinstance(vals, list):
                    companies += vals
    # order-preserving de-dupe and drop empties
    seen, out = set(), []
    for c in companies:
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return out

def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


# ======================================================================
# S3 STORAGE CLASS
# ======================================================================

class S3Storage:
    def __init__(self, bucket: str, prefix: str, region: str):

        region = region.strip()
        if region.endswith("1") and "-" not in region:
            region = region.replace("east1", "east-1").replace("west1", "west-1")
            
        self.bucket = bucket
        self.prefix = (prefix or "").strip("/")  # allow empty -> bucket root
        self.region = region
        self.s3 = boto3.client("s3", region_name=self.region)

    def _join_key(self, *parts: str) -> str:
        segs = []
        for p in parts:
            if p is None:
                continue
            p = str(p).strip("/")
            if p:
                segs.append(p)
        return "/".join(segs)

    def _put_lines(self, key: str, lines_iter):
        buf = io.StringIO()
        for line in lines_iter:
            buf.write(line)
            if not line.endswith("\n"):
                buf.write("\n")
        body = buf.getvalue().encode("utf-8")
        self.s3.put_object(Bucket=self.bucket, Key=key, Body=body)
        print(f"✅ Uploaded → s3://{self.bucket}/{key}")
        return f"s3://{self.bucket}/{key}"

    def save_jsonl(self, filename: str, rows, folder: Optional[str] = None, add_date: bool = False):
        parts = [self.prefix]
        if folder:
            parts.append(folder)
        if add_date:
            parts.append(DATE_STR)
        parts.append(filename)
        key = self._join_key(*parts)
        lines = (json.dumps(r, ensure_ascii=False) for r in rows)
        return self._put_lines(key, lines)


# ======================================================================
# LOCAL STORAGE CLASS
# ======================================================================

class LocalStorage:
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)

    def save_jsonl(self, filename: str, rows, folder: Optional[str] = None, add_date: bool = False):
        subdir = self.base_dir
        if folder:
            subdir = os.path.join(subdir, folder)
        if add_date:
            subdir = os.path.join(subdir, DATE_STR)
        os.makedirs(subdir, exist_ok=True)

        path = os.path.join(subdir, filename)
        with open(path, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"💾 Saved → {path}")
        return path


# ======================================================================
# SCRAPER LOGIC
# ======================================================================

def get_greenhouse_urls(company: str) -> List[str]:
    """Get all job URLs from a Greenhouse company careers page (single-page scrape)."""
    urls = []
    gh_url = f"https://boards.greenhouse.io/{company}"
    try:
        r = requests.get(gh_url, timeout=10)
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.select("a[href*='/jobs/']"):
            href = a.get("href", "")
            if not href:
                continue
            if href.startswith("/"):
                href = f"https://boards.greenhouse.io{href}"
            urls.append(href)
        return list(dict.fromkeys(urls))
    except Exception as e:
        print(f"⚠️ Error fetching {company}: {e}")
        return []


def get_all_job_urls(companies: List[str], limit: int) -> List[str]:
    all_urls = []
    for company in companies:
        urls = get_greenhouse_urls(company)
        print(f"INFO: {company}: {len(urls)} matches")
        all_urls.extend(urls)
        if limit > 0 and len(all_urls) >= limit:
            break
    dedup = list(dict.fromkeys(all_urls))
    return dedup if limit <= 0 else dedup[:limit]


def fetch_job_page(url: str) -> Optional[str]:
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return r.text
    except Exception as e:
        print(f"⚠️ Error fetching {url}: {e}")
    return None


def extract_fields_from_html(html: str) -> Dict[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    h1 = soup.select_one("h1.app-title") or soup.select_one("h1")
    title = clean_text(h1.get_text() if h1 else "")
    loc_el = soup.select_one("div.location") or soup.find("span", class_="location")
    location = clean_text(loc_el.get_text()) if loc_el else ""
    dept_el = soup.select_one(".department") or soup.find("a", {"href": re.compile("departments")})
    department = clean_text(dept_el.get_text()) if dept_el else ""
    content = soup.select_one("div#content") or soup.find("div", class_="content")
    desc = clean_text(content.get_text() if content else "")
    return {
        "title": title,
        "location": location,
        "department": department,
        "description": desc
    }


def download_and_extract(urls: List[str]) -> List[Dict[str, str]]:
    results = []
    total = len(urls)
    for i, url in enumerate(urls, 1):
        html = fetch_job_page(url)
        if not html:
            continue
        data = extract_fields_from_html(html)
        data["url"] = url
        results.append(data)
        print(f"[{i}/{total}] ✓ {data['title'][:60]}")
    return results


# ======================================================================
# MAIN
# ======================================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--companies-yaml", default=None, help="Path to companies.yaml (optional)")
    parser.add_argument("--limit", type=int, default=-1, help="Global max URLs (<=0 for unlimited)")
    parser.add_argument("--s3", action="store_true", help="Enable S3 uploads")
    parser.add_argument("--s3-bucket", default=None, help="S3 bucket name")
    parser.add_argument("--s3-prefix", default="", help="S3 prefix (folder). Use '' for bucket root")
    parser.add_argument("--aws-region", default="us-east-1", help="AWS region for S3 client")
    args = parser.parse_args()

    yaml_path = resolve_companies_yaml(args.companies_yaml)
    companies = load_companies(yaml_path)
    print(f"✅ Loaded {len(companies)} companies from {yaml_path}")

    # choose storage
    if args.s3:
        if not args.s3_bucket:
            raise SystemExit("--s3 was set but --s3-bucket is missing")
        store = S3Storage(bucket=args.s3_bucket, prefix=args.s3_prefix, region=args.aws_region)
        shown_prefix = (args.s3_prefix or "").rstrip("/")
        print(f"🪣 Using S3 storage → s3://{args.s3_bucket}/{shown_prefix}")
    else:
        out_dir = os.path.join(os.getcwd(), "output")
        store = LocalStorage(out_dir)
        print(f"💾 Using local storage → {out_dir}")

    print("=" * 78)
    print("GREENHOUSE SCRAPER — ROLE AGNOSTIC")
    print("=" * 78)

    urls = get_all_job_urls(companies, args.limit)
    print(f"   → {len(urls)} URLs matched")

    print("\n[2/4] Downloading postings…")
    results = download_and_extract(urls)

    # Save data: three folders at bucket root (or under --s3-prefix if provided)
    print("\n[4/4] Writing JSONL to storage…")
    store.save_jsonl("links_all_all.jsonl",     [{"url": u} for u in urls], folder="links",     add_date=False)
    store.save_jsonl("raw_all_all.jsonl",       [{"html_url": u} for u in urls], folder="raw",  add_date=False)
    store.save_jsonl("extracted_all_all.jsonl", results,                    folder="extracted", add_date=False)

    print("\n✅ DONE")


if __name__ == "__main__":
    main()
