# Elections Scraper

Command-line tool that scrapes the results of the 2017 Czech parliamentary
election for every municipality from [volby.gov.cz](https://volby.gov.cz/)
and saves them into a single CSV file.

## Features

- Downloads the results of all municipalities plus votes from abroad
  (about 6,300 pages).
- Caches downloaded pages, so a repeated run is fast and does not load the
  server again.
- Retries failed requests with a growing delay.
- Reports pages that could not be downloaded, so you know when the CSV is
  incomplete.
- Writes the CSV in `utf-8-sig`, so Excel opens Czech letters correctly.

## Requirements

- Python 3.10 or newer
- Packages: `requests`, `requests-cache`, `beautifulsoup4`, `tqdm`, `click`

## Installation

```bash
git clone https://github.com/Syndrixxx/Elections_Scraper_All.git
cd Elections_Scraper_All
python -m venv .venv
```

Activate the virtual environment:

```bash
# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Linux / macOS
source .venv/bin/activate
```

Install the packages:

```bash
pip install requests requests-cache beautifulsoup4 tqdm click
```

## Usage

```bash
python main.py INPUT_URL OUTPUT_FILE [--refresh]
```

| Argument | Description |
| --- | --- |
| `INPUT_URL` | Main results page with the list of districts. |
| `OUTPUT_FILE` | Path of the CSV file to create. |
| `--refresh` | Delete the cached pages and download everything again. |

Example:

```bash
python main.py "https://volby.gov.cz/pls/ps2017nss/ps3?xjazyk=CZ" results.csv
```

The first run takes a few minutes. Later runs read pages from the cache.
Show the built-in help with `python main.py -h`.

## Output

One row per municipality (and one row for votes from abroad):

| Column | Meaning |
| --- | --- |
| `code` | Municipality code (`0` for abroad). |
| `name` | Municipality name (`Zahraničí` for abroad). |
| `registered` | Number of registered voters. |
| `envelopes` | Number of issued envelopes. |
| `valid` | Number of valid votes. |
| other columns | Votes for each party, one column per party. |

A party that did not run in a given region has `0` in its column.

## Notes

- The tool downloads only publicly available results. Please do not lower the
  pause between requests, to avoid overloading the server.
- If some pages fail, the tool prints a warning with their URLs at the end.
  Run it again, since the successfully downloaded pages are served from the
  cache.

## Data source

Czech Statistical Office, [volby.gov.cz](https://volby.gov.cz/).
