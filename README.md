# Elections Scraper

A script that downloads the 2017 Czech parliamentary election results from
[volby.cz](https://www.volby.cz/pls/ps2017nss/ps3?xjazyk=CZ) for all
municipalities of one territorial unit (district) and saves them to a CSV
file.

## Installation

You need Python 3.10 or newer.

1. Create and activate a virtual environment:

   ```
   python -m venv venv
   source venv/bin/activate        # Linux / macOS
   venv\Scripts\activate           # Windows
   ```

2. Install the libraries from `requirements.txt`:

   ```
   pip install -r requirements.txt
   ```

## Usage

The script takes two required arguments:

```
python main.py "<TERRITORIAL_UNIT_URL>" <OUTPUT_FILE.csv>
```

1. **Territorial unit URL** - a link to a district from the
   [main table](https://www.volby.cz/pls/ps2017nss/ps3?xjazyk=CZ).
   Put the link in quotes.
2. **Output file name** - must end with the `.csv` extension.

If an argument is missing, the arguments are in the wrong order or the link
is not valid, the script shows a warning and exits. Run
`python main.py --help` to display the help.

### Example

Results of the Prostějov district:

```
python main.py "https://volby.gov.cz/pls/ps2017nss/ps32?xjazyk=CZ&xkraj=12&xnumnuts=7103" vysledky_prostejov.csv
```

The script prints the number of municipalities found and, when finished, the
number of municipalities saved. If a municipality cannot be downloaded, its
link is printed and a warning at the end says that the CSV is incomplete.

## Output

Each row of the CSV file contains one municipality. The columns are:

| Column        | Content                                         |
|---------------|-------------------------------------------------|
| `code`        | municipality code                               |
| `name`        | municipality name                               |
| `registered`  | registered voters                               |
| `envelopes`   | issued envelopes                                |
| `valid`       | valid votes                                     |
| other columns | one column per candidate party with its votes   |

A sample output for the Prostějov district is in `results.csv`.
