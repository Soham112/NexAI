#!/usr/bin/env python3
import os, re, json, time, argparse
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone

from bs4 import BeautifulSoup, Tag
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout, Page

USER_AGENT = "UTD-CourseBookBot/1.0 (+mailto:team@example.com)"
BASE_URL = "https://coursebook.utdallas.edu/search"
POLITE = 0.8  # seconds

KV_RE = re.compile(r"\s*([^:]+):\s*(.*)\s*")
STATUS_RE = re.compile(
    r"Enrollment Status:\s*(?P<status>\w+)"
    r"\s*Available Seats:\s*(?P<available>\d+)"
    r"\s*Enrolled Total:\s*(?P<enrolled>\d+)"
    r"\s*Waitlist:\s*(?P<waitlist>\d+)",
    re.I,
)

def proj_paths(base_dir: str | None = None) -> str:
    base_dir = base_dir or os.path.dirname(__file__)
    data_root = os.path.join(base_dir, "data")
    clean_dir = os.path.join(data_root, "clean", "coursebook")
    os.makedirs(clean_dir, exist_ok=True)
    date = datetime.now(timezone.utc).strftime("%Y%m%d")
    return os.path.join(clean_dir, f"sections_{date}.jsonl")


def _text(n: Optional[Tag]) -> Optional[str]:
    if not n:
        return None
    t = n.get_text(" ", strip=True)
    return t if t else None


def _kv_cells_to_dict(td: Tag) -> Dict[str, str]:
    """
    Parse the two-column mini tables like:
      | Class Section | MIS6382.001.25F | Instruction Mode | Face-to-Face |
    Returns a dict with normalized keys.
    """
    out: Dict[str, str] = {}
    for tr in td.select("table.courseinfo__classsubtable tr"):
        tds = tr.find_all("td")
        # rows can be 2 or 4 cells (K,V,[K,V])
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


def _parse_meetings(td: Tag) -> Tuple[Dict[str, str], List[Dict[str, str]]]:
    """
    Parse 'Class Location and Times' section:
      - header KV lines: Term, Type, Starts, Ends
      - meetings list: day/time and room link (one or more blocks)
    """
    meta = {"term": None, "session_type": None, "starts": None, "ends": None}
    meetings: List[Dict[str, str]] = []

    # top meta table (key left, value right)
    # They often appear as <strong>Term:</strong> 25F etc., or a small table.
    # First capture strong-based rows:
    for strong in td.select("strong"):
        label = strong.get_text(" ", strip=True).rstrip(":").lower()
        value = strong.next_sibling.strip() if strong.next_sibling else None
        if not value:
            # sometimes the value is wrapped
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

    # meeting blocks
    # Often a block contains date range + weekday + time + room link
    for block in td.select(".courseinfo__meeting-item--multiple, .courseinfo__datestimes"):
        block_text = _text(block)
        room_a = block.find("a", href=True)
        meetings.append({
            "text": block_text,
            "room": _text(room_a),
            "room_href": room_a["href"] if room_a else None,
        })

    return meta, meetings


def _parse_instructors(td: Tag) -> List[Dict[str, Optional[str]]]:
    people: List[Dict[str, Optional[str]]] = []
    for item in td.select("div[id^='inst-'] div"):
        txt = _text(item) or ""
        email = None
        mail = item.find("a", href=re.compile(r"^mailto:"))
        if mail:
            email = mail["href"].replace("mailto:", "")
        # Try to split role if present: "Name ・ Primary Instructor ・ email"
        parts = [p.strip() for p in re.split(r"・|\|", txt) if p.strip()]
        name = parts[0] if parts else None
        role = None
        for p in parts[1:]:
            if "instructor" in p.lower() or "assistant" in p.lower():
                role = p
                break
        people.append({"name": name, "email": email, "role": role})
    # Fallback: plain text
    if not people:
        t = _text(td)
        if t:
            people.append({"name": t, "email": None, "role": None})
    return people


def parse_expanded_overview(expanded_html: str) -> Dict:
    """
    Parse the entire Class Detail panel.
    """
    soup = BeautifulSoup(expanded_html or "", "lxml")
    tbl = soup.select_one("table.courseinfo__overviewtable")

    data = {
        # top
        "course_title": None,
        # class info kvs
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

        # status
        "enrollment_status": None,
        "available_seats": None,
        "enrolled_total": None,
        "waitlist": None,

        # long description (keep HTML to preserve emphasis/links)
        "description_html": None,

        # people
        "instructors": [],
        "tas": [],

        # schedule
        "term": None,
        "term_meta": {},          # raw meta extracted
        "meetings": [],

        # exam / college / evaluation / syllabus / register
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

    # Course Title
    title = tbl.select_one(".courseinfo__overviewtable__coursetitle")
    data["course_title"] = _text(title)

    # iterate rows
    for tr in tbl.select("tr"):
        th = _text(tr.find("th"))
        td = tr.find("td")
        if not th or not td:
            continue
        low = th.lower()

        if "class info" in low:
            kvs = _kv_cells_to_dict(td)
            # normalize common keys
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
                    # like "87209 / 015493"
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
            # Example: "Enrollment Status: OPEN   Available Seats: 29   Enrolled Total: 19   Waitlist: 0"
            s = _text(td) or ""
            m = STATUS_RE.search(s)
            if m:
                data["enrollment_status"] = m.group("status")
                data["available_seats"]   = int(m.group("available"))
                data["enrolled_total"]    = int(m.group("enrolled"))
                data["waitlist"]          = int(m.group("waitlist"))
            else:
                data["enrollment_status"] = s

        elif "description" in low:
            data["description_html"] = str(td)

        elif re.search(r"^instructor", low):
            data["instructors"] = _parse_instructors(td)

        elif re.search(r"^ta/ra", low):
            data["tas"] = _parse_instructors(td)

        elif "class location and times" in low or "schedule" in low:
            meta, meetings = _parse_meetings(td)
            data["term_meta"] = meta
            data["term"] = meta.get("term")
            data["session_type"] = data["session_type"] or meta.get("session_type")
            data["meetings"] = meetings

        elif "exams" in low:
            # Sometimes contains "Date: <...> Time: <...> Location: <... (link)>"
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

    # Orion registration link (usually at the bottom of the panel)
    reg = soup.find("a", href=True, string=re.compile("Register for this class on Orion", re.I))
    if reg:
        data["orion_register_href"] = reg["href"]

    return data


def wait_for_results(page: Page) -> None:
    try:
        page.wait_for_selector("#searchresults", state="visible", timeout=12000)
        return
    except PWTimeout:
        pass
    try:
        page.wait_for_selector("table >> text=Class Title", timeout=7000)
        return
    except PWTimeout:
        page.wait_for_timeout(800)


def looks_logged_in(page: Page) -> bool:
    try:
        txt = page.locator("#pauth_menu").inner_text(timeout=1500)
        return "LOGIN" not in (txt or "").upper()
    except Exception:
        return False


def scrape(query: str = "now mis6382", user_dir: str = ".pw-user", base_dir: str | None = None,
           limit: int = 50, headless: bool = False) -> str:

    out_jsonl = proj_paths(base_dir)

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_dir,
            headless=headless,
            user_agent=USER_AGENT,
            viewport={"width": 1280, "height": 900},
        )
        page = ctx.new_page()

        # 1) open UI
        page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)
        time.sleep(POLITE)

        # 2) login/captcha if needed
        need_login = (not looks_logged_in(page)) or page.locator("iframe[title='reCAPTCHA']").count() > 0
        if need_login:
            print("\n=== Action required ===")
            print("Log in with your NetID (and complete reCAPTCHA) in the browser window.")
            input("When you're on the search page and logged in, press ENTER here to continue... ")
            page.reload(wait_until="domcontentloaded")
            time.sleep(POLITE)

        # 3) submit query
        box = page.locator("input#srch") if page.locator("input#srch").count() else page.get_by_placeholder("Search for classes")
        box.fill(query)
        time.sleep(POLITE/2)
        page.keyboard.press("Enter")

        wait_for_results(page)
        time.sleep(POLITE)

        # 4) rows
        rows = page.locator("#sr table tbody tr.cb-row")
        total = min(rows.count(), limit)

        for i in range(total):
            row = rows.nth(i)
            # safe reads
            section = row.locator("td").nth(1).inner_text().strip()
            class_title = row.locator("td").nth(3).inner_text().strip()

            # expand Class Detail
            btn = row.locator("button.has-cb-row-action", has_text="Class Detail")
            if btn.count() == 0:
                btn = row.locator("td button", has_text="Class Detail")
            if btn.count():
                btn.first.click()
                page.wait_for_timeout(350)

            expanded = row.evaluate_handle(
                """(r) => { const next = r.nextElementSibling;
                           if(!next) return '';
                           const td = next.querySelector('td'); return td ? td.innerHTML : ''; }"""
            )
            expanded_html = expanded.json_value() if expanded else ""
            details = parse_expanded_overview(expanded_html)

            # open syllabus tab to ensure the link appears if lazy
            tab = row.locator("button.has-cb-action.is-tab", has_text=re.compile(r"syllabus", re.I))
            if tab.count():
                tab.first.click()
                page.wait_for_timeout(300)
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
                "section": section,           # e.g., MIS 6382.001.25F
                "class_title": class_title,   # contains (3 Semester Credit Hours)
                **details
            }

            with open(out_jsonl, "a", encoding="utf-8") as f:
                f.write(json.dumps(row_json, ensure_ascii=False) + "\n")

        ctx.close()

    return out_jsonl


def main():
    ap = argparse.ArgumentParser(description="CourseBook scraper (auth) → data/clean/coursebook/sections_YYYYMMDD.jsonl")
    ap.add_argument("--query", default="now mis6382")
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--user-dir", default=".pw-user")
    ap.add_argument("--headless", action="store_true")
    args = ap.parse_args()

    base_dir = os.path.dirname(__file__)
    out_file = scrape(args.query, args.user_dir, base_dir, args.limit, headless=args.headless)
    print(f"✓ Data saved to: {os.path.abspath(out_file)}")


if __name__ == "__main__":
    main()
