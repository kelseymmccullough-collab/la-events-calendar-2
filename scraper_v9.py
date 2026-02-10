"""
LA Events Calendar - Selenium-Based Scraper v9
Added Academy Museum to the scraper
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
    default_url = "https://ticketing.uswest.veezi.com/sessions/?siteToken=20xhpa3yt2hhkwt4zjvfcwsaww"
    
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
                
                # Try to find a link - look for <a> tags in the parent
                event_url = default_url
                links = parent.find_all('a', href=True)
                for link in links:
                    href = link.get('href', '')
                    # Look for purchase links
                    if 'purchase' in href or 'siteToken' in href:
                        if href.startswith('http'):
                            event_url = href
                        else:
                            event_url = f"https://ticketing.uswest.veezi.com{href}"
                        break
                
                event = {
                    "title": title,
                    "venue": venue_name,
                    "venueShort": venue_short,
                    "type": event_type,
                    "date": date_str,
                    "time": time_str,
                    "description": "",
                    "url": event_url
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
    default_url = "https://thenewbev.com/schedule/"
    
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
                
                # Try to find the event URL - look for link on the title
                event_url = default_url
                # Check if h4 is inside an <a> tag
                link_parent = title_tag.find_parent('a', href=True)
                if link_parent:
                    href = link_parent.get('href', '')
                    if href.startswith('http'):
                        event_url = href
                    elif href.startswith('/'):
                        event_url = f"https://thenewbev.com{href}"
                else:
                    # Look for links near the title
                    links = parent.find_all('a', href=True)
                    for link in links:
                        href = link.get('href', '')
                        if 'program' in href or 'event' in href:
                            if href.startswith('http'):
                                event_url = href
                            elif href.startswith('/'):
                                event_url = f"https://thenewbev.com{href}"
                            break
                
                event = {
                    "title": title,
                    "venue": venue_name,
                    "venueShort": venue_short,
                    "type": event_type,
                    "date": date_str,
                    "time": time_str,
                    "description": "",
                    "url": event_url
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
    default_url = "https://vidiotsfoundation.org/coming-soon/"
    
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
        print(f"  DEBUG: First 10 movie titles found:")
        for i, header in enumerate(all_headers[:10]):
            title = header.get_text(strip=True)
            print(f"    {i+1}. {title}")
        
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
                
                # DEBUG: Show what dates we're finding
                if day == 24 and month_num == 1:
                    print(f"  DEBUG: Found Jan 24 event: {title}")
            else:
                continue
            
            # Look for time
            time_pattern = r'(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))'
            time_match = re.search(time_pattern, section_text, re.I)
            
            if time_match:
                time_str = time_match.group(1).upper()
                
                # DEBUG: Show Jan 24 events with times
                if day == 24 and month_num == 1:
                    print(f"    Time found: {time_str}")
            else:
                if day == 24 and month_num == 1:
                    print(f"    No time found for: {title}")
                continue
            
            # Try to find the event URL - look for links with "purchase" in them
            event_url = default_url
            links = parent.find_all('a', href=True)
            for link in links:
                href = link.get('href', '')
                # Look for purchase links or ticket links
                if 'purchase' in href or 'ticket' in href.lower():
                    if href.startswith('http'):
                        event_url = href
                    elif href.startswith('/'):
                        event_url = f"https://vidiotsfoundation.org{href}"
                    break
            
            event = {
                "title": title,
                "venue": venue_name,
                "venueShort": venue_short,
                "type": event_type,
                "date": date_str,
                "time": time_str,
                "description": "",
                "url": event_url
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


def scrape_academy_museum():
    """Scrape film screenings from Academy Museum of Motion Pictures"""
    
    url = "https://www.academymuseum.org/en/calendar?programTypes=16i3uOYQwism7sMDhIQr2O"
    venue_name = "Academy Museum"
    venue_short = "Academy"
    event_type = "film"
    default_url = "https://www.academymuseum.org/en/calendar?programTypes=16i3uOYQwism7sMDhIQr2O"
    
    print(f"Scraping {venue_name}...")
    
    driver = None
    try:
        driver = setup_driver()
        driver.get(url)
        time.sleep(5)  # Wait for JavaScript to load
        
        # Scroll down to load more events
        for _ in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
        
        print(f"  Page loaded successfully")
        
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        events = []
        current_year = datetime.now().year
        
        # Find all showtime text elements (they contain "Feb 6, 2026 | 2:30pm | 4K DCP")
        # These are <p> tags with class containing "ShowtimeText"
        showtime_elements = soup.find_all('p', class_=lambda c: c and 'ShowtimeText' in c)
        
        print(f"  Found {len(showtime_elements)} showtime elements")
        
        for showtime_el in showtime_elements:
            try:
                showtime_text = showtime_el.get_text(strip=True)
                
                # Parse: "Feb 6, 2026 | 2:30pm | 4K DCP"
                match = re.match(
                    r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2}),\s+(\d{4})\s*\|\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)',
                    showtime_text,
                    re.I
                )
                
                if not match:
                    continue
                
                month_name = match.group(1)
                day = int(match.group(2))
                year = int(match.group(3))
                hour = int(match.group(4))
                minutes = match.group(5) or "00"
                period = match.group(6).upper()
                
                # Convert month name to number
                month_map = {
                    'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4,
                    'May': 5, 'Jun': 6, 'Jul': 7, 'Aug': 8,
                    'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
                }
                month_num = month_map.get(month_name[:3].capitalize(), 1)
                
                date_str = f"{year}-{month_num:02d}-{day:02d}"
                time_str = f"{hour}:{minutes} {period}"
                
                # Find the title - go up to parent container and find the title link
                parent = showtime_el.parent
                title = None
                
                # Go up the DOM tree looking for the event container with a title link
                for _ in range(10):
                    if parent is None:
                        break
                    
                    # Look for link to /programs/detail/
                    title_link = parent.find('a', href=lambda h: h and '/programs/detail/' in h)
                    if title_link:
                        title = title_link.get_text(strip=True)
                        break
                    
                    parent = parent.parent
                
                if not title:
                    continue
                
                # Clean up title (remove extra whitespace)
                title = re.sub(r'\s+', ' ', title).strip()
                
                event = {
                    "title": title,
                    "venue": venue_name,
                    "venueShort": venue_short,
                    "type": event_type,
                    "date": date_str,
                    "time": time_str,
                    "description": "",
                    "url": default_url
                }
                events.append(event)
                print(f"    Found: {title} on {date_str} at {time_str}")
                
            except Exception as e:
                continue
        
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
    print("Starting LA Events Calendar Scraper v9")
    print("=" * 60)
    print()
    
    all_events = []
    
    # Vista Theater, New Beverly, Vidiots, and Academy Museum
    venues = [
        scrape_vista_theater,
        scrape_new_beverly,
        scrape_vidiots,
        scrape_academy_museum
    ]
    
    for scraper in venues:
        events = scraper()
        all_events.extend(events)
        print()
        time.sleep(2)
    
    # Filter out past events - use Pacific Time and check if event has already happened
    from datetime import timezone, timedelta
    pst = timezone(timedelta(hours=-8))
    now_pst = datetime.now(pst)
    today = now_pst.date()
    current_time_minutes = now_pst.hour * 60 + now_pst.minute
    
    future_events = []
    past_events_count = 0
    
    for event in all_events:
        try:
            event_date = datetime.strptime(event['date'], '%Y-%m-%d').date()
            
            # If event is in the future (tomorrow or later), include it
            if event_date > today:
                future_events.append(event)
            # If event is today, check if it hasn't happened yet
            elif event_date == today:
                # Parse event time to check if it's in the future
                time_match = re.match(r'(\d{1,2}):(\d{2})\s*(AM|PM)', event['time'], re.I)
                if time_match:
                    hours = int(time_match.group(1))
                    minutes = int(time_match.group(2))
                    period = time_match.group(3).upper()
                    
                    # Convert to 24-hour format
                    if period == 'PM' and hours != 12:
                        hours += 12
                    elif period == 'AM' and hours == 12:
                        hours = 0
                    
                    event_time_minutes = hours * 60 + minutes
                    
                    # Only include if event hasn't started yet (with 30-minute buffer)
                    if event_time_minutes > current_time_minutes - 30:
                        future_events.append(event)
                    else:
                        past_events_count += 1
                else:
                    # If we can't parse the time, include it to be safe
                    future_events.append(event)
            else:
                # Event was yesterday or earlier
                past_events_count += 1
        except:
            # If we can't parse the date, include it to be safe
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
    print(f"Current Pacific Time: {datetime.now(pst)}")
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
    print("LA Events Calendar Scraper v9")
    print("Vista Theater + New Beverly + Vidiots + Academy Museum")
    print("Now with clickable event links!")
    print("Fixed: Keeps today's future events!\n")
    
    events = scrape_all_venues()
    save_events_to_json(events)
    
    print("\nDone! Check events.json for the results.")
