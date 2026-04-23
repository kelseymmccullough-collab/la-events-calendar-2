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
        seen_events = set()  # Track (title, date, time) to avoid duplicates
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
            
            # Skip if section text is too long (likely grabbed too much of the page)
            if len(section_text) > 150:
                continue
            
            # Debug: print info for The Drama
            if 'drama' in title.lower():
                print(f"    DEBUG Drama: section_text length: {len(section_text)}")
            
            # Look for date: "Thursday 22, January" or just "22, January"
            date_pattern = r'(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)?\s*(\d{1,2}),?\s+(January|February|March|April|May|June|July|August|September|October|November|December)'
            date_match = re.search(date_pattern, section_text, re.I)
            
            # Look for ALL times: "7:15 PM", "9:30 PM", etc.
            time_pattern = r'(\d{1,2}:\d{2}\s*(?:am|pm))'
            time_matches = re.findall(time_pattern, section_text, re.I)
            
            if date_match and time_matches:
                day = int(date_match.group(1))
                month_name = date_match.group(2)
                month_num = datetime.strptime(month_name, '%B').month
                date_str = f"{current_year}-{month_num:02d}-{day:02d}"
                
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
                
                # Create an event for EACH showtime (but skip duplicates)
                for time_str in time_matches:
                    time_str = time_str.upper()
                    
                    # Check if we've already seen this event
                    event_key = (title, date_str, time_str)
                    if event_key in seen_events:
                        continue
                    seen_events.add(event_key)
                    
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
                
                if not times:
                    times = ["7:30 PM"]  # Default
                
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
                
                # Create an event for EACH showtime
                for time_str in times:
                    time_str = time_str.upper()
                    
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
    """Scrape film screenings from Vidiots website using data-date attributes"""
    
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
        seen_events = set()
        
        # Find all movie containers
        movie_containers = soup.find_all('div', class_='showtimes-description-inner')
        print(f"  Found {len(movie_containers)} movie containers")
        
        for container in movie_containers:
            # Get the title from the h2.show-title
            title_h2 = container.find('h2', class_='show-title')
            if not title_h2:
                continue
            
            title = title_h2.get_text(strip=True)
            if not title or title.lower() == 'coming soon to vidiots':
                continue
            
            # Find all showtime <li> elements with data-date attribute
            # These are inside ol.showtimes
            showtime_lis = container.find_all('li', attrs={'data-date': True})
            
            for li in showtime_lis:
                # Get the date from the data-date attribute (Unix timestamp)
                timestamp = li.get('data-date')
                if not timestamp:
                    continue
                
                try:
                    # Convert Unix timestamp to date
                    dt = datetime.fromtimestamp(int(timestamp))
                    date_str = dt.strftime('%Y-%m-%d')
                except (ValueError, OSError):
                    continue
                
                # Find the showtime link inside this li
                showtime_link = li.find('a', class_='showtime')
                if not showtime_link:
                    continue
                
                # Get the time from the link text
                time_text = showtime_link.get_text(strip=True)
                
                # Parse time like "3:45 pm" or "10:15 pm"
                time_match = re.search(r'(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))', time_text, re.I)
                if not time_match:
                    continue
                
                time_str = time_match.group(1).upper().replace(' ', ' ')
                # Normalize: "3:45 PM" format
                time_str = re.sub(r'\s+', ' ', time_str).strip()
                # Make sure there's a space before AM/PM
                time_str = re.sub(r'(\d)([AP]M)', r'\1 \2', time_str)
                
                # Get the URL
                event_url = showtime_link.get('href', default_url)
                
                # Skip duplicates
                event_key = (title, date_str, time_str)
                if event_key in seen_events:
                    continue
                seen_events.add(event_key)
                
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
        seen_events = set()
        page_num = 1
        max_pages = 10  # Safety limit
        
        from selenium.webdriver.common.by import By
        
        # Track first card title to detect when pagination has actually changed the page
        previous_first_title = None
        
        while page_num <= max_pages:
            print(f"  Scraping page {page_num}...")
            
            # Wait for cards to actually update by checking that the first card title has changed
            if page_num > 1:
                wait_attempts = 0
                while wait_attempts < 10:
                    page_source = driver.page_source
                    soup = BeautifulSoup(page_source, 'html.parser')
                    cards = soup.find_all('div', class_='seriesEventCardModule')
                    if cards:
                        first_h3 = cards[0].find('h3')
                        if first_h3:
                            current_first_title = first_h3.get_text(strip=True)
                            if current_first_title != previous_first_title:
                                break
                    time.sleep(1)
                    wait_attempts += 1
            
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Find all individual event cards using the specific class
            event_cards = soup.find_all('div', class_='seriesEventCardModule')
            print(f"    Found {len(event_cards)} event cards on page {page_num}")
            
            # Track the first title for next iteration's wait check
            if event_cards:
                first_h3 = event_cards[0].find('h3')
                if first_h3:
                    previous_first_title = first_h3.get_text(strip=True)
            
            events_found_on_page = 0
            cards_skipped = 0
            
            for card in event_cards:
                try:
                    # Get the card text - this contains date, time, title, venue
                    # Format: "View Event Details | FRI APR 17, 2026 | 5:00 PM | MY NDA | Los Feliz 3 | description | Los Feliz Theatre | View Event Details"
                    card_text = card.get_text(separator=' | ', strip=True)
                    
                    # Filter: Only keep events at Los Feliz 3 (in case filter doesn't persist across pages)
                    if 'Los Feliz 3' not in card_text and 'los feliz 3' not in card_text.lower():
                        cards_skipped += 1
                        continue
                    
                    # Get the title from the h3 element
                    title_h3 = card.find('h3')
                    if not title_h3:
                        continue
                    title = title_h3.get_text(strip=True)
                    
                    if not title:
                        continue
                    
                    # Convert ALL CAPS title to Title Case
                    # Handle special cases: words with slashes, parentheses, etc.
                    def smart_title_case(text):
                        """Convert text to title case, but preserve known abbreviations and articles."""
                        # Words that should stay lowercase (unless first word)
                        small_words = {'a', 'an', 'and', 'as', 'at', 'but', 'by', 'for', 'in', 'of', 'on', 'or', 'the', 'to', 'with', 'vs', 'vs.'}
                        # Known abbreviations to keep uppercase
                        keep_upper = {'L.A.', 'NYC', 'USA', 'UK', 'TV', 'DVD', 'VHS', 'IMAX', '70MM', '35MM', '16MM', 'Q&A', 'NDA', 'AC', 'MTV'}
                        
                        # Split by spaces but preserve original separators
                        words = text.split(' ')
                        result = []
                        for i, word in enumerate(words):
                            if not word:
                                result.append(word)
                                continue
                            
                            # Check if this is a known abbreviation
                            word_clean = word.strip('[](){}.,!?:;')
                            if word_clean.upper() in keep_upper:
                                result.append(word.replace(word_clean, word_clean.upper()))
                                continue
                            
                            # Handle slashes - title case each part
                            if '/' in word:
                                parts = word.split('/')
                                new_parts = []
                                for part in parts:
                                    if part.upper() in keep_upper:
                                        new_parts.append(part.upper())
                                    else:
                                        new_parts.append(part.capitalize())
                                result.append('/'.join(new_parts))
                                continue
                            
                            # Lowercase small words (except first word)
                            if i > 0 and word.lower() in small_words:
                                result.append(word.lower())
                            else:
                                # Title case - handle words with brackets/punctuation
                                if word.startswith('['):
                                    # Like [ANCESTOR/...]
                                    inner = word[1:]
                                    if '/' in inner:
                                        parts = inner.rstrip(']').split('/')
                                        new_parts = [p.capitalize() for p in parts]
                                        suffix = ']' if word.endswith(']') else ''
                                        result.append('[' + '/'.join(new_parts) + suffix)
                                    else:
                                        result.append('[' + inner.capitalize())
                                else:
                                    result.append(word.capitalize())
                        
                        return ' '.join(result)
                    
                    title = smart_title_case(title)
                    
                    # Get the URL from a link in the card
                    event_url = base_url
                    for link in card.find_all('a', href=True):
                        href = link.get('href', '')
                        if '/now-showing/' in href and href != '/now-showing/' and '?' not in href:
                            event_url = href if href.startswith('http') else f"https://www.americancinematheque.com{href}"
                            break
                    
                    # Parse date from card text - format: "FRI APR 17, 2026"
                    date_match = re.search(
                        r'(MON|TUE|WED|THU|FRI|SAT|SUN)\s+(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\s+(\d{1,2}),?\s+(\d{4})',
                        card_text, re.I
                    )
                    
                    if not date_match:
                        # Try alternative format
                        date_match = re.search(
                            r'(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\s+(\d{1,2}),?\s+(\d{4})',
                            card_text, re.I
                        )
                        if date_match:
                            month_abbr = date_match.group(1)[:3].capitalize()
                            day = int(date_match.group(2))
                            year = int(date_match.group(3))
                        else:
                            continue
                    else:
                        month_abbr = date_match.group(2)[:3].capitalize()
                        day = int(date_match.group(3))
                        year = int(date_match.group(4))
                    
                    month_map = {
                        'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4,
                        'May': 5, 'Jun': 6, 'Jul': 7, 'Aug': 8,
                        'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
                    }
                    month_num = month_map.get(month_abbr, 1)
                    date_str = f"{year}-{month_num:02d}-{day:02d}"
                    
                    # Parse time from card text - format: "5:00 PM"
                    time_match = re.search(r'(\d{1,2}):(\d{2})\s*(AM|PM|am|pm)', card_text)
                    if time_match:
                        hour = int(time_match.group(1))
                        minutes = time_match.group(2)
                        period = time_match.group(3).upper()
                        time_str = f"{hour}:{minutes} {period}"
                    else:
                        time_str = "7:30 PM"  # Default
                    
                    # Skip duplicates
                    event_key = (title, date_str, time_str)
                    if event_key in seen_events:
                        continue
                    seen_events.add(event_key)
                    
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
                    print(f"      Error processing card: {e}")
                    continue
            
            print(f"    Events found on page {page_num}: {events_found_on_page} (skipped {cards_skipped} non-Los Feliz 3 cards)")
            
            # Try to click the next page button (Algolia InstantSearch pagination)
            try:
                pagination_found = False
                next_page_num = page_num + 1
                
                # Scroll to bottom first to make sure pagination is loaded and visible
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                
                # The pagination uses ais-Pagination structure with <button> elements
                # Find all buttons inside ais-Pagination-item elements
                page_buttons = driver.find_elements(By.CSS_SELECTOR, 'li.ais-Pagination-item button')
                
                print(f"    DEBUG: Found {len(page_buttons)} pagination buttons")
                if page_buttons:
                    # Get text via JavaScript (innerText/textContent) - more reliable than .text
                    button_info = []
                    for btn in page_buttons:
                        text = btn.text.strip()
                        inner_text = driver.execute_script("return arguments[0].textContent;", btn).strip()
                        aria = btn.get_attribute('aria-label') or ''
                        button_info.append(f"text='{text}' textContent='{inner_text}' aria='{aria}'")
                    print(f"    DEBUG: Buttons: {button_info}")
                
                for button in page_buttons:
                    button_text = button.text.strip()
                    button_aria = button.get_attribute('aria-label') or ''
                    # Use textContent as fallback
                    button_inner_text = driver.execute_script("return arguments[0].textContent;", button).strip()
                    
                    # Match either by text, textContent, or aria-label
                    is_target = (
                        button_text == str(next_page_num) or
                        button_inner_text == str(next_page_num) or
                        button_aria == str(next_page_num) or
                        button_aria == f"Page {next_page_num}" or
                        button_aria.endswith(f" {next_page_num}")
                    )
                    
                    if is_target:
                        # Scroll to button and click
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                        time.sleep(1)
                        driver.execute_script("arguments[0].click();", button)
                        time.sleep(4)  # Wait for new page to load
                        # Scroll back to top to see new content
                        driver.execute_script("window.scrollTo(0, 0);")
                        time.sleep(1)
                        page_num += 1
                        pagination_found = True
                        print(f"    Clicked page {next_page_num}")
                        break
                
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
    print("Starting LA Events Calendar Scraper v11")
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
