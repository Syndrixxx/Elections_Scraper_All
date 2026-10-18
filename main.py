import csv
import time
from urllib.parse import urljoin

import click
import requests
from bs4 import BeautifulSoup
from requests_cache import CachedSession
from tqdm import tqdm

input_url = "https://volby.gov.cz/pls/ps2017nss/ps3?xjazyk=CZ"
input_csv_file_location = "results.csv"
session = CachedSession("cache")
BASE = "https://volby.gov.cz/pls/ps2017nss/"
failed = []


def fetch(url: str) -> str | None:
    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.HTTPError as e:
        tqdm.write(f"HTTP error {e.response.status_code}: {url}")
    except requests.Timeout:
        tqdm.write(f"Request timed out: {url}")
    except requests.ConnectionError:
        tqdm.write(f"Connection error: {url}")
    except requests.RequestException as e:
        tqdm.write(f"Failed to fetch {url}: {e}")
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

while True:
    region_links = get_links(input_url, "td[class~='center'][headers~='t2sa3'] a[href]")
    for region_link in region_links:
        district_links = get_links(region_link, "td[class~='cislo'][headers~='t1sa1'][headers~='t1sb1'] a[href]")
        for district_link in district_links:
            break

    break