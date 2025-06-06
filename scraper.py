import pandas as pd
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from webdriver_manager.chrome import ChromeDriverManager
import time
import sys
import logging
from typing import Dict, Any
import os
from dotenv import load_dotenv
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoSuchElementException
import re

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class GasStationScraper:
    def __init__(self):
        self.setup_selenium()
        self.base_url = "https://oprs.co.monmouth.nj.us/oprs/GoogleWithUC/Default.aspx"
        self.street_abbreviations = {
            'LN': ['LANE'],
            'ST': ['STREET'],
            'AVE': ['AVENUE'],
            'RD': ['ROAD'],
            'RT': ['ROUTE', 'HWY', 'HIGHWAY', 'US HIGHWAY', 'US HWY'],
            'HWY': ['HIGHWAY', 'ROUTE', 'US HIGHWAY', 'US HWY'],
            'DR': ['DRIVE'],
            'BLVD': ['BOULEVARD'],
            'CT': ['COURT'],
            'PL': ['PLACE'],
            'CIR': ['CIRCLE'],
            'TER': ['TERRACE'],
            'PKWY': ['PARKWAY'],
            'SQ': ['SQUARE'],
            'EXPY': ['EXPRESSWAY'],
            'FWY': ['FREEWAY']
        }
        
    def setup_selenium(self):
        """Initialize Selenium WebDriver with appropriate options."""
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # Run in headless mode
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        # Use webdriver_manager to automatically manage ChromeDriver
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )
        
    def _format_street_name(self, address: str) -> str:
        """Convert street name abbreviations to their full forms."""
        words = address.split()
        formatted_words = []
        for word in words:
            # Convert to uppercase for comparison
            word_upper = word.upper()
            if word_upper in self.street_abbreviations:
                formatted_words.append(self.street_abbreviations[word_upper])
            else:
                formatted_words.append(word)
        return ' '.join(formatted_words)
        
    def get_property_details(self, address: str, city: str, state: str, zip_code: str) -> Dict[str, Any]:
        """
        Scrape property details for a given address from Monmouth County OPRS.
        Tries all abbreviation and full street type variants if needed.
        """
        # Try as given (no formatting)
        details = self._search_property(address, city, state, zip_code)
        if details:
            return details

        abbr_map = self.street_abbreviations
        # Build reverse map: full form -> list of abbreviations
        rev_map = {}
        for abbr, alts in abbr_map.items():
            for alt in alts:
                alt_upper = alt.upper()
                if alt_upper not in rev_map:
                    rev_map[alt_upper] = []
                rev_map[alt_upper].append(abbr)
        words = address.split()
        tried = set()
        tried.add(address.upper())
        # Try all abbr->full alternatives
        for i, word in enumerate(words):
            word_upper = word.upper()
            if word_upper in abbr_map:
                for alt in abbr_map[word_upper]:
                    new_words = words.copy()
                    new_words[i] = alt
                    alt_address = ' '.join(new_words)
                    if alt_address.upper() not in tried:
                        logger.info(f"Retrying with full form: {alt_address}")
                        details = self._search_property(alt_address, city, state, zip_code)
                        if details:
                            return details
                        tried.add(alt_address.upper())
        # Try all full->abbr alternatives
        for i, word in enumerate(words):
            word_upper = word.upper()
            if word_upper in rev_map:
                for abbr in rev_map[word_upper]:
                    new_words = words.copy()
                    new_words[i] = abbr
                    alt_address = ' '.join(new_words)
                    if alt_address.upper() not in tried:
                        logger.info(f"Retrying with abbreviation: {alt_address}")
                        details = self._search_property(alt_address, city, state, zip_code)
                        if details:
                            return details
                        tried.add(alt_address.upper())
        # If all fail
        return None

    def _search_property(self, address, city, state, zip_code):
        """
        The main property search logic. Returns details dict if found, else None.
        """
        try:
            # Do NOT format the address here; use as-is for retry logic
            logger.info(f"Searching for property: {address}, {city}, {state} {zip_code}")
            self.driver.get(self.base_url)
            logger.info("Navigated to base URL")
            try:
                tabbernav = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "tabbernav"))
                )
                logger.info("Found tabbernav element")
                logger.info(f"Tabbernav HTML: {tabbernav.get_attribute('outerHTML')}")
            except TimeoutException:
                logger.error("Could not find tabbernav element")
                return None
            try:
                address_tab = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'By Address')]"))
                )
                address_tab.click()
                logger.info("Clicked By Address tab")
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//li[contains(@class, 'tabberactive')]//a[contains(text(), 'By Address')]"))
                )
                logger.info("By Address tab is now active")
                time.sleep(2)
                self.driver.switch_to.default_content()
                def tab1_visible(driver):
                    tab1 = driver.find_element(By.ID, "tab1")
                    return tab1.is_displayed() and "tabbertabhide" not in tab1.get_attribute("class")
                WebDriverWait(self.driver, 10).until(tab1_visible)
                logger.info("By Address tab content is visible")
                township_dropdown = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_ddlMunicp1"))
                )
                logger.info("Township dropdown found and clickable (By Address tab)")
                address_input = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_txtAddress"))
                )
                logger.info("Address input found (By Address tab)")
                address_input.clear()
                address_input.send_keys(address)
                logger.info(f"Entered street address: {address}")
                township_select = Select(township_dropdown)
                logger.info("Available township options:")
                for option in township_select.options:
                    logger.info(f"  - {option.text}")
                proper_case_city = city.title()
                logger.info(f"Attempting to select township: {proper_case_city}")
                try:
                    township_select.select_by_visible_text(proper_case_city)
                except Exception as e:
                    logger.error(f"Could not select township '{proper_case_city}'. Available options were printed above.")
                    return None
                search_button = self.driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_btnSearch1")
                search_button.click()
                logger.info("Clicked search button (By Address tab)")
                try:
                    logger.info(f"Current URL before waiting: {self.driver.current_url}")
                    WebDriverWait(self.driver, 20).until(
                        lambda driver: "PropertyDtls.aspx" in driver.current_url
                    )
                    logger.info(f"Redirected to property details page: {self.driver.current_url}")
                    time.sleep(3)
                    page_source = self.driver.page_source
                    if "No matching property record found" in page_source:
                        logger.warning("No results found for the search")
                        return None
                    elif "ctl00_ContentPlaceHolder1_PrimPropInfo_gvDtls" in page_source:
                        logger.info("Found property details table by ID in page source")
                        property_details = self._extract_property_details()
                        return {
                            'address': address,
                            'city': city,
                            'state': state,
                            'zip_code': zip_code,
                            'property_details': property_details,
                        }
                    else:
                        logger.error("Could not determine if results were found")
                        return None
                except TimeoutException:
                    logger.error("Timeout waiting for property details page")
                    return None
            except TimeoutException as e:
                logger.error(f"Timeout while waiting for elements after clicking By Address tab: {str(e)}")
                return None
            except Exception as e:
                logger.error(f"Error during tab navigation: {str(e)}")
                return None
        except Exception as e:
            logger.error(f"Error scraping property {address}, {city}, {state} {zip_code}: {str(e)}")
            return None
            
    def _extract_property_details(self) -> Dict[str, Any]:
        """Extract property details from the search results page."""
        try:
            # Try to find the table by its id first
            try:
                property_table = self.driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_PrimPropInfo_gvDtls")
                logger.info("Found property details table by ID 'ctl00_ContentPlaceHolder1_PrimPropInfo_gvDtls'")
            except Exception:
                # Fallback to the old method if not found
                logger.warning("Could not find property details table by ID, falling back to class 'propertyDetails'")
                property_table = self.driver.find_element(By.CLASS_NAME, "propertyDetails")
            
            details = {}
            rows = property_table.find_elements(By.TAG_NAME, "tr")
            for row in rows:
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) >= 2:
                    key = cells[0].text.strip()
                    value = cells[1].text.strip()
                    details[key] = value
            return details
        except Exception as e:
            logger.error(f"Error extracting property details: {str(e)}")
            return {}
            
    def _extract_ownership_info(self) -> Dict[str, Any]:
        """Extract ownership information from the property page."""
        try:
            ownership_info = {}
            ownership_table = self.driver.find_element(By.CLASS_NAME, "ownershipInfo")
            rows = ownership_table.find_elements(By.TAG_NAME, "tr")
            
            for row in rows:
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) >= 2:
                    key = cells[0].text.strip()
                    value = cells[1].text.strip()
                    ownership_info[key] = value
                    
            return ownership_info
            
        except Exception as e:
            logger.error(f"Error extracting ownership info: {str(e)}")
            return {}
            
    def _extract_metadata(self) -> Dict[str, Any]:
        """Extract additional metadata from the property page."""
        try:
            metadata = {}
            metadata_table = self.driver.find_element(By.CLASS_NAME, "metadata")
            rows = metadata_table.find_elements(By.TAG_NAME, "tr")
            
            for row in rows:
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) >= 2:
                    key = cells[0].text.strip()
                    value = cells[1].text.strip()
                    metadata[key] = value
                    
            return metadata
            
        except Exception as e:
            logger.error(f"Error extracting metadata: {str(e)}")
            return {}
            
    def close(self):
        """Close the Selenium WebDriver."""
        if hasattr(self, 'driver'):
            self.driver.quit()

    def get_tax_list_history(self) -> list:
        """
        After searching for the property and landing on the details page, extract the property ID from the hidden input with id 'ctl00_ContentPlaceHolder1_hdnPID' and use it for the ShowMod4.aspx?p=... URL when extracting the Tax List History.
        """
        tax_list = []
        try:
            # Get the property ID from the hidden input on the property details page
            try:
                property_id_elem = self.driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_hdnPID")
                property_id = property_id_elem.get_attribute("value")
                logger.info(f"Extracted property ID from hidden input: {property_id}")
            except Exception as e:
                logger.error(f"Could not extract property ID from hidden input: {str(e)}")
                return tax_list
            
            # Construct the Assessment and Sales URL
            assessment_url = f"https://oprs.co.monmouth.nj.us/oprs/GoogleWithUC/FramePage.aspx?tab=2&id={property_id}"
            logger.info(f"Navigating to Assessment and Sales page: {assessment_url}")
            
            # Navigate to the Assessment and Sales page
            self.driver.get(assessment_url)
            time.sleep(2)  # Wait for page to load
            
            # Switch to the 'frmPage' iframe
            WebDriverWait(self.driver, 10).until(
                EC.frame_to_be_available_and_switch_to_it((By.ID, "frmPage"))
            )
            logger.info("Switched to iframe 'frmPage'")
            
            # Switch to the 'rightFrame' frame
            self.driver.switch_to.frame("rightFrame")
            logger.info("Switched to frame 'rightFrame'")
            
            # Now navigate to the ShowMod4.aspx page in rightFrame using the numeric property ID
            mod4_url = f"https://oprs.co.monmouth.nj.us/oprs/GoogleWithUC/ShowMod4.aspx?p={property_id}"
            self.driver.get(mod4_url)
            logger.info(f"Navigated to {mod4_url} in rightFrame")
            time.sleep(2)  # Wait for page to load

            current_page = 1
            while True:
                # Find the Tax List History table
                table = self.driver.find_element(By.ID, "gvwMod4")
                logger.info(f"Found Tax List History table by id 'gvwMod4' on page {current_page}")
                
                # Extract data from current page
                rows = table.find_elements(By.XPATH, ".//tr[contains(@class, 'itemstyle') or contains(@class, 'altitemstyle')]")
                for row in rows:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 5:
                        tax_list.append({
                            "Year": cells[0].text.strip(),
                            "Owner Info": cells[1].text.strip(),
                            "Land/Imp/Tot": cells[2].text.strip(),
                            "Exemption": cells[3].text.strip(),
                            "Assessed": cells[4].text.strip(),
                        })
                logger.info(f"Extracted rows from page {current_page}")

                # Find pagination links in the last row
                try:
                    pagination_row = table.find_element(By.XPATH, ".//tr[@align='left']")
                    page_links = pagination_row.find_elements(By.TAG_NAME, "a")
                except Exception:
                    page_links = []
                
                found_next = False
                for link in page_links:
                    try:
                        page_num = int(link.text.strip())
                        if page_num == current_page + 1:
                            self.driver.execute_script("arguments[0].scrollIntoView();", link)
                            link.click()
                            time.sleep(1)  # Wait for page to load
                            current_page += 1
                            found_next = True
                            break
                    except ValueError:
                        continue  # Not a page number
                if not found_next:
                    logger.info("No next page link found; reached last page.")
                    break

            # Switch back to default content
            self.driver.switch_to.default_content()
            
        except Exception as e:
            logger.error(f"Error extracting Tax List History: {str(e)}")
            try:
                self.driver.switch_to.default_content()
            except:
                pass
            
        return tax_list

def save_results(results, output_file):
    results_df = pd.DataFrame(results)
    results_df = results_df.rename(columns={
        'address': 'Address',
        'city': 'City',
        'state': 'State',
        'zip_code': 'Zip Code'
    })
    # Ensure ZIP codes are treated as strings with leading zeros
    results_df['Zip Code'] = results_df['Zip Code'].astype(str).str.zfill(5)
    results_df.to_csv(output_file, index=False)

def main():
    if len(sys.argv) != 3:
        print("Usage: python scraper.py input.csv output.csv")
        sys.exit(1)
        
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    try:
        # Read input CSV
        df = pd.read_csv(input_file)
        required_columns = ['address', 'city', 'state', 'zip_code']
        
        # Validate input CSV
        if not all(col in df.columns for col in required_columns):
            raise ValueError(f"Input CSV must contain these columns: {required_columns}")
            
        results = []
        for index, row in df.iterrows():
            logger.info(f"Processing property {index + 1} of {len(df)}")
            scraper = GasStationScraper()  # New browser for each property
            try:
                details = scraper.get_property_details(
                    row['address'],
                    row['city'],
                    row['state'],
                    row['zip_code']
                )
                if details:
                    tax_history = scraper.get_tax_list_history()
                    if tax_history:
                        for tax_row in tax_history:
                            flat_row = {
                                'address': row['address'],
                                'city': row['city'],
                                'state': row['state'],
                                'zip_code': row['zip_code'],
                            }
                            if isinstance(details.get('property_details'), dict):
                                for k, v in details['property_details'].items():
                                    flat_row[k] = v
                            if isinstance(details.get('ownership_info'), dict):
                                for k, v in details['ownership_info'].items():
                                    flat_row[f'owner_{k}'] = v
                            if isinstance(details.get('metadata'), dict):
                                for k, v in details['metadata'].items():
                                    flat_row[f'meta_{k}'] = v
                            for k, v in tax_row.items():
                                flat_row[k] = v
                            results.append(flat_row)
                    else:
                        flat_row = {
                            'address': row['address'],
                            'city': row['city'],
                            'state': row['state'],
                            'zip_code': row['zip_code'],
                        }
                        if isinstance(details.get('property_details'), dict):
                            for k, v in details['property_details'].items():
                                flat_row[k] = v
                        if isinstance(details.get('ownership_info'), dict):
                            for k, v in details['ownership_info'].items():
                                flat_row[f'owner_{k}'] = v
                        if isinstance(details.get('metadata'), dict):
                            for k, v in details['metadata'].items():
                                flat_row[f'meta_{k}'] = v
                        results.append(flat_row)
                else:
                    # If details is None, output a row with just the input data and empty fields for the rest
                    flat_row = {
                        'address': row['address'],
                        'city': row['city'],
                        'state': row['state'],
                        'zip_code': row['zip_code'],
                        'Year': '',
                        'Owner Info': '',
                        'Assessed': '',
                    }
                    results.append(flat_row)
            finally:
                scraper.close()
            time.sleep(2)
        
        # Save results to CSV
        save_results(results, output_file)
        logger.info(f"Results saved to {output_file}")
        
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python scraper.py input.csv output.csv")
        sys.exit(1)
    main() 