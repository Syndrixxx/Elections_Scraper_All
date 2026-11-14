"""Scrape the 2017 Czech election results of one territorial unit.

Usage: python main.py "<INPUT_URL>" <OUTPUT_FILE.csv>
"""

import csv
import time
from urllib.parse import parse_qs, urljoin, urlparse

import click
import requests
from bs4 import BeautifulSoup, Tag


def validate_arguments(input_url: str, output_file: str) -> None:
    """Raise a usage error if the arguments are invalid or swapped."""
    if "ps32" not in input_url or "xnumnuts=" not in input_url:
        raise click.UsageError(
            "INPUT_URL must be a link to a territorial unit (okres). "
            "Are the arguments swapped?"
        )
    if not output_file.lower().endswith(".csv"):
        raise click.UsageError("OUTPUT_FILE must be a .csv file.")


def get_soup(url: str) -> BeautifulSoup:
    """Download a page and parse it.

    Args:
        url: Address of the page.

    Returns:
        The parsed page.

    Raises:
        requests.RequestException: If the download fails.
    """
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    response.encoding = "utf-8"  # decode the Czech letters correctly
    time.sleep(0.3)  # be polite to the server
    return BeautifulSoup(response.text, "html.parser")


def to_int(tag: Tag | None) -> int | None:
    """Convert a table cell with a number like "14 990" to an int.

    Args:
        tag: The table cell, or None if it was not found.

    Returns:
        The integer, or None if the cell is missing or empty.
    """
    # Thousands are separated by (non-breaking) spaces; split() drops them.
    text = "".join(tag.get_text().split()) if tag else ""
    return int(text) if text.isdigit() else None


def get_town_links(url: str) -> list[str]:
    """Collect the links to the results of all towns in a territorial unit.

    Args:
        url: Address of the territorial unit page.

    Returns:
        Absolute URLs of the town pages (empty if there are none).
    """
    soup = get_soup(url)
    # The links in the page are relative, so make them absolute.
    return [urljoin(url, a["href"])
            for a in soup.select("td.cislo a[href^='ps311?']")]


def scrape_town(url: str) -> dict:
    """Scrape the results of one town.

    Args:
        url: Address of the results page of the town.

    Returns:
        One row for the CSV: town info plus votes of each party.

    Raises:
        requests.RequestException: If the download fails.
        ValueError: If the page contains no results.
    """
    soup = get_soup(url)
    header = soup.select_one("div.topline h3:-soup-contains('Obec:')")
    if header is None:
        raise ValueError("no results found on the page")
    row = {
        "code": parse_qs(urlparse(url).query)["xobec"][0],  # from the URL
        "name": header.get_text(strip=True).removeprefix("Obec:").strip(),
        "registered": to_int(soup.select_one("td.cislo[headers='sa2']")),
        "envelopes": to_int(soup.select_one("td.cislo[headers='sa3']")),
        "valid": to_int(soup.select_one("td.cislo[headers='sa6']")),
    }
    # Only rows with a party name; the table number in `headers` varies,
    # so match just the ending "sb3" (the votes column).
    for tr in soup.select("tr:has(td.overflow_name)"):
        party = tr.select_one("td.overflow_name").get_text(strip=True)
        row[party] = to_int(tr.select_one("td[headers$='sb3']"))
    return row


def scrape_towns(links: list[str]) -> tuple[list[dict], list[str]]:
    """Scrape all towns, printing and collecting the ones that failed.

    Args:
        links: Addresses of the town pages.

    Returns:
        The rows of the successful towns and the links that failed.
    """
    rows, failed = [], []
    for link in links:
        try:
            rows.append(scrape_town(link))
        except (requests.RequestException, ValueError) as e:
            print(f"Failed: {link} ({e})")  # carry on with the other towns
            failed.append(link)
    return rows, failed


def write_csv(rows: list[dict], output_file: str) -> None:
    """Write the rows to a CSV file that Excel opens correctly.

    Args:
        rows: One dict per town.
        output_file: Path of the CSV file to create.
    """
    # Parties differ by town, so collect the column names from all rows
    # (in first-seen order); a missing party is filled with 0 (restval).
    fieldnames = list(dict.fromkeys(key for row in rows for key in row))
    # utf-8-sig: Excel reads Czech letters; newline="": no blank rows.
    with open(output_file, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames, restval=0)
        writer.writeheader()
        writer.writerows(rows)


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("input_url", metavar="INPUT_URL")
@click.argument(
    "output_file",
    metavar="OUTPUT_FILE",
    type=click.Path(dir_okay=False, writable=True),
)
def main(input_url: str, output_file: str) -> None:
    """Scrape the 2017 election results of one territorial unit into a CSV.

    \b
    Arguments:
      INPUT_URL    Link to a territorial unit, e.g.
      https://volby.gov.cz/pls/ps2017nss/ps32?xjazyk=CZ&xkraj=12&xnumnuts=7103
      OUTPUT_FILE  Path of the CSV file to create, e.g. vysledky_prostejov.csv

    \b
    Example:
      python main.py "<INPUT_URL>" vysledky_prostejov.csv
    """
    validate_arguments(input_url, output_file)
    try:
        links = get_town_links(input_url)
    except requests.RequestException as e:
        raise click.ClickException(f"Could not download {input_url}: {e}")
    if not links:
        raise click.ClickException(f"No towns found on {input_url}")
    print(f"Found {len(links)} towns.")
    rows, failed = scrape_towns(links)
    if not rows:
        raise click.ClickException("No data to write.")
    write_csv(rows, output_file)
    print(f"Saved {len(rows)} towns to {output_file}.")
    if failed:
        print(f"WARNING: {len(failed)} towns failed, the CSV is incomplete.")


if __name__ == "__main__":
    main()