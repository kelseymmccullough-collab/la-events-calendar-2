"""
LA Events Calendar - Selenium-Based Scraper v6
Added Vidiots to the scraper
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from datetime import datetime
import json
import re
import time

def setup_driver():
    """Set up Selenium Chrome driver with options to appear more human-like"""
    
    chrome_options = Options()
    
    # Run in headless mode (required for server)
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    # Make it look more like a real browser
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Try to use system Chrome in Docker, fallback to ChromeDriverManager
    try:
        # For Docker/production environment
        service = Service('/usr/bin/chromedriver')
        driver = webdriver.Chrome(service=service, options=chrome_options)
    except:
        # For local development
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # Execute script to hide webdriver property
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver


def scrape_vista_theater():
    """Scrape film screenings from Vista Theater ticketing website"""
    
    url = "https://ticketing.uswest.veezi.com/sessions/?siteToken=20xhpa3yt2hhkwt4zjvfcwsaww"
    venue_name = "The Vista Theater"
    venue_short = "Vista"
    event_type = "film"
    
    print(f"Scraping {venue_name}...")
    
    driver = None
    try:
        driver = setup_driver()
        driver.get(url)
        time.sleep(5)
        
        print(f"  Page loaded successfully")
        
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        events = []
        current_year = datetime.now().year
        
        # Find all headers (h2, h3, h4 tags)
        all_headers = soup.find_all(['h2', 'h3', 'h4'])
        
        print(f"  Found {len(all_headers)} header elements")
        
        for header in all_headers:
            title = header.get_text(strip=True)
            
            if not title or len(title) < 3:
                continue
            
            # Skip venue name
            if 'vista' in title.lower() and 'theater' in title.lower():
                continue
            
            # Skip if title STARTS with a day of the week (these are date headers)
            days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
            if any(title.lower().startswith(day) for day in days):
                continue
            
            # Skip common UI text
            skip_terms = ['select', 'choose', 'tickets', 'sessions', 'showtimes', 'book now']
            if any(term in title.lower() for term in skip_terms):
                continue
            
            # Get surrounding text from parent container
            parent = header.find_parent()
            if not parent:
                continue
            
            section_text = parent.get_text()
            
            # Look for date: "Thursday 22, January" or just "22, January"
            date_pattern = r'(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)?\s*(\d{1,2}),?\s+(January|February|March|April|May|June|July|August|September|October|November|December)'
            date_match = re.search(date_pattern, section_text, re.I)
            
            # Look for time: "7:15 PM"
            time_pattern = r'(\d{1,2}:\d{2}\s*(?:am|pm))'
            time_match = re.search(time_pattern, section_text, re.I)
            
            if date_match and time_match:
                day = int(date_match.group(1))
                month_name = date_match.group(2)
                month_num = datetime.strptime(month_name, '%B').month
                date_str = f"{current_year}-{month_num:02d}-{day:02d}"
                
                time_str = time_match.group(1).upper()
                
                event = {
                    "title": title,
                    "venue": venue_name,
                    "venueShort": venue_short,
                    "type": event_type,
                    "date": date_str,
                    "time": time_str,
                    "description": ""
                }
                events.append(event)
                print(f"    Found: {title} on {date_str} at {time_str}")
        
        print(f"✓ Successfully scraped {len(events)} events from {venue_name}")
        return events
        
    except Exception as e:
        print(f"✗ Error scraping {venue_name}: {e}")
        return []
    finally:
        if driver:
            driver.quit()


def scrape_new_beverly():
    """Scrape film screenings from New Beverly Cinema website"""
    
    url = "https://thenewbev.com/schedule/"
    venue_name = "The New Beverly Theater"
    venue_short = "New Bev"
    event_type = "film"
    
    print(f"Scraping {venue_name}...")
    
    driver = None
    try:
        driver = setup_driver()
        driver.get(url)
        time.sleep(3)
        
        print(f"  Page loaded successfully")
        
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        events = []
        current_year = datetime.now().year
        
        event_cards = soup.find_all('h4')
        
        print(f"  Found {len(event_cards)} potential event cards")
        
        for title_tag in event_cards:
            try:
                title = title_tag.get_text(strip=True)
                
                if not title or len(title) < 3:
                    continue
                
                # Only go up 2 parent levels (not 3) to stay within this movie's card
                parent = title_tag.find_parent()
                for _ in range(2):
                    if parent and parent.find_parent():
                        parent = parent.find_parent()
                
                if not parent:
                    continue
                
                section_text = parent.get_text()
                
                # Look for date pattern with day of week: "Fri, January 23"
                date_pattern = r'(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*,?\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})'
                date_match = re.search(date_pattern, section_text, re.I)
                
                if date_match:
                    month_name = date_match.group(1)
                    day = int(date_match.group(2))
                    month_num = datetime.strptime(month_name, '%B').month
                    date_str = f"{current_year}-{month_num:02d}-{day:02d}"
                else:
                    continue
                
                time_pattern = r'(\d{1,2}:\d{2}\s*(?:am|pm))'
                times = re.findall(time_pattern, section_text, re.I)
                
                if times:
                    time_str = times[0].upper()
                else:
                    time_str = "7:30 PM"
                
                event = {
                    "title": title,
                    "venue": venue_name,
                    "venueShort": venue_short,
                    "type": event_type,
                    "date": date_str,
                    "time": time_str,
                    "description": ""
                }
                events.append(event)
                print(f"    Found: {title} on {date_str} at {time_str}")
                
            except Exception as e:
                continue
        
        print(f"✓ Successfully scraped {len(events)} events from {venue_name}")
        return events
        
    except Exception as e:
        print(f"✗ Error scraping {venue_name}: {e}")
        return []
    finally:
        if driver:
            driver.quit()


def scrape_vidiots():
    """Scrape film screenings from Vidiots website"""
    
    url = "https://vidiotsfoundation.org/coming-soon/"
    venue_name = "Vidiots"
    venue_short = "Vidiots"
    event_type = "film"
    
    print(f"Scraping {venue_name}...")
    
    driver = None
    try:
        driver = setup_driver()
        driver.get(url)
        time.sleep(5)
        
        print(f"  Page loaded successfully")
        
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        events = []
        current_year = datetime.now().year
        
        # Movie titles are in h2 tags
        all_headers = soup.find_all('h2')
        
        print(f"  Found {len(all_headers)} h2 elements")
        
        for header in all_headers:
            title = header.get_text(strip=True)
            
            if not title or len(title) < 3:
                continue
            
            # Only skip the main page header, not movie titles
            if title.lower() == 'coming soon to vidiots':
                continue
            
            # Get the parent - go up just 1 level to stay in the movie card
            parent = header.find_parent()
            if not parent:
                continue
            
            # Go up 1 more level to get full movie card
            if parent.find_parent():
                parent = parent.find_parent()
            
            section_text = parent.get_text()
            
            # Look for date patterns - "Sat, Jan 24" format
            date_pattern = r'(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*,?\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2})'
            date_match = re.search(date_pattern, section_text, re.I)
            
            if date_match:
                # Convert abbreviated month to full month
                month_abbr = date_match.group(1).capitalize()
                month_map = {
                    'Jan': 'January', 'Feb': 'February', 'Mar': 'March', 'Apr': 'April',
                    'May': 'May', 'Jun': 'June', 'Jul': 'July', 'Aug': 'August',
                    'Sep': 'September', 'Oct': 'October', 'Nov': 'November', 'Dec': 'December'
                }
                month_name = month_map.get(month_abbr[:3], month_abbr)
                day = int(date_match.group(2))
                month_num = datetime.strptime(month_name, '%B').month
                date_str = f"{current_year}-{month_num:02d}-{day:02d}"
            else:
                continue
            
            # Look for time
            time_pattern = r'(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))'
            time_match = re.search(time_pattern, section_text, re.I)
            
            if time_match:
                time_str = time_match.group(1).upper()
            else:
                continue
            
            event = {
                "title": title,
                "venue": venue_name,
                "venueShort": venue_short,
                "type": event_type,
                "date": date_str,
                "time": time_str,
                "description": ""
            }
            events.append(event)
            print(f"    Found: {title} on {date_str} at {time_str}")
        
        print(f"✓ Successfully scraped {len(events)} events from {venue_name}")
        return events
        
    except Exception as e:
        print(f"✗ Error scraping {venue_name}: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        if driver:
            driver.quit()


def scrape_all_venues():
    """Scrape all venues and combine events"""
    
    print("=" * 60)
    print("Starting LA Events Calendar Scraper v6")
    print("=" * 60)
    print()
    
    all_events = []
    
    # Vista Theater, New Beverly, and Vidiots
    venues = [
        scrape_vista_theater,
        scrape_new_beverly,
        scrape_vidiots
    ]
    
    for scraper in venues:
        events = scraper()
        all_events.extend(events)
        print()
        time.sleep(2)
    
    # Filter out past events
    today = datetime.now().date()
    future_events = []
    past_events_count = 0
    
    for event in all_events:
        try:
            event_date = datetime.strptime(event['date'], '%Y-%m-%d').date()
            if event_date >= today:
                future_events.append(event)
            else:
                past_events_count += 1
        except:
            future_events.append(event)
    
    if past_events_count > 0:
        print(f"Filtered out {past_events_count} past events")
    
    # Remove duplicates (same title, venue, date, and time)
    unique_events = []
    seen = set()
    duplicates_count = 0
    
    for event in future_events:
        # Create a unique key for each event
        key = (event['title'], event['venue'], event['date'], event['time'])
        if key not in seen:
            seen.add(key)
            unique_events.append(event)
        else:
            duplicates_count += 1
    
    if duplicates_count > 0:
        print(f"Removed {duplicates_count} duplicate events")
    
    print("=" * 60)
    print(f"Total unique upcoming events: {len(unique_events)}")
    print("=" * 60)
    
    return unique_events


def save_events_to_json(events, filename='events.json'):
    """Save events to a JSON file"""
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(events, f, indent=2, ensure_ascii=False)
        print(f"\n✓ Events saved to {filename}")
        return True
    except Exception as e:
        print(f"\n✗ Error saving events: {e}")
        return False


if __name__ == "__main__":
    print("LA Events Calendar Scraper v6")
    print("Vista Theater + New Beverly + Vidiots\n")
    
    events = scrape_all_venues()
    save_events_to_json(events)
    
    print("\nDone! Check events.json for the results.")
