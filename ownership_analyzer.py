import pandas as pd
import re

def normalize_owner_name_and_address(owner_info):
    """Extract and normalize the owner name and mailing address from the full owner info."""
    # Regex to match the business name and suffix (LLC, INC, CORP, LTD, etc.), then the mailing address
    match = re.match(r'^(.*?)(?:,\s*(LLC|INC|CORP(?:ORATION)?|LTD|LIMITED))\b(?:,\s*)?(.*)$', owner_info, re.IGNORECASE)
    if match:
        base = match.group(1).strip()
        suffix = match.group(2)
        address = match.group(3).strip()
        name = f"{base} {suffix.upper()}"
        # Clean up address (remove leading/trailing commas and spaces)
        address = re.sub(r'^,+', '', address).strip()
    else:
        # Fallback: just use everything before the first comma as name, rest as address
        parts = owner_info.split(',', 1)
        name = parts[0].strip()
        address = parts[1].strip() if len(parts) > 1 else ''
    # Convert to uppercase and remove extra spaces
    name = ' '.join(name.upper().split())
    # Standardize common business entity suffixes
    name = re.sub(r'\bCORPORATION\b', 'CORP', name)
    name = re.sub(r'\bLIMITED\b', 'LTD', name)
    return name, address

def analyze_ownership(csv_file):
    """Analyze property ownership history from CSV file."""
    # Read the CSV file
    df = pd.read_csv(csv_file)
    # Get the current owner and mailing address (from the most recent year)
    current_owner, mailing_address = normalize_owner_name_and_address(df.iloc[0]['Owner Info'])
    current_year = df.iloc[0]['Year']
    # Find the ownership start year
    ownership_start_year = None
    for _, row in df.iterrows():
        owner, _ = normalize_owner_name_and_address(row['Owner Info'])
        if owner != current_owner:
            break
        ownership_start_year = row['Year']
    # Calculate years owned
    years_owned = current_year - ownership_start_year + 1
    return {
        "owner": current_owner,
        "mailing_address": mailing_address,
        "ownership_start_year": ownership_start_year,
        "current_year": current_year,
        "years_owned": years_owned
    }

if __name__ == "__main__":
    # Analyze ownership for each property
    results = analyze_ownership('test_results.csv')
    # Print results
    print("\nOwnership Analysis:")
    print(f"Current Owner: {results['owner']}")
    print(f"Mailing Address: {results['mailing_address']}")
    print(f"Ownership Start Year: {results['ownership_start_year']}")
    print(f"Current Year: {results['current_year']}")
    print(f"Years Owned: {results['years_owned']}") 