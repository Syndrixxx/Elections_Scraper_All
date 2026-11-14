"""Scrape the 2017 Czech parliamentary election results into a CSV."""

import csv
import time
from urllib.parse import parse_qs, urljoin, urlparse

import click
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from requests_cache import CachedSession
from tqdm import tqdm
from urllib3.util.retry import Retry

BASE = "https://volby.gov.cz/pls/ps2017nss/"
USER_AGENT = "ElectionsScraper/0.1 (+https://github.com/Syndrixxx/Elections_Scraper_All)"
failed = set()
session = CachedSession("cache")
session.headers["User-Agent"] = USER_AGENT
# Retry dropped connections and server errors, waiting longer each time.
retry = Retry(total=3, backoff_factor=2, raise_on_status=False,
              status_forcelist=[500, 502, 503, 504])
session.mount("https://", HTTPAdapter(max_retries=retry))


def fetch(url: str) -> str | None:
    """Download a page and record the URL in `failed` if that fails.

    Args:
        url: Address of the page to download.

    Returns:
        The page HTML, or None if the download failed.
    """
    try:
        response = session.get(url, timeout=10)
        if not response.from_cache:
            time.sleep(0.5)  # pause only for real downloads, not the cache
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
    failed.add(url)  # reached only after an error, success returns above
    return None


def get_soup(url: str) -> BeautifulSoup | None:
    """Download a page and parse it.

    Args:
        url: Address of the page.

    Returns:
        The parsed page, or None if the download failed.
    """
    html = fetch(url)
    return BeautifulSoup(html, "html.parser") if html else None


def get_links(url: str, selector: str) -> list[str]:
    """Collect the unique absolute URLs of links matching a selector.

    Args:
        url: Address of the page to search.
        selector: CSS selector of the <a href> elements to collect.

    Returns:
        The URLs in page order, or an empty list if there are none.
    """
    html = fetch(url)
    if html is None:
        return []
    soup = BeautifulSoup(html, "html.parser")
    links = []

    for item in soup.select(selector):
        try:
            full_url = urljoin(url, item["href"])  # hrefs are relative
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
    """Return the cleaned text of the first element matching a selector.

    Args:
        soup: Parsed page to search.
        selector: CSS selector of the element.

    Returns:
        The text without surrounding whitespace, or None if no match.
    """
    tag = soup.select_one(selector)
    return tag.get_text(" ", strip=True) if tag else None


def to_int(text: str | None) -> int | None:
    """Convert a number with spaces as thousands separators to an int.

    Args:
        text: Text such as "14 990"; the space may be non-breaking.

    Returns:
        The integer, or None if the text is empty or missing.
    """
    try:
        return int("".join(text.split())) if text else None
    except ValueError:
        return None


def get_votes(soup: BeautifulSoup) -> dict[str, int | None]:
    """Read the votes of every party from the results page of one town.

    Args:
        soup: Parsed results page of the town.

    Returns:
        Mapping of party name to the number of votes it received.
    """
    votes = {}
    for row in soup.select("tr:has(td.overflow_name)"):  # party rows only
        party = row.select_one("td.overflow_name").get_text(strip=True)
        cell = row.select_one("td[headers$='sb3']")  # table number varies
        votes[party] = to_int(cell.get_text()) if cell else None
    return votes


def write_csv(rows: list[dict], output_file: str) -> None:
    """Write the results to a CSV file that Excel opens correctly.

    Args:
        rows: One dict per town; a party missing in a row counts as 0.
        output_file: Path of the CSV file to create.
    """
    if not rows:
        tqdm.write("No data to write.")
        return
    # Keys of all rows in first-seen order; parties differ by region.
    fieldnames = list(dict.fromkeys(key for row in rows for key in row))
    # utf-8-sig: Excel reads Czech letters; newline="": no blank rows.
    with open(output_file, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, restval=0)
        writer.writeheader()
        writer.writerows(rows)


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("input_url", metavar="INPUT_URL")
@click.argument(
    "output_file",
    metavar="OUTPUT_FILE",
    type=click.Path(dir_okay=False, writable=True),
)
@click.option(
    "--refresh",
    is_flag=True,
    help="Delete the cached pages and download everything again.",
)
def main(input_url: str, output_file: str, refresh: bool) -> None:
    """Scrape the 2017 election results of all towns into a CSV file.

    \b
    Arguments:
      INPUT_URL    Main results page, e.g.
                   https://www.volby.cz/pls/ps2017nss/ps2?xjazyk=CZ
      OUTPUT_FILE  Path of the CSV file to create, e.g. results.csv

    \b
    Example:
      python main.py "<INPUT_URL>" results.csv --refresh

    \f
    Args:
        input_url: Address of the main results page.
        output_file: Path of the CSV file to create.
        refresh: Whether to clear the cache before scraping.
    """
    if refresh:
        session.cache.clear()
    district_links = get_links(input_url, "td[headers$='sa3'] a[href*='ps32']")
    town_links = [BASE + "ps361?xjazyk=CZ"]  # votes from abroad
    for district_link in tqdm(district_links, desc="Districts"):
        town_links += get_links(district_link, "td.cislo a[href^='ps311?']")
    tqdm.write(f"Found {len(town_links)} town pages.")

    rows = []
    for town_link in tqdm(town_links, desc="Towns"):
        soup = get_soup(town_link)
        if soup is None:
            continue
        query = parse_qs(urlparse(town_link).query)  # values are lists
        code = int(query.get("xobec", ["0"])[0])  # abroad has no xobec: 0
        header = get_text(soup, "div.topline h3:-soup-contains('Obec:')")
        name = "Zahraničí" if code == 0 else header
        valid = to_int(get_text(soup, "td.cislo[headers='sa6']"))
        if valid is None or not name:  # skip pages without results
            tqdm.write(f"No results found: {town_link}")
            failed.add(town_link)
            continue
        rows.append({
            "code": code,
            "name": name.removeprefix("Obec: "),
            "registered": to_int(get_text(soup, "td.cislo[headers='sa2']")),
            "envelopes": to_int(get_text(soup, "td.cislo[headers='sa3']")),
            "valid": valid,
            **get_votes(soup),  # one extra column per party
        })

    write_csv(rows, output_file)
    if failed:
        print(f"WARNING: {len(failed)} pages failed, the CSV is incomplete:")
        for url in sorted(failed):
            print(url)


if __name__ == "__main__":
    main()

