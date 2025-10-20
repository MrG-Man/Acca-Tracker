#!/usr/bin/env python3
"""
Enhanced BBC Sport Football Fixtures and Live Scores Scraper

UNIFIED SCRAPING APPROACH:
- Scrapes the main BBC football page for ALL matches on a given date
- Filters results to only our supported leagues
- Consistent parsing methodology across all leagues
- Much more reliable than individual league page scraping

FEATURES:
- Unified BBC page scraping for all leagues
- Dynamic date-based URL construction for BBC Sport
- Live score extraction including current scores and match status
- Enhanced data models with live score information and match timing
- Comprehensive error handling and fallback mechanisms
- Intelligent caching system for both fixtures and live data
- Rate limiting and performance optimization
- Zero external API dependencies (BBC direct scraping)

NEW FUNCTIONALITY:
- scrape_unified_bbc_matches(): Unified scraping of main BBC page
- Enhanced data models include: home_score, away_score, status, match_time
- Support for all match times (not just 15:00 kickoffs)
- Real-time match status tracking (not_started, live, halftime, finished)
- Dynamic URL construction using BBC's date-based format

LEAGUES SUPPORTED:
- Premier League, English Championship, League One, League Two, National League
- Scottish Premiership, Championship, League One, League Two

SCRAPING METHODOLOGY:
- Uses https://www.bbc.co.uk/sport/football/scores-fixtures/YYYY-MM-DD
- Parses ALL matches from this single page
- Filters to only supported leagues
- Handles both fixture and live score modes

USAGE:
- python bbc_scraper.py          # Run fixture scraping (original functionality)
- python bbc_scraper.py test     # Test enhanced functionality
- python bbc_scraper.py api-test # Test API endpoint logic

API ENDPOINTS (when used with Flask app):
- GET /api/bbc-fixtures         # Get next Saturday's fixtures
- GET /api/bbc-live-scores      # Get current live scores
- GET /api/bbc-matches/<date>   # Get matches for specific date

Author: Football Predictions System
Date: 2024
Updated: 2025 - Enhanced with unified BBC page scraping
"""

import requests
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime, timedelta, timezone
import re
from typing import Dict, List, Optional, Tuple
import hashlib
import os
from urllib.parse import urljoin, urlparse
import logging

# Import DataManager for caching with fallback handling
try:
    from data_manager import data_manager
    print("DataManager imported successfully in BBC scraper")
except Exception as e:
    print(f"ERROR: Failed to import DataManager in BBC scraper: {e}")
    # Create a minimal fallback data_manager for basic functionality
    class FallbackDataManager:
        def get_bbc_fixtures(self, date, league=None):
            print(f"FALLBACK: get_bbc_fixtures called for {date}, {league}")
            return None
        def cache_bbc_fixtures(self, fixtures, date):
            print(f"FALLBACK: cache_bbc_fixtures called for {date}")
            return False
        @property
        def fixtures_path(self):
            return "data/fixtures"

    data_manager = FallbackDataManager()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BBCSportScraper:
    """
    Enhanced BBC Sport scraper for football fixtures and live scores.

    Supports both fixture scraping for upcoming matches and live score monitoring
    using dynamic date-based URLs. Handles all match times, not just 15:00 kickoffs.
    """

    # Base URL for BBC Sport
    BASE_URL = "https://www.bbc.co.uk"

    # Operating modes
    MODE_FIXTURES = "fixtures"
    MODE_LIVE = "live"

    # League configurations with their BBC Sport URLs
    LEAGUES = {
        # English Leagues
        "Premier League": "/sport/football/premier-league/scores-fixtures",
        "English Championship": "/sport/football/championship/scores-fixtures",
        "English League One": "/sport/football/league-one/scores-fixtures",
        "English League Two": "/sport/football/league-two/scores-fixtures",
        "English National League": "/sport/football/national-league/scores-fixtures",

        # Scottish Leagues
        "Scottish Premiership": "/sport/football/scottish-premiership/scores-fixtures",
        "Scottish Championship": "/sport/football/scottish-championship/scores-fixtures",
        "Scottish League One": "/sport/football/scottish-league-one/scores-fixtures",
        "Scottish League Two": "/sport/football/scottish-league-two/scores-fixtures",

        # Example: Adding a new league would be this simple:
        # "Italian Serie A": "/sport/football/italian-serie-a/scores-fixtures",
        # "German Bundesliga": "/sport/football/german-bundesliga/scores-fixtures",
        # "French Ligue 1": "/sport/football/french-ligue-1/scores-fixtures",
    }

    def __init__(self, rate_limit: float = 1.0):
        """
        Initialize the BBC Sport scraper.

        Args:
            rate_limit: Minimum seconds between requests (default: 1.0)
        """
        self.rate_limit = rate_limit
        self.last_request_time = 0
        self.session = requests.Session()

        # Set user agent to avoid blocking
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def _get_next_saturday(self) -> Tuple[str, str]:
        """
        Calculate next Saturday's date.

        Returns:
            Tuple of (scraping_date, next_saturday) in YYYY-MM-DD format
        """
        today = datetime.now()
        days_until_saturday = (5 - today.weekday()) % 7

        # If today is Saturday, use today as the target date
        if today.weekday() == 5:  # 5 = Saturday
            next_saturday = today
        else:
            next_saturday = today + timedelta(days=days_until_saturday)

        return today.strftime("%Y-%m-%d"), next_saturday.strftime("%Y-%m-%d")

    def _build_bbc_url(self, target_date: str, mode: str = MODE_FIXTURES) -> str:
        """
        Build BBC Sport URL for the specified date and mode.

        Args:
            target_date: Target date in YYYY-MM-DD format
            mode: Operating mode (fixtures or live)

        Returns:
            Complete BBC Sport URL
        """
        if mode == self.MODE_FIXTURES:
            # Format: https://www.bbc.co.uk/sport/football/scores-fixtures/2025-10-25
            return f"{self.BASE_URL}/sport/football/scores-fixtures/{target_date}"
        elif mode == self.MODE_LIVE:
            # Format: https://www.bbc.co.uk/sport/football/scores-fixtures/2025-10-25?filter=results
            return f"{self.BASE_URL}/sport/football/scores-fixtures/{target_date}?filter=results"
        else:
            raise ValueError(f"Invalid mode: {mode}. Use MODE_FIXTURES or MODE_LIVE")

    def _build_league_url(self, league_url: str, target_date: str, mode: str = MODE_FIXTURES) -> str:
        """
        Build league-specific BBC Sport URL for the specified date and mode.

        Args:
            league_url: Base league URL from LEAGUES configuration
            target_date: Target date in YYYY-MM-DD format
            mode: Operating mode (fixtures or live)

        Returns:
            Complete league-specific BBC Sport URL
        """
        # Extract year-month from target_date for URL construction
        date_parts = target_date.split('-')
        if len(date_parts) >= 2:
            year_month = f"{date_parts[0]}-{date_parts[1]}"
            # Use the original working URL format with year-month
            if mode == self.MODE_FIXTURES:
                return f"{self.BASE_URL}{league_url}/{year_month}?filter=fixtures"
            else:  # MODE_LIVE
                return f"{self.BASE_URL}{league_url}/{year_month}?filter=results"
        else:
            # Fallback to base URL if date parsing fails
            return f"{self.BASE_URL}{league_url}"

    def _enforce_rate_limit(self):
        """Enforce rate limiting between requests."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time

        if time_since_last_request < self.rate_limit:
            sleep_time = self.rate_limit - time_since_last_request
            logger.info(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def _get_cache_key(self, url: str, date: str) -> str:
        """Generate cache key for URL and date combination."""
        content = f"{url}:{date}"
        return hashlib.md5(content.encode()).hexdigest()

    def _get_cached_data(self, cache_key: str, date: str, league_name: str) -> Optional[Dict]:
        """Retrieve cached data if available and not expired using DataManager."""
        fixtures = data_manager.get_bbc_fixtures(date, league_name)
        if fixtures:
            logger.info(f"Using cached BBC data for {date} - {league_name}")
            # Ensure fixtures is a list of dictionaries
            if isinstance(fixtures, list):
                return {'matches': fixtures}
            else:
                logger.warning(f"Invalid fixtures format from cache: {type(fixtures)}")
                return None
        return None

    def _is_cache_valid_for_date(self, target_date: str) -> bool:
        """Check if cached data is still valid for the target date."""
        try:
            # Check if target date is within next 7 days (Saturday fixtures are weekly)
            today = datetime.now()
            target = datetime.strptime(target_date, "%Y-%m-%d")

            # If target date is more than 7 days away, cache is invalid
            if target > today + timedelta(days=7):
                return False

            # If target date is in the past, cache is invalid
            if target.date() < today.date():
                return False

            return True
        except ValueError:
            return False

    def _save_cache_data(self, cache_key: str, data: Dict, date: str, league_name: str):
        """Save data to cache using DataManager with validation."""
        matches = data.get('matches', [])

        # Validate the scraped data before caching
        if not self._validate_scraped_matches(matches):
            logger.error(f"Scraped data validation failed for {date} - {league_name}. Not caching corrupted data.")
            return

        success = data_manager.cache_bbc_fixtures(matches, date)
        if success:
            logger.info(f"Cached BBC data for {date} - {league_name} using DataManager")
        else:
            logger.error(f"Failed to cache BBC data for {date} - {league_name}")

    def _validate_scraped_matches(self, matches: List[Dict]) -> bool:
        """Validate scraped match data to prevent caching corrupted HTML content.

        Args:
            matches: List of match dictionaries to validate

        Returns:
            bool: True if data is valid, False if corrupted
        """
        if not isinstance(matches, list):
            return False

        if len(matches) == 0:
            return True  # Empty list is valid

        for match in matches:
            if not isinstance(match, dict):
                return False

            # Check for HTML content in match data (indicates scraping failure)
            for key, value in match.items():
                if isinstance(value, str):
                    # Check if the value looks like HTML (contains many HTML tags)
                    html_tags = value.count('<') + value.count('>')
                    if html_tags > 10:  # More than 10 HTML tags indicates HTML content
                        logger.error(f"Found HTML content in match data for key '{key}': {value[:200]}...")
                        return False

                    # Check for extremely long values (likely HTML content)
                    if len(value) > 1000:
                        logger.error(f"Found extremely long value in match data for key '{key}': {len(value)} characters")
                        return False

            # Validate required fields
            required_fields = ["league", "home_team", "away_team", "kickoff"]
            for field in required_fields:
                if field not in match:
                    return False

                value = match[field]
                if not isinstance(value, str) or len(value.strip()) == 0:
                    return False

        return True

    def _make_request(self, url: str) -> Optional[BeautifulSoup]:
        """
        Make HTTP request with error handling and rate limiting.

        Args:
            url: Full URL to request

        Returns:
            BeautifulSoup object or None if request failed
        """
        self._enforce_rate_limit()

        try:
            logger.info(f"Requesting: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            return BeautifulSoup(response.content, 'html.parser')

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error requesting {url}: {e}")
            return None

    def _parse_match_data(self, match_element, league_name: str, mode: str = MODE_FIXTURES) -> Optional[Dict]:
        """
        Parse individual match data from HTML element.

        Args:
            match_element: BeautifulSoup element containing match info
            league_name: Name of the league for this match
            mode: Operating mode (fixtures or live)

        Returns:
            Match dictionary or None if parsing failed
        """
        try:
            # Special handling for Championship - use JSON data extraction
            if league_name in ["English Championship", "Scottish Championship"]:
                if mode == self.MODE_FIXTURES:
                    return self._parse_championship_match_data(match_element, league_name)
                else:
                    # For live mode, use the general live parsing method
                    return self._parse_live_match_data(match_element, league_name)

            # Route to appropriate parsing method based on mode
            if mode == self.MODE_LIVE:
                return self._parse_live_match_data(match_element, league_name)
            elif mode == self.MODE_FIXTURES:
                # NEW BBC Sport structure: Look for match text with "versus" pattern
                match_text = None

                # Look for text containing "versus" and "kick off 15:00"
                for element in match_element.find_all(string=lambda text: text and 'versus' in text.lower() and 'kick off 15:00' in text):
                    match_text = element.strip()
                    break

                if not match_text:
                    return None

                # Parse team names from match text like "Team A versus Team B kick off 15:00"
                try:
                    # Extract teams from pattern "Home versus Away kick off 15:00"
                    versus_pattern = re.search(r'(.+?)\s+versus\s+(.+?)\s+kick off 15:00', match_text, re.IGNORECASE)
                    if versus_pattern:
                        home_team = versus_pattern.group(1).strip()
                        away_team = versus_pattern.group(2).strip()
                    else:
                        return None

                except Exception:
                    return None

                # Validate team names are reasonable
                if (len(home_team) < 2 or len(away_team) < 2 or
                    len(home_team) > 50 or len(away_team) > 50):
                    return None

                # Extract kickoff time - NEW structure uses ssrcss time classes
                time_element = match_element.find('time', class_=re.compile(r'ssrcss.*Time'))
                if not time_element:
                    return None

                kickoff = time_element.get_text(strip=True)

                # Extract venue if available
                venue_element = match_element.find('span', class_=re.compile(r'ssrcss.*Venue|stadium'))
                venue = venue_element.get_text(strip=True) if venue_element else "TBC"

                # Validate that this is exactly 15:00
                if kickoff != "15:00":
                    return None

                return {
                    "league": league_name,
                    "home_team": home_team,
                    "away_team": away_team,
                    "kickoff": kickoff,
                    "venue": venue,
                    "home_score": 0,
                    "away_score": 0,
                    "status": "not_started",
                    "match_time": "0'"
                }
            else:
                raise ValueError(f"Invalid mode: {mode}")

        except Exception as e:
            logger.error(f"Error parsing match data: {e}")
            return None

    def _parse_live_match_data(self, match_element, league_name: str) -> Optional[Dict]:
        """
        Parse live match data from HTML element including current scores and status.

        Args:
            match_element: BeautifulSoup element containing match info
            league_name: Name of the league for this match

        Returns:
            Match dictionary with live data or None if parsing failed
        """
        try:
            # Look for live score indicators and current match status
            match_text = None

            # Look for text containing team names and scores
            for element in match_element.find_all(string=lambda text: text and (' vs ' in text.lower() or ' v ' in text.lower())):
                match_text = element.strip()
                break

            if not match_text:
                return None

            # Extract team names and scores from patterns like:
            # "Team A 2-1 Team B" or "Team A vs Team B"
            teams = []
            scores = []

            # Pattern 1: "Team A 2-1 Team B"
            score_pattern = re.search(r'(.+?)\s+(\d+)-(\d+)\s+(.+)', match_text)
            if score_pattern:
                teams = [score_pattern.group(1).strip(), score_pattern.group(4).strip()]
                scores = [int(score_pattern.group(2)), int(score_pattern.group(3))]
            else:
                # Pattern 2: "Team A vs Team B" (no scores yet)
                vs_pattern = re.search(r'(.+?)\s+vs?\s+(.+)', match_text, re.IGNORECASE)
                if vs_pattern:
                    teams = [vs_pattern.group(1).strip(), vs_pattern.group(2).strip()]
                    scores = [0, 0]
                else:
                    return None

            # Validate team names
            if (len(teams[0]) < 2 or len(teams[1]) < 2 or
                len(teams[0]) > 50 or len(teams[1]) > 50):
                return None

            home_team, away_team = teams[0], teams[1]
            home_score, away_score = scores[0], scores[1]

            # Extract match status and time
            status = "not_started"
            match_time = "0'"

            # Look for status indicators (live, finished, halftime, etc.)
            status_element = match_element.find(['span', 'div'], class_=re.compile(r'ssrcss.*Status|live|finished|halftime'))
            if status_element:
                status_text = status_element.get_text(strip=True).lower()
                if 'live' in status_text or 'playing' in status_text:
                    status = "live"
                    # Look for match time (e.g., "67'", "45+2'", etc.)
                    time_element = match_element.find(['span', 'div'], class_=re.compile(r'ssrcss.*Time|minute'))
                    if time_element:
                        match_time = time_element.get_text(strip=True)
                    else:
                        match_time = "LIVE"
                elif 'finished' in status_text or 'ft' in status_text.lower():
                    status = "finished"
                    match_time = "FT"
                elif 'halftime' in status_text or 'ht' in status_text.lower():
                    status = "halftime"
                    match_time = "HT"
                elif 'half time' in status_text:
                    status = "halftime"
                    match_time = "HT"

            # Extract kickoff time for fixtures mode
            kickoff = "TBC"
            time_element = match_element.find('time', class_=re.compile(r'ssrcss.*Time'))
            if time_element:
                kickoff = time_element.get_text(strip=True)

            # Extract venue if available
            venue_element = match_element.find('span', class_=re.compile(r'ssrcss.*Venue|stadium'))
            venue = venue_element.get_text(strip=True) if venue_element else "TBC"

            return {
                "league": league_name,
                "home_team": home_team,
                "away_team": away_team,
                "kickoff": kickoff,
                "venue": venue,
                "home_score": home_score,
                "away_score": away_score,
                "status": status,
                "match_time": match_time,
                "last_updated": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error parsing live match data: {e}")
            return None

    def _parse_championship_match_data(self, match_element, league_name: str) -> Optional[Dict]:
        """
        Parse Championship match data from JSON embedded in HTML.

        Args:
            match_element: BeautifulSoup element containing match info
            league_name: Name of the league for this match

        Returns:
            Match dictionary or None if parsing failed
        """
        try:
            # Look for script tags containing match data
            script_tags = match_element.find_all('script', type='application/json')

            for script in script_tags:
                if script.string:
                    try:
                        data = json.loads(script.string)

                        # Navigate through the JSON structure to find match data
                        # Try multiple possible JSON structures
                        event_groups = None

                        # Structure 1: props/data/eventGroups (original structure)
                        if 'props' in data and 'data' in data['props']:
                            props_data = data['props']['data']
                            if 'eventGroups' in props_data:
                                event_groups = props_data['eventGroups']

                        # Structure 2: Direct eventGroups in data
                        elif 'data' in data and 'eventGroups' in data['data']:
                            event_groups = data['data']['eventGroups']

                        # Structure 3: Direct eventGroups in root
                        elif 'eventGroups' in data:
                            event_groups = data['eventGroups']

                        if event_groups:
                            for group in event_groups:
                                # Handle both direct events and nested secondaryGroups
                                events = []

                                if 'events' in group:
                                    events.extend(group['events'])
                                elif 'secondaryGroups' in group:
                                    for secondary_group in group['secondaryGroups']:
                                        if 'events' in secondary_group:
                                            events.extend(secondary_group['events'])

                                for event in events:
                                    # Extract match information
                                    if 'home' in event and 'away' in event:
                                        home_team = event['home'].get('fullName', '')
                                        away_team = event['away'].get('fullName', '')

                                        # Validate team names
                                        if (len(home_team) < 2 or len(away_team) < 2 or
                                            len(home_team) > 50 or len(away_team) > 50):
                                            continue

                                        # Extract kickoff time
                                        start_time = event.get('startDateTime', '')
                                        if start_time:
                                            # Convert UTC time to local time and extract hour:minute
                                            try:
                                                utc_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                                                local_time = utc_time.astimezone()  # Convert to local timezone
                                                kickoff = local_time.strftime('%H:%M')
                                            except:
                                                kickoff = "15:00"  # Default fallback
                                        else:
                                            kickoff = "15:00"

                                        # Only return matches at 15:00
                                        if kickoff == "15:00":
                                            return {
                                                "league": league_name,
                                                "home_team": home_team,
                                                "away_team": away_team,
                                                "kickoff": kickoff,
                                                "venue": "TBC"
                                            }

                    except json.JSONDecodeError:
                        continue

            return None

        except Exception as e:
            logger.error(f"Error parsing Championship match data: {e}")
            return None

    def scrape_unified_bbc_matches(self, target_date: str, mode: str = MODE_FIXTURES) -> Dict:
        """
        Scrape the unified BBC football page for all matches on the target date.

        This is the correct approach - scraping the main BBC page that contains
        ALL matches for the date, then filtering by our supported leagues.

        Args:
            target_date: Target date in YYYY-MM-DD format
            mode: Operating mode (fixtures or live)

        Returns:
            Dictionary containing scraping metadata and matches for all leagues
        """
        scraping_date = datetime.now().strftime("%Y-%m-%d")
        logger.info(f"Scraping unified BBC page for {target_date} in {mode} mode")

        # Use the main BBC football page URL
        full_url = self._build_bbc_url(target_date, mode)
        cache_key = self._get_cache_key(full_url, target_date)

        # Check cache first
        cached_data = self._get_cached_data(cache_key, target_date, "ALL_LEAGUES")
        if cached_data and self._is_cache_valid_for_date(target_date):
            logger.info(f"Using cached unified BBC data for {target_date}")
            return {
                "scraping_date": scraping_date,
                "target_date": target_date,
                "matches": cached_data.get('matches', []),
                "total_matches": len(cached_data.get('matches', []))
            }

        all_matches = []

        try:
            soup = self._make_request(full_url)
            if not soup:
                logger.error(f"Failed to retrieve unified BBC page: {full_url}")
                return {
                    "scraping_date": scraping_date,
                    "target_date": target_date,
                    "matches": [],
                    "total_matches": 0
                }

            # Parse all matches from the unified page
            matches = self._parse_unified_matches(soup, mode)

            # Filter to only our supported leagues
            supported_matches = []
            for match in matches:
                league_name = match.get('league', '')
                if league_name in self.LEAGUES.keys():
                    supported_matches.append(match)

            # Cache the results
            if supported_matches:
                cache_data = {'matches': supported_matches}
                self._save_cache_data(cache_key, cache_data, target_date, "ALL_LEAGUES")
                logger.info(f"Cached {len(supported_matches)} unified matches for {target_date}")

            result = {
                "scraping_date": scraping_date,
                "target_date": target_date,
                "matches": supported_matches,
                "total_matches": len(supported_matches)
            }

            logger.info(f"Found {len(supported_matches)} matches across all supported leagues")

            # Log summary by league
            league_summary = {}
            for league_name in self.LEAGUES.keys():
                league_matches = [match for match in supported_matches if match.get('league') == league_name]
                league_summary[league_name] = len(league_matches)

            logger.info(f"Matches by league: {league_summary}")

            return result

        except Exception as e:
            logger.error(f"Error scraping unified BBC page: {e}")
            return {
                "scraping_date": scraping_date,
                "target_date": target_date,
                "matches": [],
                "total_matches": 0
            }

    def _parse_unified_matches(self, soup: BeautifulSoup, mode: str) -> List[Dict]:
        """
        Parse all matches from the unified BBC page.

        Args:
            soup: BeautifulSoup object of the BBC page
            mode: Operating mode (fixtures or live)

        Returns:
            List of match dictionaries
        """
        matches = []

        try:
            # NEW APPROACH: Look for elements containing "versus" and "kick off"
            # This is more targeted than looking for all ssrcss elements

            # Find all elements that contain match information
            match_elements = []

            # Look for elements containing "versus" - these are likely match containers
            versus_elements = soup.find_all(string=re.compile(r'versus', re.IGNORECASE))

            for versus_element in versus_elements:
                # Get the parent element that contains the match info
                parent = versus_element.parent

                # Look for elements that also contain "kick off" (indicating a match)
                if parent and 'kick off' in parent.get_text().lower():
                    match_elements.append(parent)

            # Also look for script tags with JSON data (for Championship)
            script_tags = soup.find_all('script', type='application/json')
            for script in script_tags:
                if script.string:
                    try:
                        data = json.loads(script.string)
                        # Extract matches from JSON data if present
                        json_matches = self._extract_matches_from_json(data)
                        if json_matches:
                            matches.extend(json_matches)
                    except json.JSONDecodeError:
                        continue

            processed_matches = set()

            # Process each match element
            for match_element in match_elements:
                match = self._parse_unified_match_data(match_element, mode)
                if match:
                    # Create unique match key to avoid duplicates
                    match_key = f"{match['home_team']}_{match['away_team']}_{match['league']}"
                    if match_key not in processed_matches:
                        processed_matches.add(match_key)
                        matches.append(match)

            logger.info(f"Parsed {len(matches)} matches from unified BBC page")
            return matches

        except Exception as e:
            logger.error(f"Error parsing unified matches: {e}")
            return []

    def _parse_unified_match_data(self, match_element, mode: str) -> Optional[Dict]:
        """
        Parse individual match data from unified BBC page element.

        Args:
            match_element: BeautifulSoup element containing match info
            mode: Operating mode (fixtures or live)

        Returns:
            Match dictionary or None if parsing failed
        """
        try:
            # NEW APPROACH: Look for the specific BBC match structure
            # The BBC page has a different structure than expected

            # Look for elements containing match information
            # BBC uses spans with match text and time elements nearby
            match_text_element = None

            # Find elements that contain "versus" and "kick off"
            for element in match_element.find_all(string=lambda text: text and 'versus' in text.lower() and 'kick off' in text):
                match_text_element = element
                break

            if not match_text_element:
                return None

            # Get the full match text
            match_text = match_text_element.strip()

            # Extract teams from pattern like "Team A versus Team B kick off 15:00"
            versus_pattern = re.search(r'(.+?)\s+versus\s+(.+?)\s+kick off (\d{1,2}:\d{2})', match_text, re.IGNORECASE)
            if not versus_pattern:
                return None

            home_team = versus_pattern.group(1).strip()
            away_team = versus_pattern.group(2).strip()
            kickoff = versus_pattern.group(3).strip()

            # Validate team names
            if (len(home_team) < 2 or len(away_team) < 2 or
                len(home_team) > 50 or len(away_team) > 50):
                return None

            # Determine league - look for league headers in nearby elements
            league_name = self._identify_league_from_context(match_element)
            if not league_name or league_name not in self.LEAGUES.keys():
                return None

            # Extract venue if available (look for stadium/venue info)
            venue = "TBC"
            venue_patterns = ['stadium', 'venue', 'ground']
            for pattern in venue_patterns:
                venue_element = match_element.find(string=lambda text: text and pattern in text.lower())
                if venue_element:
                    venue = venue_element.strip()
                    break

            return {
                "league": league_name,
                "home_team": home_team,
                "away_team": away_team,
                "kickoff": kickoff,
                "venue": venue,
                "home_score": 0,
                "away_score": 0,
                "status": "not_started",
                "match_time": "0'"
            }

        except Exception as e:
            logger.error(f"Error parsing unified match data: {e}")
            return None

    def _identify_league_from_element(self, element) -> Optional[str]:
        """Identify the league name from a match element."""
        # Look for league headers above the match
        league_headers = [
            "Premier League", "English Championship", "English League One",
            "English League Two", "English National League",
            "Scottish Premiership", "Scottish Championship",
            "Scottish League One", "Scottish League Two"
        ]

        # Check the element text for league names
        element_text = element.get_text()
        for league in league_headers:
            if league.lower() in element_text.lower():
                return league

        return None

    def _identify_league_from_context(self, element) -> Optional[str]:
        """Identify the league name from the broader context around a match element."""
        # NEW APPROACH: Use document structure to find league headers
        # Look backwards from the match element to find the nearest league header

        league_headers = [
            "Premier League", "English Championship", "English League One",
            "English League Two", "English National League",
            "Scottish Premiership", "Scottish Championship",
            "Scottish League One", "Scottish League Two"
        ]

        # Start from the match element and look backwards through the document
        current_element = element

        # Look at preceding siblings and their children
        for _ in range(10):  # Look back up to 10 levels
            if current_element:
                # Check if current element contains league name
                element_text = current_element.get_text()
                for league in league_headers:
                    if league.lower() in element_text.lower():
                        return league

                # Move to previous sibling or parent
                if current_element.previous_sibling:
                    current_element = current_element.previous_sibling
                elif current_element.parent:
                    current_element = current_element.parent
                else:
                    break
            else:
                break

        return None

    def _extract_teams_and_scores(self, element, mode: str) -> Optional[tuple]:
        """Extract team names and scores from match element."""
        try:
            # Pattern 1: Look for "Team A vs Team B" or "Team A X-Y Team B"
            text_patterns = [
                r'(.+?)\s+(\d+)-(\d+)\s+(.+)',  # Team A 2-1 Team B
                r'(.+?)\s+vs?\s+(.+)',          # Team A vs Team B
            ]

            element_text = element.get_text()
            element_str = str(element)

            for pattern in text_patterns:
                match = re.search(pattern, element_text, re.IGNORECASE)
                if match:
                    if len(match.groups()) == 4:  # Score pattern
                        home_team, home_score, away_score, away_team = match.groups()
                        home_score, away_score = int(home_score), int(away_score)

                        # Determine status based on scores and mode
                        if mode == self.MODE_LIVE:
                            if home_score > 0 or away_score > 0:
                                status = "live"
                                match_time = "LIVE"
                            else:
                                status = "not_started"
                                match_time = "0'"
                        else:
                            status = "not_started"
                            match_time = "0'"

                        return home_team.strip(), away_team.strip(), home_score, away_score, status, match_time

                    elif len(match.groups()) == 2:  # No score pattern
                        home_team, away_team = match.groups()

                        if mode == self.MODE_LIVE:
                            # Try to find scores in the element
                            score_match = re.search(r'(\d+)-(\d+)', element_text)
                            if score_match:
                                home_score, away_score = map(int, score_match.groups())
                                status = "live" if home_score > 0 or away_score > 0 else "not_started"
                                match_time = "LIVE" if status == "live" else "0'"
                            else:
                                home_score, away_score = 0, 0
                                status = "not_started"
                                match_time = "0'"
                        else:
                            home_score, away_score = 0, 0
                            status = "not_started"
                            match_time = "0'"

                        return home_team.strip(), away_team.strip(), home_score, away_score, status, match_time

            return None

        except Exception as e:
            logger.error(f"Error extracting teams and scores: {e}")
            return None

    def _extract_matches_from_json(self, data: Dict) -> List[Dict]:
        """Extract match data from JSON embedded in BBC pages."""
        matches = []

        try:
            # Navigate through various possible JSON structures
            event_groups = None

            # Try different JSON structures
            if 'props' in data and 'data' in data['props']:
                props_data = data['props']['data']
                if 'eventGroups' in props_data:
                    event_groups = props_data['eventGroups']

            elif 'data' in data and 'eventGroups' in data['data']:
                event_groups = data['data']['eventGroups']

            elif 'eventGroups' in data:
                event_groups = data['eventGroups']

            if event_groups:
                for group in event_groups:
                    events = []

                    if 'events' in group:
                        events.extend(group['events'])
                    elif 'secondaryGroups' in group:
                        for secondary_group in group['secondaryGroups']:
                            if 'events' in secondary_group:
                                events.extend(secondary_group['events'])

                    for event in events:
                        if 'home' in event and 'away' in event:
                            home_team = event['home'].get('fullName', '')
                            away_team = event['away'].get('fullName', '')

                            if len(home_team) > 2 and len(away_team) > 2:
                                # Determine league (would need to be passed or inferred)
                                league_name = "Unknown League"  # Would need better logic here

                                matches.append({
                                    "league": league_name,
                                    "home_team": home_team,
                                    "away_team": away_team,
                                    "home_score": 0,
                                    "away_score": 0,
                                    "status": "not_started",
                                    "match_time": "0'",
                                    "kickoff": "15:00",
                                    "venue": "TBC"
                                })

            return matches

        except Exception as e:
            logger.error(f"Error extracting matches from JSON: {e}")
            return []

        cache_key = self._get_cache_key(full_url, target_date)

        # Check if cache is valid for this date first
        if not self._is_cache_valid_for_date(target_date):
            logger.info(f"Cache invalid for date {target_date} - too far in future or past")
            # Don't use cache for invalid dates

        # Check cache first (only if date is valid)
        cached_data = self._get_cached_data(cache_key, target_date, league_name)
        if cached_data and self._is_cache_valid_for_date(target_date):
            logger.info(f"Using valid cached data for {target_date} - {league_name}")
            return cached_data.get('matches', [])

        matches = []

        try:
            soup = self._make_request(full_url)
            if not soup:
                logger.error(f"Failed to retrieve data from {full_url}")
                # If scraping fails, try to return cached data even if slightly old
                if cached_data:
                    logger.warning(f"Using stale cache due to scraping failure for {league_name}")
                    return cached_data.get('matches', [])
                return matches

            # Special handling for Championship leagues - they use different structure
            if league_name in ["English Championship", "Scottish Championship"]:
                # For Championship, we need to look at the entire page structure
                # The match data is embedded in JSON within script tags
                fixture_containers = soup.find_all(['script', 'div', 'section'])
            else:
                # Look for fixture containers - NEW BBC Sport structure uses ssrcss classes
                # Be more specific to avoid duplicates - look for match containers with time elements
                fixture_containers = soup.find_all(['div', 'section'], class_=re.compile(r'ssrcss'))

            processed_matches = set()  # Track processed matches to avoid duplicates

            for container in fixture_containers:
                match = self._parse_match_data(container, league_name, mode)
                if match:
                    # Create unique match key to avoid duplicates
                    match_key = f"{match['home_team']}_{match['away_team']}_{match['kickoff']}"
                    if match_key not in processed_matches:
                        processed_matches.add(match_key)
                        matches.append(match)

            # Only cache if we got valid results
            if matches:
                cache_data = {'matches': matches}
                self._save_cache_data(cache_key, cache_data, target_date, league_name)
                logger.info(f"Cached {len(matches)} matches for {league_name}")
            else:
                if league_name in ["English Championship", "Scottish Championship"]:
                    logger.info(f"No matches found for {league_name} - this may be due to international break or scheduled weekend off")
                else:
                    logger.warning(f"No matches found for {league_name} - not caching empty results")

        except Exception as e:
            logger.error(f"Error scraping {league_name}: {e}")
            # If scraping fails, try to return cached data even if slightly old
            if cached_data:
                logger.warning(f"Using stale cache due to scraping error for {league_name}")
                return cached_data.get('matches', [])

        return matches

    def scrape_live_scores(self, target_date: Optional[str] = None) -> Dict:
        """
        Scrape live scores using the unified BBC page approach.

        Args:
            target_date: Target date in YYYY-MM-DD format (defaults to today)

        Returns:
            Dictionary containing scraping metadata and live matches
        """
        if target_date is None:
            target_date = datetime.now().strftime("%Y-%m-%d")

        logger.info(f"Scraping unified BBC live scores for {target_date}")

        # Use the unified scraping approach for live scores
        unified_result = self.scrape_unified_bbc_matches(target_date, self.MODE_LIVE)

        # For live mode, include all matches (not just 15:00)
        live_matches = unified_result.get("matches", [])

        result = {
            "scraping_date": unified_result.get("scraping_date"),
            "target_date": unified_result.get("target_date"),
            "live_matches": live_matches,
            "total_matches": len(live_matches)
        }

        logger.info(f"Total live matches found: {len(live_matches)}")

        # Log summary by league for transparency
        league_summary = {}
        for league_name in self.LEAGUES.keys():
            league_matches = [match for match in live_matches if match.get('league') == league_name]
            league_summary[league_name] = len(league_matches)

        logger.info(f"Live matches by league: {league_summary}")

        return result

    def scrape_saturday_3pm_fixtures(self) -> Dict:
        """
        Scrape next Saturday's 15:00 fixtures using the unified BBC page approach.

        Returns:
            Dictionary containing scraping metadata and matches
        """
        scraping_date, next_saturday = self._get_next_saturday()

        logger.info(f"Scraping unified BBC fixtures for Saturday {next_saturday}")

        # Use the unified scraping approach with the FIXED parsing logic
        unified_result = self.scrape_unified_bbc_matches(next_saturday, self.MODE_FIXTURES)

        # Filter for exactly 15:00 matches
        all_matches = unified_result.get("matches", [])
        matches_3pm = [match for match in all_matches if match.get('kickoff') == '15:00']

        result = {
            "scraping_date": unified_result.get("scraping_date"),
            "next_saturday": unified_result.get("target_date"),
            "matches_3pm": matches_3pm,
            "all_matches": all_matches,
            "total_3pm_matches": len(matches_3pm),
            "total_all_matches": len(all_matches)
        }

        logger.info(f"Total matches found: {len(all_matches)} ({len(matches_3pm)} at 15:00)")

        # Log summary by league for transparency
        league_summary = {}
        for league_name in self.LEAGUES.keys():
            league_matches = [match for match in all_matches if match.get('league') == league_name]
            league_summary[league_name] = len(league_matches)

        logger.info(f"Matches by league: {league_summary}")

        return result

    def clear_cache(self):
        """Clear all cached BBC scraper data using DataManager."""
        try:
            # Get all fixture cache files from DataManager
            fixtures_path = data_manager.fixtures_path
            cache_files = [f for f in os.listdir(fixtures_path) if f.startswith('bbc_cache_')]

            removed_count = 0
            for cache_file in cache_files:
                try:
                    os.remove(os.path.join(fixtures_path, cache_file))
                    removed_count += 1
                except Exception as e:
                    logger.warning(f"Could not remove cache file {cache_file}: {e}")

            logger.info(f"Cleared {removed_count} BBC cache files")
        except Exception as e:
            logger.error(f"Error clearing BBC cache: {e}")


def debug_championship_parsing():
    """Debug function to examine Championship page structure and JSON data."""
    scraper = BBCSportScraper(rate_limit=0.5)

    # Get next Saturday
    scraping_date, next_saturday = scraper._get_next_saturday()
    print(f"Debugging Championship parsing for {next_saturday}")

    # Make request to Championship page with NEW URL format
    championship_url = "/sport/football/championship/scores-fixtures"
    # Use the same dynamic URL construction as the main scraper
    date_parts = next_saturday.split('-')
    if len(date_parts) >= 2:
        year_month = f"{date_parts[0]}-{date_parts[1]}"
        full_url = urljoin(scraper.BASE_URL, f"{championship_url}/{year_month}?filter=fixtures")
    else:
        full_url = urljoin(scraper.BASE_URL, championship_url)

    print(f"Debug URL: {full_url}")

    soup = scraper._make_request(full_url)
    if not soup:
        print("Failed to retrieve Championship page")
        return

    print(f"Successfully retrieved Championship page: {full_url}")
    print(f"Page title: {soup.title.text if soup.title else 'No title'}")

    # Look for script tags with JSON data
    script_tags = soup.find_all('script', type='application/json')
    print(f"\nFound {len(script_tags)} script tags with JSON data")

    for i, script in enumerate(script_tags):  # Examine ALL scripts
        if script.string:
            try:
                # Clean the JSON string (remove any potential issues)
                json_str = script.string.strip()

                # Skip if it looks like CSS or other non-JSON content
                if json_str.startswith('{') and '{' in json_str and '}' in json_str:
                    data = json.loads(json_str)
                    print(f"\nScript {i+1} JSON structure:")

                    # Print the top-level keys and structure
                    if isinstance(data, dict):
                        for key in data.keys():
                            print(f"  Top-level key: {key}")
                            if isinstance(data[key], dict):
                                sub_keys = list(data[key].keys())[:10]  # Show first 10 sub-keys
                                print(f"    Sub-keys: {sub_keys}")

                                # Look deeper for eventGroups
                                if 'eventGroups' in data[key]:
                                    print(f"    Found eventGroups: {len(data[key]['eventGroups'])} groups")
                                    for j, group in enumerate(data[key]['eventGroups'][:2]):  # Show first 2 groups
                                        print(f"      Group {j+1}: {list(group.keys())}")
                                        if 'events' in group:
                                            print(f"        Direct events: {len(group['events'])}")
                                        if 'secondaryGroups' in group:
                                            print(f"        Secondary groups: {len(group['secondaryGroups'])}")

                    # Also check if the entire data structure contains eventGroups
                    if 'eventGroups' in data:
                        print(f"  Found eventGroups at root level: {len(data['eventGroups'])} groups")

            except json.JSONDecodeError as e:
                print(f"  Script {i+1} is not valid JSON: {str(e)[:100]}...")
            except Exception as e:
                print(f"  Error processing script {i+1}: {str(e)[:100]}...")

    # Also check for visible match text
    print("\nVisible match text on page:")
    match_text_elements = soup.find_all(string=re.compile(r'\w+\s+versus\s+\w+', re.IGNORECASE))
    for i, elem in enumerate(match_text_elements[:10]):  # Show first 10
        print(f"  Match {i+1}: '{elem.strip()}'")

    return soup


def test_championship_fix():
    """Test function to verify Championship scraping fix."""
    scraper = BBCSportScraper(rate_limit=0.5)

    # Test Championship specifically
    league_name = "English Championship"
    league_url = "/sport/football/championship/scores-fixtures"
    scraping_date, next_saturday = scraper._get_next_saturday()

    print(f"Testing Championship scraping for {next_saturday}")

    # Use the unified scraping approach
    unified_result = scraper.scrape_unified_bbc_matches(next_saturday, "fixtures")
    matches = unified_result.get("matches", [])

    print(f"Found {len(matches)} matches for {league_name}")

    for match in matches:
        print(f"  {match['home_team']} vs {match['away_team']} ({match['kickoff']})")

    return matches


def test_dynamic_url_construction():
    """Test function to verify dynamic URL construction for different months."""
    scraper = BBCSportScraper(rate_limit=2.0)

    # Test different date formats
    test_dates = [
        "2025-10-18",  # October 2025
        "2025-11-15",  # November 2025
        "2025-12-20",  # December 2025
        "2026-01-10",  # January 2026
    ]

    league_name = "English Championship"
    league_url = "/sport/football/championship/scores-fixtures"

    print("Testing dynamic URL construction for different months:")
    print("=" * 60)

    for test_date in test_dates:
        # Extract year-month from target_date for URL construction
        date_parts = test_date.split('-')
        if len(date_parts) >= 2:
            year_month = f"{date_parts[0]}-{date_parts[1]}"
            full_url = urljoin(scraper.BASE_URL, f"{league_url}/{year_month}?filter=fixtures")
        else:
            full_url = urljoin(scraper.BASE_URL, league_url)

        print(f"Date: {test_date} -> URL: {full_url}")

    print("=" * 60)


def test_new_bbc_scraper():
    """Test function for the new enhanced BBC scraper functionality."""
    print("🧪 Testing Enhanced BBC Scraper")
    print("=" * 50)

    scraper = BBCSportScraper(rate_limit=1.0)

    # Test URL construction
    print("\n1. Testing URL Construction:")
    test_date = "2025-10-25"
    fixtures_url = scraper._build_bbc_url(test_date, scraper.MODE_FIXTURES)
    live_url = scraper._build_bbc_url(test_date, scraper.MODE_LIVE)

    print(f"   Fixtures URL: {fixtures_url}")
    print(f"   Live URL: {live_url}")

    # Test league URL construction
    print("\n2. Testing League URL Construction:")
    for league_name, league_url in list(scraper.LEAGUES.items())[:3]:  # Test first 3 leagues
        league_fixture_url = scraper._build_league_url(league_url, test_date, scraper.MODE_FIXTURES)
        league_live_url = scraper._build_league_url(league_url, test_date, scraper.MODE_LIVE)
        print(f"   {league_name}:")
        print(f"     Fixtures: {league_fixture_url}")
        print(f"     Live: {league_live_url}")

    # Test live score scraping (if it's a match day)
    print("\n3. Testing Live Score Scraping:")
    try:
        live_result = scraper.scrape_live_scores(test_date)
        print(f"   Found {live_result['total_matches']} live matches")

        if live_result['live_matches']:
            print("   Sample match data:")
            for match in live_result['live_matches'][:3]:  # Show first 3 matches
                print(f"     {match['home_team']} vs {match['away_team']} ({match.get('status', 'unknown')})")
                if 'home_score' in match and 'away_score' in match:
                    print(f"       Score: {match['home_score']}-{match['away_score']}")
                    print(f"       Time: {match.get('match_time', 'N/A')}")
    except Exception as e:
        print(f"   Live scraping test failed: {e}")

    # Test fixture scraping
    print("\n4. Testing Fixture Scraping:")
    try:
        fixture_result = scraper.scrape_saturday_3pm_fixtures()
        print(f"   Found {len(fixture_result['matches_3pm'])} 15:00 fixtures")
        if fixture_result['matches_3pm']:
            print("   Sample fixtures:")
            for match in fixture_result['matches_3pm'][:3]:
                print(f"     {match['home_team']} vs {match['away_team']} ({match['league']}) at {match['kickoff']}")
    except Exception as e:
        print(f"   Fixture scraping test failed: {e}")

    print("\n✅ Enhanced BBC Scraper Tests Completed")


def test_api_endpoints():
    """Test the new API endpoints without running Flask server."""
    print("🔗 Testing API Endpoint Logic")
    print("=" * 50)

    # Test the logic that would be used in API endpoints
    scraper = BBCSportScraper(rate_limit=2.0)

    # Test fixtures endpoint logic
    print("\n1. Testing BBC Fixtures API Logic:")
    try:
        scraper_result = scraper.scrape_saturday_3pm_fixtures()
        api_response = {
            "success": True,
            "scraping_date": scraper_result.get("scraping_date"),
            "next_saturday": scraper_result.get("next_saturday"),
            "matches": scraper_result.get("matches_3pm", []),
            "total_matches": len(scraper_result.get("matches_3pm", [])),
        }
        print(f"   Success: {api_response['success']}")
        print(f"   Total matches: {api_response['total_matches']}")
        print(f"   Next Saturday: {api_response['next_saturday']}")
    except Exception as e:
        print(f"   Error: {e}")

    # Test live scores endpoint logic
    print("\n2. Testing BBC Live Scores API Logic:")
    try:
        live_result = scraper.scrape_live_scores()
        api_response = {
            "success": True,
            "target_date": live_result.get("target_date"),
            "live_matches": live_result.get("live_matches", []),
            "total_matches": live_result.get("total_matches", 0),
        }
        print(f"   Success: {api_response['success']}")
        print(f"   Total live matches: {api_response['total_matches']}")
        print(f"   Target date: {api_response['target_date']}")
    except Exception as e:
        print(f"   Error: {e}")

    print("\n✅ API Endpoint Logic Tests Completed")


def main():
    """Main function for testing the scraper."""
    scraper = BBCSportScraper(rate_limit=0.5)  # Faster rate limit for testing
    result = scraper.scrape_saturday_3pm_fixtures()

    # Print formatted output similar to admin page style
    print_bbc_scraper_results(result)


def print_bbc_scraper_results(result):
    """Print BBC scraper results in a formatted, admin-page-like layout."""
    print("=" * 80)
    print("🏆 BBC SPORT FOOTBALL FIXTURES SCRAPER")
    print("=" * 80)
    print(f"📅 Scraping Date: {result['scraping_date']}")
    print(f"🎯 Target Date: {result['next_saturday']}")
    print(f"⚽ Total Matches Found: {len(result['matches_3pm'])}")
    print()

    if not result['matches_3pm']:
        print("❌ No 15:00 matches found for the target date.")
        print("This may be due to:")
        print("  • International break")
        print("  • Scheduled weekend off")
        print("  • BBC website structure changes")
        return

    # Group matches by league
    leagues = {}
    for match in result['matches_3pm']:
        league = match['league']
        if league not in leagues:
            leagues[league] = []
        leagues[league].append(match)

    # Print matches in admin-page-like format
    for league, matches in leagues.items():
        print(f"🏆 {league}")
        print(f"   Matches: {len(matches)}")
        print()

        for i, match in enumerate(matches, 1):
            print(f"   {i}. {match['home_team']}")
            print(f"      vs")
            print(f"      {match['away_team']}")
            print(f"      🕐 Kickoff: {match['kickoff']}")
            if match['venue'] != "TBC":
                print(f"      📍 Venue: {match['venue']}")
            print()

    print("=" * 80)
    print("✅ SCRAPER COMPLETED SUCCESSFULLY")
    print("=" * 80)

    # Also print raw JSON for debugging
    print("\n🔧 RAW JSON OUTPUT (for debugging):")
    print("-" * 40)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "test":
            test_new_bbc_scraper()
        elif sys.argv[1] == "api-test":
            test_api_endpoints()
        else:
            print("Usage: python bbc_scraper.py [test|api-test]")
            print("  test     - Test enhanced BBC scraper functionality")
            print("  api-test - Test API endpoint logic")
    else:
        main()