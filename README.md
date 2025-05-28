# NJ Gas Station Scraper

This tool scrapes information about gas stations from a list of addresses in a CSV file.

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Prepare your input CSV file with the following columns:
- address
- city
- state
- zip_code

4. Run the scraper:
```bash
python scraper.py input.csv output.csv
```

## Input CSV Format
The input CSV should have the following columns:
- address: Street address of the gas station
- city: City name
- state: State (e.g., NJ)
- zip_code: ZIP code

## Output
The script will generate a new CSV file with all the scraped information, including:
- Original address information
- Property details
- Ownership information
- Additional metadata from the website 