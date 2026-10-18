import csv
import time
from urllib.parse import parse_qs, urljoin, urlparse

import click
import requests
from bs4 import BeautifulSoup
from requests_cache import CachedSession
from tqdm import tqdm


input_url = "https://volby.gov.cz/pls/ps2017nss/ps3?xjazyk=CZ"
input_csv_file_location = "results.csv"
session = CachedSession("cache")
session.headers["User-Agent"] = "ElectionsScraper/0.1 (+https://github.com/Syndrixxx/Elections_Scraper_All)"
BASE = "https://volby.gov.cz/pls/ps2017nss/"
failed = set()


def fetch(url: str) -> str | None:
    try:
        response = session.get(url, timeout=10)
        if not response.from_cache:
            time.sleep(0.5)
        response.raise_for_status()
        response.encoding = "utf-8"
        return response.text
    except requests.HTTPError as e:
        tqdm.write(f"HTTP error {e.response.status_code}: {url}")
    except requests.Timeout:
        tqdm.write(f"Request timed out: {url}")
    except requests.ConnectionError:
        tqdm.write(f"Connection error: {url}")
    except requests.RequestException as e:
        tqdm.write(f"Failed to fetch {url}: {e}")
    time.sleep(2)
    failed.add(url)
    return None


def get_links(url: str, selector: str) -> list[str]:
    html = fetch(url)
    if html is None:
        return []
    soup = BeautifulSoup(html, "html.parser")
    links = []

    for item in soup.select(selector):
        try:
            full_url = urljoin(url, item["href"])
        except (KeyError, ValueError):
            tqdm.write(f"Skipping an invalid link on {url}")
            continue
        if full_url not in links:
            links.append(full_url)

    if not links:
        tqdm.write(f"No links found on {url} for selector: {selector}")
        failed.add(url)
    return links


def get_text(soup: BeautifulSoup, selector: str) -> str | None:
    tag = soup.select_one(selector)
    return tag.get_text(" ", strip=True) if tag else None


def get_soup(url: str) -> BeautifulSoup | None:
    html = fetch(url)
    return BeautifulSoup(html, "html.parser") if html else None


def to_int(text: str | None) -> int | None:
    return int("".join(text.split())) if text else None


def get_votes(soup: BeautifulSoup) -> dict[str, int | None]:
    votes = {}
    for row in soup.select("tr:has(td.overflow_name)"):
        party = row.select_one("td.overflow_name").get_text(strip=True)
        cell = row.select_one("td[headers$='sb3']")
        votes[party] = to_int(cell.get_text()) if cell else None
    return votes


def write_csv(rows: list[dict], output_file: str) -> None:
    if not rows:
        tqdm.write("No data to write.")
        return
    fieldnames = list(dict.fromkeys(key for row in rows for key in row))
    with open(output_file, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, restval=0)
        writer.writeheader()
        writer.writerows(rows)


@click.command()
@click.argument("input_url")
@click.argument("output_file")
def main(input_url: str, output_file: str) -> None:
    district_links = get_links(input_url, "td[headers$='sa3'] a[href*='ps32']")
    town_links = [BASE + "ps361?xjazyk=CZ"]
    for district_link in tqdm(district_links, desc="Districts"):
        town_links += get_links(district_link, "td[class~='cislo'][headers~='t1sa1'][headers~='t1sb1'] a[href]")

    rows = []
    for town_link in tqdm(town_links, desc="Towns"):
        soup = get_soup(town_link)
        if soup is None:
            continue
        code = int(parse_qs(urlparse(town_link).query).get("xobec", ["0"])[0])
        raw_name = get_text(soup, "div.topline h3:-soup-contains('Obec:')") or ""
        name = "Zahraničí" if code == 0 else raw_name.removeprefix("Obec: ")
        rows.append({
            "code": code,
            "name": name,
            "registered": to_int(get_text(soup, "td[class~='cislo'][headers='sa2']")),
            "envelopes": to_int(get_text(soup, "td[class~='cislo'][headers='sa3']")),
            "valid": to_int(get_text(soup, "td[class~='cislo'][headers='sa6']")),
            **get_votes(soup),
        })

    write_csv(rows, output_file)
    if failed:
        print(f"WARNING: {len(failed)} pages failed, the CSV is incomplete:")
        for url in sorted(failed):
            print(url)


if __name__ == "__main__":
    main()
