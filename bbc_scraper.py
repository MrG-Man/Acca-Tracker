#!/usr/bin/env python3
"""
BBC Sport Football Fixtures Scraper

Scrapes BBC Sport for football fixtures from 8 leagues focusing on next Saturday's 15:00 matches.
Returns structured data for admin interface with zero API calls.

Author: Football Predictions System
Date: 2024
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

# Import DataManager for caching
from data_manager import data_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BBCSportScraper:
    """
    BBC Sport scraper for football fixtures.

    Scrapes match data from BBC Sport website for English and Scottish leagues,
    focusing specifically on next Saturday's 15:00 kickoffs.
    """

    # Base URL for BBC Sport
    BASE_URL = "https://www.bbc.co.uk"

    # League configurations with their BBC Sport URLs
    LEAGUES = {
        # English Leagues
        "Premier League": "/sport/football/premier-league/scores-fixtures",
        "English Championship": "/sport/football/championship/scores-fixtures",
        "English League One": "/sport/football/league-one/scores-fixtures",
        "English League Two": "/sport/football/league-two/scores-fixtures",
        "English National League" "/sport/football/national-league/scores-fixtures",

        # Scottish Leagues
        "Scottish Premiership": "/sport/football/scottish-premiership/scores-fixtures",
        "Scottish Championship": "/sport/football/scottish-championship/scores-fixtures",
        "Scottish League One": "/sport/football/scottish-league-one/scores-fixtures",
        "Scottish League Two": "/sport/football/scottish-league-two/scores-fixtures",
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
        if days_until_saturday == 0 and today.weekday() == 5:  # If today is Saturday
            days_until_saturday = 7  # Get next Saturday

        next_saturday = today + timedelta(days=days_until_saturday)

        return today.strftime("%Y-%m-%d"), next_saturday.strftime("%Y-%m-%d")

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
        """Save data to cache using DataManager."""
        matches = data.get('matches', [])
        success = data_manager.cache_bbc_fixtures(matches, date)
        if success:
            logger.info(f"Cached BBC data for {date} - {league_name} using DataManager")
        else:
            logger.error(f"Failed to cache BBC data for {date} - {league_name}")

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

    def _parse_match_data(self, match_element, league_name: str) -> Optional[Dict]:
        """
        Parse individual match data from HTML element.

        Args:
            match_element: BeautifulSoup element containing match info
            league_name: Name of the league for this match

        Returns:
            Match dictionary or None if parsing failed
        """
        try:
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
                "venue": venue
            }

        except Exception as e:
            logger.error(f"Error parsing match data: {e}")
            return None

    def _scrape_league_fixtures(self, league_name: str, league_url: str, target_date: str) -> List[Dict]:
        """
        Scrape fixtures for a specific league with aggressive caching.

        Args:
            league_name: Name of the league
            league_url: BBC Sport URL for the league
            target_date: Target date in YYYY-MM-DD format

        Returns:
            List of match dictionaries
        """
        full_url = urljoin(self.BASE_URL, league_url)
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

            # Look for fixture containers - NEW BBC Sport structure uses ssrcss classes
            # Be more specific to avoid duplicates - look for match containers with time elements
            fixture_containers = soup.find_all(['div', 'section'], class_=re.compile(r'ssrcss'))

            processed_matches = set()  # Track processed matches to avoid duplicates

            for container in fixture_containers:
                match = self._parse_match_data(container, league_name)
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
                logger.warning(f"No matches found for {league_name} - not caching empty results")

        except Exception as e:
            logger.error(f"Error scraping {league_name}: {e}")
            # If scraping fails, try to return cached data even if slightly old
            if cached_data:
                logger.warning(f"Using stale cache due to scraping error for {league_name}")
                return cached_data.get('matches', [])

        return matches

    def scrape_saturday_3pm_fixtures(self) -> Dict:
        """
        Scrape next Saturday's 15:00 fixtures from all leagues.

        Returns:
            Dictionary containing scraping metadata and matches
        """
        scraping_date, next_saturday = self._get_next_saturday()

        logger.info(f"Scraping fixtures for Saturday {next_saturday}")

        all_matches = []

        for league_name, league_url in self.LEAGUES.items():
            logger.info(f"Scraping {league_name}")
            matches = self._scrape_league_fixtures(league_name, league_url, next_saturday)

            # Filter for exactly 15:00 matches
            matches_3pm = [match for match in matches if match.get('kickoff') == '15:00']
            all_matches.extend(matches_3pm)

            logger.info(f"Found {len(matches_3pm)} 15:00 matches in {league_name}")

        result = {
            "scraping_date": scraping_date,
            "next_saturday": next_saturday,
            "matches_3pm": all_matches
        }

        logger.info(f"Total 15:00 matches found: {len(all_matches)}")
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


def main():
    """Main function for testing the scraper."""
    scraper = BBCSportScraper(rate_limit=0.5)  # Faster rate limit for testing
    result = scraper.scrape_saturday_3pm_fixtures()

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()