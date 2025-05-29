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

def analyze_ownership(filename):
    df = pd.read_csv(filename)
    required_columns = ['Address', 'City', 'State', 'Zip Code', 'Year', 'Owner Info']
    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    # Group by property
    group_cols = ['Address', 'City', 'State', 'Zip Code']
    results = []
    for group_keys, group in df.groupby(group_cols):
        group = group.sort_values('Year', ascending=False)
        current_owner, mailing_address = normalize_owner_name_and_address(group.iloc[0]['Owner Info'])
        current_year = int(group.iloc[0]['Year'])
        # Find the earliest year the current owner appears
        years_owned = 1
        start_year = current_year
        for _, row in group.iterrows():
            owner, _ = normalize_owner_name_and_address(row['Owner Info'])
            year = int(row['Year'])
            if owner == current_owner:
                start_year = year
                years_owned = current_year - start_year + 1
            else:
                break
        results.append({
            'Address': group_keys[0],
            'City': group_keys[1],
            'State': group_keys[2],
            'Zip Code': group_keys[3],
            'Current Owner': current_owner,
            'Mailing Address': mailing_address,
            'Ownership Start Year': start_year,
            'Current Year': current_year,
            'Years Owned': years_owned
        })
    return results

if __name__ == "__main__":
    results = analyze_ownership('test_results.csv')
    print("Ownership Analysis:")
    for r in results:
        print(f"\nProperty: {r['Address']}, {r['City']}, {r['State']} {r['Zip Code']}")
        print(f"Current Owner: {r['Current Owner']}")
        print(f"Mailing Address: {r['Mailing Address']}")
        print(f"Ownership Start Year: {r['Ownership Start Year']}")
        print(f"Current Year: {r['Current Year']}")
        print(f"Years Owned: {r['Years Owned']}") 