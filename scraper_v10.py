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
    
    base_url = "https://www.academymuseum.org/en/calendar?locale=en&programTypes=16i3uOYQwism7sMDhIQr2O"
    venue_name = "Academy Museum"
    venue_short = "Academy"
    event_type = "film"
    default_url = "https://www.academymuseum.org/en/calendar?programTypes=16i3uOYQwism7sMDhIQr2O"
    
    print(f"Scraping {venue_name}...")
    
    driver = None
    try:
        driver = setup_driver()
        
        all_events = []
        page_num = 1
        max_pages = 10  # Safety limit
        
        while page_num <= max_pages:
            # Build URL with page parameter
            if page_num == 1:
                url = base_url
            else:
                url = f"{base_url}&page={page_num}"
            
            print(f"  Scraping page {page_num}: {url}")
            
            driver.get(url)
            time.sleep(5)  # Wait for JavaScript to load
            
            # Scroll down to ensure all content is loaded
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Find all showtime text elements (they contain "Feb 6, 2026 | 2:30pm | 4K DCP")
            showtime_elements = soup.find_all('p', class_=lambda c: c and 'ShowtimeText' in c)
            
            print(f"    Found {len(showtime_elements)} showtime elements on page {page_num}")
            
            # If no events found, we've gone past the last page
            if len(showtime_elements) == 0:
                print(f"  No events on page {page_num}, stopping pagination")
                break
            
            events_on_page = 0
            
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
                    
                    # Find the title - go up to parent container and find the SECOND title link
                    # (first link is usually the image, second is the actual title text)
                    parent = showtime_el.parent
                    title = None
                    
                    # Go up the DOM tree looking for the event container
                    for _ in range(10):
                        if parent is None:
                            break
                        
                        # Find ALL links to /programs/detail/ in this container
                        title_links = parent.find_all('a', href=lambda h: h and '/programs/detail/' in h)
                        
                        if len(title_links) >= 2:
                            # The second link is typically the title (first is image)
                            title_link = title_links[1]
                            title = title_link.get_text(strip=True)
                            if title:
                                break
                        elif len(title_links) == 1:
                            # Only one link, use it
                            title = title_links[0].get_text(strip=True)
                            if title:
                                break
                        
                        parent = parent.parent
                    
                    if not title:
                        continue
                    
                    # Clean up title (remove extra whitespace)
                    title = re.sub(r'\s+', ' ', title).strip()
                    
                    # Fix missing space before format suffixes (e.g., "Wizard of Ozin 4K" -> "Wizard of Oz in 4K")
                    title = re.sub(r'(\w)(in\s+(?:4K|35mm|DCP|Dolby Vision|Dolby Atmos|IMAX|70mm))', r'\1 \2', title, flags=re.I)
                    
                    # Skip if title looks like it grabbed too much (contains common non-title words)
                    if any(word in title.lower() for word in ['screenings', 'in person:', 'special guest']):
                        # Try to extract just the movie name - typically before "In person" or after certain patterns
                        # Look for pattern like "Movie Title in 4K" or "Movie Title in 35mm"
                        clean_match = re.match(r'^(.+?(?:\s+in\s+(?:4K|35mm|DCP))?)\s*$', title.split('In person')[0].split('Selected by')[0], re.I)
                        if clean_match:
                            title = clean_match.group(1).strip()
                    
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
                    all_events.append(event)
                    events_on_page += 1
                    print(f"    Found: {title} on {date_str} at {time_str}")
                    
                except Exception as e:
                    continue
            
            # Move to next page
            page_num += 1
        
        # Remove duplicates (same title, date, time)
        seen = set()
        unique_events = []
        for event in all_events:
            key = (event['title'], event['date'], event['time'])
            if key not in seen:
                seen.add(key)
                unique_events.append(event)
        
        print(f"✓ Successfully scraped {len(unique_events)} events from {venue_name}")
        return unique_events
        
    except Exception as e:
        print(f"✗ Error scraping {venue_name}: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        if driver:
            driver.quit()


def scrape_american_cinematheque():
    """Scrape film screenings from American Cinematheque - Los Feliz 3"""
    
    base_url = "https://www.americancinematheque.com/now-showing/?event_location=102&view_type=list"
    venue_name = "American Cinematheque at Los Feliz 3"
    venue_short = "Los Feliz 3"
    event_type = "film"
    
    print(f"Scraping {venue_name}...")
    
    driver = None
    try:
        driver = setup_driver()
        driver.get(base_url)
        time.sleep(6)  # Wait for JavaScript to load
        
        # Scroll to load lazy content
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)
        
        print(f"  Page loaded successfully")
        
        all_events = []
        page_num = 1
        max_pages = 10  # Safety limit
        
        from selenium.webdriver.common.by import By
        
        while page_num <= max_pages:
            print(f"  Scraping page {page_num}...")
            
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            events_found_on_page = 0
            processed_events = set()
            
            # Find all "View Event Details" links - these mark event cards
            view_details_links = soup.find_all('a', string=lambda t: t and 'view event' in t.lower())
            
            # Also try finding links that contain the event URL pattern
            if not view_details_links:
                view_details_links = soup.find_all('a', href=lambda h: h and '/now-showing/' in h and '?' not in h and h != '/now-showing/')
            
            print(f"    Found {len(view_details_links)} event links on page {page_num}")
            
            for link in view_details_links:
                try:
                    href = link.get('href', '')
                    
                    # Skip navigation links
                    if not href or href == '/now-showing/' or 'event_location=' in href:
                        continue
                    
                    # Build full URL
                    event_url = href if href.startswith('http') else f"https://www.americancinematheque.com{href}"
                    
                    # Skip if we've already processed this URL
                    if event_url in processed_events:
                        continue
                    processed_events.add(event_url)
                    
                    # Debug: print the URL being processed
                    print(f"      Processing URL: {href}")
                    
                    # Find the parent container (the event card)
                    parent = link.parent
                    card_container = None
                    
                    # Go up the DOM to find the card container
                    for _ in range(10):
                        if parent is None:
                            break
                        
                        # Check if this container has a heading (title) and date info
                        has_heading = parent.find(['h1', 'h2', 'h3', 'h4', 'h5'])
                        has_date = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)', parent.get_text())
                        
                        if has_heading and has_date:
                            card_container = parent
                            break
                        
                        parent = parent.parent
                    
                    if not card_container:
                        continue
                    
                    # Get ONLY this card's text for date/time parsing
                    container_text = card_container.get_text(separator=' ', strip=True)
                    
                    # Find the title from a heading element
                    title = None
                    for heading in card_container.find_all(['h1', 'h2', 'h3', 'h4', 'h5']):
                        heading_text = heading.get_text(strip=True)
                        # Skip if it's a date or time or "View Event Details"
                        if heading_text and len(heading_text) > 2:
                            if not re.match(r'^(Mon|Tue|Wed|Thu|Fri|Sat|Sun|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|\d)', heading_text):
                                continue
                            if 'view event' in heading_text.lower():
                                continue
                            # This looks like a title
                            title = heading_text
                            break
                    
                    # If no heading found, try to extract title from the URL
                    if not title:
                        # URL like /now-showing/twin-peaks-season-1-ep-5-2-10-26-630pm/
                        url_match = re.search(r'/now-showing/([^/]+)/?$', href)
                        if url_match:
                            # Convert slug to title
                            slug = url_match.group(1)
                            # Remove date/time suffix - matches patterns like:
                            # -2-10-26-630pm, -2-12-26-700pm, -12-25-26-1pm, etc.
                            slug = re.sub(r'-\d{1,2}-\d{1,2}-\d{2,4}-\d{1,4}(?:am|pm)?$', '', slug, flags=re.I)
                            # Also try simpler pattern without time
                            slug = re.sub(r'-\d{1,2}-\d{1,2}-\d{2,4}$', '', slug, flags=re.I)
                            # Convert dashes to spaces and title case
                            title = slug.replace('-', ' ').title()
                            # Fix common abbreviations
                            title = re.sub(r'\bEp\b', 'Ep.', title)
                    
                    if not title:
                        continue
                    
                    # Parse date and time FROM THE URL first (most reliable)
                    # URL formats:
                    # - With time: /now-showing/twin-peaks-season-1-ep-5-2-10-26-630pm/
                    # - Without time: /now-showing/in-order-of-disappearance-2-13-26/
                    date_str = None
                    time_str = None
                    
                    # Try matching URL with time first
                    url_date_match = re.search(r'-(\d{1,2})-(\d{1,2})-(\d{2,4})-(\d{1,4})(am|pm)/?$', href, re.I)
                    if url_date_match:
                        month = int(url_date_match.group(1))
                        day = int(url_date_match.group(2))
                        year = int(url_date_match.group(3))
                        if year < 100:
                            year += 2000  # Convert 26 to 2026
                        
                        time_num = url_date_match.group(4)
                        period = url_date_match.group(5).upper()
                        
                        # Parse time: 630 -> 6:30, 1000 -> 10:00, 1 -> 1:00
                        if len(time_num) <= 2:
                            hour = int(time_num)
                            minutes = "00"
                        elif len(time_num) == 3:
                            hour = int(time_num[0])
                            minutes = time_num[1:3]
                        else:
                            hour = int(time_num[:-2])
                            minutes = time_num[-2:]
                        
                        date_str = f"{year}-{month:02d}-{day:02d}"
                        time_str = f"{hour}:{minutes} {period}"
                    else:
                        # Try matching URL without time (e.g., -2-13-26/)
                        url_date_match = re.search(r'-(\d{1,2})-(\d{1,2})-(\d{2,4})/?$', href)
                        if url_date_match:
                            month = int(url_date_match.group(1))
                            day = int(url_date_match.group(2))
                            year = int(url_date_match.group(3))
                            if year < 100:
                                year += 2000
                            date_str = f"{year}-{month:02d}-{day:02d}"
                            # Time will be parsed from container text below
                    
                    if date_str:
                        print(f"        URL date parsed: {date_str}" + (f" at {time_str}" if time_str else " (no time in URL)"))
                    else:
                        print(f"        URL date NOT matched for: {href}")
                    
                    # Parse time from container text if not found in URL
                    if not time_str:
                        time_match = re.search(r'(\d{1,2}):(\d{2})\s*(am|pm|AM|PM)', container_text)
                        if time_match:
                            hour = int(time_match.group(1))
                            minutes = time_match.group(2)
                            period = time_match.group(3).upper()
                            time_str = f"{hour}:{minutes} {period}"
                        else:
                            time_str = "7:30 PM"  # Default
                    
                    # Fallback to parsing date from container text if URL parsing failed
                    if not date_str:
                        print(f"        Falling back to container text parsing")
                        date_patterns = [
                            r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})',
                            r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})',
                            r'(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\w*\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+(\d{1,2})',
                            r'(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+(\d{1,2})(?:st|nd|rd|th)?',
                        ]
                        
                        for pattern in date_patterns:
                            date_match = re.search(pattern, container_text, re.I)
                            if date_match:
                                groups = date_match.groups()
                                month_name = groups[0][:3].capitalize()
                                day = int(groups[1])
                                year = int(groups[2]) if len(groups) > 2 and groups[2] else datetime.now().year
                                
                                month_map = {
                                    'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4,
                                    'May': 5, 'Jun': 6, 'Jul': 7, 'Aug': 8,
                                    'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
                                }
                                month_num = month_map.get(month_name, 1)
                                date_str = f"{year}-{month_num:02d}-{day:02d}"
                                break
                    
                    if not date_str:
                        continue
                    
                    # Parse time from container if not already set from URL
                    if not time_str:
                        time_str = "7:30 PM"  # Default
                        time_match = re.search(r'(\d{1,2}):(\d{2})\s*(am|pm|AM|PM)', container_text)
                        if time_match:
                            hour = int(time_match.group(1))
                            minutes = time_match.group(2)
                            period = time_match.group(3).upper()
                            time_str = f"{hour}:{minutes} {period}"
                    
                    # Create unique key to avoid duplicates
                    event_key = (title, date_str, time_str)
                    if event_key in processed_events:
                        continue
                    processed_events.add(event_key)
                    
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
                    all_events.append(event)
                    events_found_on_page += 1
                    print(f"    Found: {title} on {date_str} at {time_str}")
                    
                except Exception as e:
                    continue
            
            print(f"    Events found on page {page_num}: {events_found_on_page}")
            
            # Try to find and click the next page number
            try:
                pagination_found = False
                next_page_num = page_num + 1
                
                # Try different pagination selectors
                pagination_selectors = [
                    'a.page-numbers',
                    '.pagination a',
                    'nav[class*="pagination"] a',
                    'a[class*="page"]',
                ]
                
                for selector in pagination_selectors:
                    try:
                        page_links = driver.find_elements(By.CSS_SELECTOR, selector)
                        for link in page_links:
                            link_text = link.text.strip()
                            if link_text == str(next_page_num):
                                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", link)
                                time.sleep(0.5)
                                link.click()
                                time.sleep(4)
                                page_num += 1
                                pagination_found = True
                                print(f"    Clicked page {next_page_num}")
                                break
                        if pagination_found:
                            break
                    except:
                        continue
                
                if not pagination_found:
                    print(f"  No more pages found after page {page_num}")
                    break
                    
            except Exception as e:
                print(f"  Pagination error: {e}")
                break
        
        # Remove duplicates (same title, date, time)
        seen = set()
        unique_events = []
        for event in all_events:
            key = (event['title'], event['date'], event['time'])
            if key not in seen:
                seen.add(key)
                unique_events.append(event)
        
        print(f"✓ Successfully scraped {len(unique_events)} events from {venue_name}")
        return unique_events
        
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
    print("Starting LA Events Calendar Scraper v10")
    print("=" * 60)
    print()
    
    all_events = []
    
    # Vista Theater, New Beverly, Vidiots, Academy Museum, and American Cinematheque
    venues = [
        scrape_vista_theater,
        scrape_new_beverly,
        scrape_vidiots,
        scrape_academy_museum,
        scrape_american_cinematheque
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
