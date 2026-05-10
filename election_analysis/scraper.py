"""
Generic ECI election results scraper using Wayback Machine.

ECI direct access often returns 403 (Akamai WAF). We use Wayback Machine
snapshots captured shortly after result declaration.
"""
from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Optional

import pandas as pd
import requests
from bs4 import BeautifulSoup

from .models import ElectionConfig

WAYBACK_BASE = "https://web.archive.org/web"


class ECIScraper:
    """
    Generic scraper for ECI election results.
    Fetches statewise summary pages and candidateswise vote-count pages,
    then merges them into a single DataFrame.
    """

    def __init__(
        self,
        config: ElectionConfig,
        cache_dir: Path = Path("cache"),
        fetch_delay: float = 2.5,
    ) -> None:
        self.config = config
        self.cache_dir = cache_dir
        self.fetch_delay = fetch_delay
        self._session = self._make_session()

        # Build the ECI base URL for this election
        state = config.state_name.replace(" ", "")
        self._eci_base = (
            f"https://results.eci.gov.in/ResultAcGen{state}{config.year}"
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def scrape(self) -> pd.DataFrame:
        """
        Run both scrape phases and return the merged DataFrame.
        Saves intermediate CSVs: statewise_raw.csv, candidateswise_raw.csv,
        and the merged wb_2026_results.csv (named after state/year).
        """
        cfg = self.config

        print("=" * 60)
        print(f"PHASE 1: Scraping statewise summary pages ({cfg.state_name} {cfg.year})")
        print("=" * 60)
        statewise_df = self.scrape_statewise()
        statewise_df.to_csv("statewise_raw.csv", index=False)
        print(f"Saved statewise_raw.csv ({len(statewise_df)} rows)")

        const_numbers = sorted(
            [n for n in statewise_df["const_no"].tolist() if n not in cfg.skip_seats]
        )
        print(f"\n{len(const_numbers)} constituencies to scrape candidateswise data for")

        print("\n" + "=" * 60)
        print("PHASE 2: Scraping candidateswise vote counts")
        print("=" * 60)
        cand_df = self.scrape_candidateswise(const_numbers)
        cand_df.to_csv("candidateswise_raw.csv", index=False)
        print(f"\nSaved candidateswise_raw.csv ({len(cand_df)} rows)")

        # Merge
        df = statewise_df.merge(cand_df[["const_no", "party_a_votes", "party_b_votes", "total_votes"]], on="const_no", how="left")

        # Derived columns
        df["winner_is_party_a"] = df["winner_party"].str.contains(cfg.party_a_name, na=False)
        df["winner_is_party_b"] = df["winner_party"].str.contains(cfg.party_b_name, na=False)

        missing = df["party_a_votes"].isna()
        print(f"\nConstituencies with missing vote data: {missing.sum()}")

        out_csv = f"{cfg.state_name.lower().replace(' ', '_')}_{cfg.year}_results.csv"
        df.to_csv(out_csv, index=False)
        print(f"Saved {out_csv} ({len(df)} rows)")
        return df

    def scrape_statewise(self) -> pd.DataFrame:
        """Scrape statewise summary pages and return DataFrame."""
        cfg = self.config
        records = []
        for page_num in range(1, cfg.statewise_pages + 1):
            path = f"statewise{cfg.state_code}{page_num}.htm"
            html = self._cached_fetch(f"statewise_{page_num}", self._wayback_url(path))
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
                rec = self._parse_statewise_row(row)
                if rec:
                    records.append(rec)
                    page_count += 1
            print(f"  Statewise page {page_num}: {page_count} constituencies")

        df = pd.DataFrame(records)
        print(f"\nTotal from statewise pages: {len(df)} constituencies")
        return df

    def scrape_candidateswise(self, const_numbers: list) -> pd.DataFrame:
        """Scrape candidateswise vote-count pages and return DataFrame."""
        results = []
        total = len(const_numbers)
        for i, n in enumerate(const_numbers):
            path = f"candidateswise-{self.config.state_code}{n}.htm"
            html = self._cached_fetch(f"cand_{n}", self._wayback_url(path))
            if not html:
                print(f"  [{i+1}/{total}] Constituency {n}: FAILED")
                results.append({
                    "const_no": n,
                    "party_a_votes": None,
                    "party_b_votes": None,
                    "total_votes": None,
                })
                continue
            rec = self._parse_candidateswise(html, n)
            a_label = self.config.party_a_label
            b_label = self.config.party_b_label
            status = (
                f"{a_label}={rec['party_a_votes']:,} {b_label}={rec['party_b_votes']:,} "
                f"Total={rec['total_votes']:,}"
                if rec["total_votes"]
                else "parse error"
            )
            print(f"  [{i+1}/{total}] Constituency {n} ({rec.get('const_name_cw', '')}): {status}")
            results.append({
                "const_no": rec["const_no"],
                "party_a_votes": rec.get("party_a_votes"),
                "party_b_votes": rec.get("party_b_votes"),
                "total_votes": rec.get("total_votes"),
            })

        return pd.DataFrame(results)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _wayback_url(self, path: str) -> str:
        ts = self.config.wayback_timestamp
        return f"{WAYBACK_BASE}/{ts}/{self._eci_base}/{path}"

    def _make_session(self) -> requests.Session:
        s = requests.Session()
        s.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        })
        return s

    def _cached_fetch(self, cache_key: str, url: str) -> Optional[str]:
        self.cache_dir.mkdir(exist_ok=True)
        cache_file = self.cache_dir / f"{cache_key}.html"
        if cache_file.exists():
            return cache_file.read_text(encoding="utf-8")
        print(f"  Fetching: {url}")
        time.sleep(self.fetch_delay)
        html = self._fetch_with_retry(url)
        if html:
            cache_file.write_text(html, encoding="utf-8")
        return html

    def _fetch_with_retry(self, url: str, retries: int = 4) -> Optional[str]:
        delay = 3
        for attempt in range(retries):
            try:
                resp = self._session.get(url, timeout=30)
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

    def _parse_statewise_row(self, row) -> Optional[dict]:
        """Parse a single statewise table row into a record dict."""
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

        winner_name  = cells[2].get_text(strip=True)
        winner_party = self._party_from_cell(cells[3])
        runner_name  = cells[4].get_text(strip=True)
        runner_party = self._party_from_cell(cells[5])

        try:
            margin = int(cells[6].get_text(strip=True).replace(",", ""))
        except ValueError:
            margin = None

        status = cells[8].get_text(strip=True) if len(cells) > 8 else ""

        return {
            "const_no":    const_no,
            "const_name":  const_name,
            "winner_name": winner_name,
            "winner_party": winner_party,
            "runner_name": runner_name,
            "runner_party": runner_party,
            "margin":      margin,
            "status":      status,
        }

    @staticmethod
    def _party_from_cell(cell) -> str:
        """Extract party name from a cell that may contain a nested tooltip table."""
        nested = cell.find("table")
        if nested:
            first_td = nested.find("td")
            if first_td:
                return first_td.get_text(strip=True)
        return cell.get_text(strip=True).split("i")[0].strip()

    def _normalize_party(self, name: str) -> str:
        """Normalize a raw party name using config.party_aliases."""
        key = name.lower().strip()
        for alias, canonical in self.config.party_aliases.items():
            if alias in key:
                return canonical
        return name.strip()

    def _parse_candidateswise(self, html: str, const_no: int) -> dict:
        """Parse a candidateswise HTML page and return vote counts."""
        soup = BeautifulSoup(html, "html.parser")
        cfg = self.config

        title_div = soup.find("div", class_="page-title")
        const_name = ""
        if title_div:
            m = re.search(
                r"Assembly Constituency\s+\d+\s*-\s*([A-Z\s\(\)]+)\s*\(" + re.escape(cfg.state_name) + r"\)",
                title_div.get_text(),
            )
            if m:
                const_name = m.group(1).strip()

        party_a_votes = 0
        party_b_votes = 0
        total_votes = 0

        cand_boxes = soup.find_all("div", class_="cand-box")
        for box in cand_boxes:
            nme_prty = box.find("div", class_="nme-prty")
            if not nme_prty:
                continue

            h5 = nme_prty.find("h5")
            h6 = nme_prty.find("h6")
            party_name = h6.get_text(strip=True) if h6 else ""

            votes = 0
            cand_info = box.find("div", class_="cand-info")
            if cand_info:
                status_div = cand_info.find("div", class_="status")
                if status_div:
                    vote_divs = status_div.find_all("div", recursive=False)
                    if len(vote_divs) >= 2:
                        vote_text = vote_divs[1].get_text(separator=" ", strip=True)
                        m = re.search(r"^([\d,]+)", vote_text)
                        if m:
                            try:
                                votes = int(m.group(1).replace(",", ""))
                            except ValueError:
                                pass

            party_norm = self._normalize_party(party_name)
            total_votes += votes
            if party_norm == cfg.party_a_label:
                party_a_votes += votes
            elif party_norm == cfg.party_b_label:
                party_b_votes += votes

        return {
            "const_no":      const_no,
            "const_name_cw": const_name,
            "party_a_votes": party_a_votes,
            "party_b_votes": party_b_votes,
            "total_votes":   total_votes,
        }
