import pandas as pd
import re

def normalize_owner_name_and_address(owner_info):
    """Extract and normalize the owner name and mailing address from the full owner info."""
    if not isinstance(owner_info, str) or not owner_info.strip():
        return '', ''
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
    required_columns = ['Address', 'City', 'State', 'Zip Code', 'Year', 'Owner Info', 'Assessed']
    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    # Read the original input file to get Site Names and preserve order
    input_df = pd.read_csv('addresses.csv')
    site_names = dict(zip(input_df['address'].str.upper(), input_df['Site Name']))

    # Group the results by property for fast lookup
    group_cols = ['Address', 'City', 'State', 'Zip Code']
    grouped = {tuple(str(x).upper() for x in k): v for k, v in df.groupby(group_cols)}

    results = []
    for _, input_row in input_df.iterrows():
        addr = input_row['address']
        city = input_row['city']
        state = input_row['state']
        zip_code = str(input_row['zip_code'])
        site_name = input_row['Site Name']  # Always use the input file's site name
        group_key = tuple(str(x).upper() for x in [addr, city, state, zip_code])
        group = grouped.get(group_key)
        if group is not None:
            group = group.sort_values('Year', ascending=False)
            first_row = group.iloc[0]
            # If all key columns are missing/empty, output empty fields for calculated columns
            if (
                (not isinstance(first_row.get('Year', ''), str) and pd.isna(first_row.get('Year', '')))
                and (not isinstance(first_row.get('Owner Info', ''), str) or not str(first_row.get('Owner Info', '')).strip())
                and (not isinstance(first_row.get('Assessed', ''), str) and pd.isna(first_row.get('Assessed', '')))
            ):
                results.append({
                    'Site Name': site_name,
                    'Address': addr,
                    'City': city,
                    'State': state,
                    'Zip Code': zip_code,
                    'Owner Info': '',
                    'Mailing Address': '',
                    'Ownership Start Year': '',
                    'Current Year': '',
                    'Years Owned': '',
                    'Assessed': ''
                })
                continue
            current_owner, mailing_address = normalize_owner_name_and_address(first_row['Owner Info'])
            current_year = int(first_row['Year'])
            current_assessed = first_row['Assessed']
            years_owned = 1
            start_year = current_year
            for _, row in group.iterrows():
                owner, _ = normalize_owner_name_and_address(row['Owner Info'])
                year = row['Year']
                if not isinstance(year, str) and pd.isna(year):
                    continue
                year = int(year)
                if owner == current_owner:
                    start_year = year
                    years_owned = current_year - start_year + 1
                else:
                    break
            results.append({
                'Site Name': site_name,
                'Address': addr,
                'City': city,
                'State': state,
                'Zip Code': zip_code,
                'Owner Info': current_owner,
                'Mailing Address': mailing_address,
                'Ownership Start Year': start_year,
                'Current Year': current_year,
                'Years Owned': years_owned,
                'Assessed': current_assessed
            })
        else:
            # No group found, output empty row
            results.append({
                'Site Name': site_name,
                'Address': addr,
                'City': city,
                'State': state,
                'Zip Code': zip_code,
                'Owner Info': '',
                'Mailing Address': '',
                'Ownership Start Year': '',
                'Current Year': '',
                'Years Owned': '',
                'Assessed': ''
            })

    # Convert results to DataFrame and save to CSV
    results_df = pd.DataFrame(results)
    output_file = 'ownership_analysis.csv'
    results_df.to_csv(output_file, index=False)
    print(f"\nAnalysis saved to {output_file}")
    
    # Print summary
    print("\nOwnership Analysis Summary:")
    for r in results:
        print(f"\nSite Name: {r['Site Name']}")
        print(f"Property: {r['Address']}, {r['City']}, {r['State']} {r['Zip Code']}")
        print(f"Owner Info: {r['Owner Info']}")
        print(f"Mailing Address: {r['Mailing Address']}")
        print(f"Ownership Start Year: {r['Ownership Start Year']}")
        print(f"Current Year: {r['Current Year']}")
        print(f"Years Owned: {r['Years Owned']}")
        print(f"Assessed Value: {r['Assessed']}")
    
    return results

if __name__ == "__main__":
    results = analyze_ownership('addresses_results.csv') 