"""
Scraper for West Bengal 2026 Assembly Election results from ECI via Wayback Machine.

ECI direct access returns 403 (Akamai WAF). We use Wayback Machine snapshots from
~20260505, when all 293 constituencies had declared results.
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import json
import os
import re
from pathlib import Path

WAYBACK_BASE = "https://web.archive.org/web"
ECI_BASE = "https://results.eci.gov.in/ResultAcGenMay2026"

# Use a timestamp safely past result declaration (5am May 5 IST = 2026-05-04 23:30 UTC)
WAYBACK_TS = "20260505010000"

STATEWISE_PAGES = 15
TOTAL_SEATS = 294
SKIP_SEATS = {144}  # Falta — repoll on May 21, not yet declared

CACHE_DIR = Path("cache")
OUTPUT_DIR = Path(".")


def get_session():
    s = requests.Session()
    s.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    })
    return s


def fetch_with_retry(session, url, retries=4, delay=3):
    for attempt in range(retries):
        try:
            resp = session.get(url, timeout=30)
            if resp.status_code == 200 and len(resp.text) > 500:
                return resp.text
            if resp.status_code == 429:
                wait = delay * (2 ** attempt)
                print(f"  Rate limited, waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"  HTTP {resp.status_code} for {url}")
                time.sleep(delay)
        except requests.RequestException as e:
            print(f"  Request error ({attempt+1}/{retries}): {e}")
            time.sleep(delay * (attempt + 1))
    return None


def wayback_url(path, ts=WAYBACK_TS):
    return f"{WAYBACK_BASE}/{ts}/{ECI_BASE}/{path}"


def cached_fetch(session, cache_key, url, delay=2.0):
    CACHE_DIR.mkdir(exist_ok=True)
    cache_file = CACHE_DIR / f"{cache_key}.html"
    if cache_file.exists():
        return cache_file.read_text(encoding="utf-8")
    print(f"  Fetching: {url}")
    time.sleep(delay)
    html = fetch_with_retry(session, url)
    if html:
        cache_file.write_text(html, encoding="utf-8")
    return html


# ---------------------------------------------------------------------------
# Statewise pages (summary: winner, runner-up, margin per constituency)
# ---------------------------------------------------------------------------

def _party_from_cell(cell):
    """Extract party name from a cell that contains a nested tooltip table."""
    nested = cell.find("table")
    if nested:
        first_td = nested.find("td")
        if first_td:
            return first_td.get_text(strip=True)
    return cell.get_text(strip=True).split("i")[0].strip()


def parse_statewise_row(row):
    # Use recursive=False so nested table <td>s are not counted as siblings
    cells = row.find_all("td", recursive=False)
    if len(cells) < 8:
        return None
    const_name = cells[0].get_text(strip=True)
    if not const_name or const_name in ("Constituency", "Status Known"):
        return None
    try:
        const_no = int(cells[1].get_text(strip=True))
    except ValueError:
        return None

    winner_name = cells[2].get_text(strip=True)
    winner_party = _party_from_cell(cells[3])
    runner_name = cells[4].get_text(strip=True)
    runner_party = _party_from_cell(cells[5])

    try:
        margin = int(cells[6].get_text(strip=True).replace(",", ""))
    except ValueError:
        margin = None

    status = cells[8].get_text(strip=True) if len(cells) > 8 else ""

    return {
        "const_no": const_no,
        "const_name": const_name,
        "winner_name": winner_name,
        "winner_party": winner_party,
        "runner_name": runner_name,
        "runner_party": runner_party,
        "margin": margin,
        "status": status,
    }


def scrape_statewise(session):
    records = []
    for page_num in range(1, STATEWISE_PAGES + 1):
        path = f"statewiseS25{page_num}.htm"
        html = cached_fetch(session, f"statewise_{page_num}", wayback_url(path), delay=2.5)
        if not html:
            print(f"  WARNING: Could not fetch statewise page {page_num}")
            continue
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")
        if not tables:
            print(f"  WARNING: No tables in statewise page {page_num}")
            continue
        main_table = tables[0]
        rows = main_table.find_all("tr")
        page_count = 0
        for row in rows:
            rec = parse_statewise_row(row)
            if rec:
                records.append(rec)
                page_count += 1
        print(f"  Statewise page {page_num}: {page_count} constituencies")

    df = pd.DataFrame(records)
    print(f"\nTotal from statewise pages: {len(df)} constituencies")
    return df


# ---------------------------------------------------------------------------
# Candidateswise pages (per-candidate vote counts)
# ---------------------------------------------------------------------------

PARTY_ALIASES = {
    "bharatiya janata party": "BJP",
    "bjp": "BJP",
    "all india trinamool congress": "TMC",
    "aitc": "TMC",
    "trinamool congress": "TMC",
    "indian national congress": "INC",
    "inc": "INC",
    "communist party of india (marxist)": "CPI(M)",
    "cpi(m)": "CPI(M)",
    "cpi-m": "CPI(M)",
    "independent": "IND",
    "none of the above": "NOTA",
    "aam janata unnayan party": "AJUP",
    "all india secular front": "AISF",
    "socialist unity centre of india (communist)": "SUCI(C)",
}


def normalize_party(name):
    key = name.lower().strip()
    for alias, canonical in PARTY_ALIASES.items():
        if alias in key:
            return canonical
    return name.strip()


def parse_candidateswise(html, const_no):
    soup = BeautifulSoup(html, "html.parser")

    # Title: "Assembly Constituency N - NAME (West Bengal)"
    title_div = soup.find("div", class_="page-title")
    const_name = ""
    if title_div:
        m = re.search(r"Assembly Constituency\s+\d+\s*-\s*([A-Z\s\(\)]+)\s*\(West Bengal\)", title_div.get_text())
        if m:
            const_name = m.group(1).strip()

    candidates = []
    bjp_votes = 0
    tmc_votes = 0
    total_votes = 0

    cand_boxes = soup.find_all("div", class_="cand-box")
    for box in cand_boxes:
        nme_prty = box.find("div", class_="nme-prty")
        if not nme_prty:
            continue

        # Structure: <h5>CANDIDATE NAME</h5><h6>Party Name</h6>
        h5 = nme_prty.find("h5")
        h6 = nme_prty.find("h6")
        cand_name  = h5.get_text(strip=True) if h5 else ""
        party_name = h6.get_text(strip=True) if h6 else ""

        # Votes are in <div class="cand-info"> → <div class="status ..."> →
        # second <div> child: "143242 <span>(+ 70420)</span>"
        votes = 0
        cand_info = box.find("div", class_="cand-info")
        if cand_info:
            status_div = cand_info.find("div", class_="status")
            if status_div:
                vote_divs = status_div.find_all("div", recursive=False)
                # vote_divs[0] = "won"/"lost", vote_divs[1] = vote count + margin
                if len(vote_divs) >= 2:
                    # Extract only the direct text (not the span with margin)
                    vote_text = vote_divs[1].get_text(separator=" ", strip=True)
                    m = re.search(r"^([\d,]+)", vote_text)
                    if m:
                        try:
                            votes = int(m.group(1).replace(",", ""))
                        except ValueError:
                            pass

        party_norm = normalize_party(party_name)
        total_votes += votes
        if party_norm == "BJP":
            bjp_votes += votes
        elif party_norm == "TMC":
            tmc_votes += votes

        candidates.append({
            "name": cand_name,
            "party": party_name,
            "party_norm": party_norm,
            "votes": votes,
        })

    return {
        "const_no": const_no,
        "const_name_cw": const_name,
        "bjp_votes": bjp_votes,
        "tmc_votes": tmc_votes,
        "total_votes": total_votes,
        "candidates": candidates,
    }


def scrape_candidateswise(session, const_numbers):
    results = []
    total = len(const_numbers)
    for i, n in enumerate(const_numbers):
        path = f"candidateswise-S25{n}.htm"
        html = cached_fetch(session, f"cand_{n}", wayback_url(path), delay=2.5)
        if not html:
            print(f"  [{i+1}/{total}] Constituency {n}: FAILED")
            results.append({"const_no": n, "bjp_votes": None, "tmc_votes": None, "total_votes": None})
            continue
        rec = parse_candidateswise(html, n)
        status = f"BJP={rec['bjp_votes']:,} TMC={rec['tmc_votes']:,} Total={rec['total_votes']:,}" if rec["total_votes"] else "parse error"
        print(f"  [{i+1}/{total}] Constituency {n} ({rec['const_name_cw']}): {status}")
        results.append(rec)

    return results


# ---------------------------------------------------------------------------
# Main scrape entry point
# ---------------------------------------------------------------------------

def run_scrape():
    session = get_session()

    print("=" * 60)
    print("PHASE 1: Scraping statewise summary pages")
    print("=" * 60)
    statewise_df = scrape_statewise(session)
    statewise_df.to_csv("statewise_raw.csv", index=False)
    print(f"Saved statewise_raw.csv ({len(statewise_df)} rows)")

    const_numbers = sorted(
        [n for n in statewise_df["const_no"].tolist() if n not in SKIP_SEATS]
    )
    print(f"\n{len(const_numbers)} constituencies to scrape candidateswise data for")

    print("\n" + "=" * 60)
    print("PHASE 2: Scraping candidateswise vote counts")
    print("=" * 60)
    cand_results = scrape_candidateswise(session, const_numbers)

    # Build candidateswise dataframe (drop candidates list for CSV)
    cand_rows = []
    for rec in cand_results:
        cand_rows.append({
            "const_no": rec["const_no"],
            "const_name_cw": rec.get("const_name_cw", ""),
            "bjp_votes": rec.get("bjp_votes"),
            "tmc_votes": rec.get("tmc_votes"),
            "total_votes": rec.get("total_votes"),
        })
    cand_df = pd.DataFrame(cand_rows)
    cand_df.to_csv("candidateswise_raw.csv", index=False)
    print(f"\nSaved candidateswise_raw.csv ({len(cand_df)} rows)")

    # Merge
    df = statewise_df.merge(cand_df, on="const_no", how="left")

    # Derived columns
    df["winner_is_bjp"] = df["winner_party"].str.contains("Bharatiya Janata", na=False)
    df["winner_is_tmc"] = df["winner_party"].str.contains("Trinamool", na=False)

    # Where we couldn't parse votes, estimate from margin
    # Winner votes = runner_up votes + margin = (total_votes + margin) / 2
    # (only possible if total_votes known)
    mask_missing_bjp = df["bjp_votes"].isna()
    print(f"\nConstituencies with missing vote data: {mask_missing_bjp.sum()}")

    df.to_csv("wb_2026_results.csv", index=False)
    print(f"Saved wb_2026_results.csv ({len(df)} rows)")
    return df


if __name__ == "__main__":
    run_scrape()
