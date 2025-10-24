#!/usr/bin/env python3
"""
Live Score Manager for Football Predictions

Coordinates live score updates with ultra-low API usage:
- Event-driven updates (KO/HT/FT detection)
- Real-time BTTS detection
- Integration with DataManager for live data storage
- Maximum 12-16 API calls per month
- Zero API calls for match details (BBC handles this)

Author: Live Score Manager
Date: 2024
"""

import threading
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
import json
import os

# SOFASCORE API DISABLED - Using mock API
from data_manager import data_manager

# Import BTTS detector for integration
try:
    from btts_detector import btts_detector
    BTTS_DETECTOR_AVAILABLE = True
except ImportError:
    BTTS_DETECTOR_AVAILABLE = False

class BBCLiveScoresAPI:
    """
    BBC-based live scores API that integrates with the existing LiveScoreManager interface.
    Uses BBC scraper to fetch live scores instead of Sofascore.
    """

    def __init__(self, cache_dir="cache"):
        """Initialize BBC API with scraper."""
        self.cache_dir = cache_dir
        self.active_matches = {}
        self.btts_status = {}
        self.api_calls_used = 0

    def get_live_scores_batch(self, match_ids=None, use_cache=True):
        """Return live scores data from BBC."""
        try:
            from bbc_scraper import BBCSportScraper
            scraper = BBCSportScraper()
            target_date = datetime.now().strftime('%Y-%m-%d')
            live_result = scraper.scrape_live_scores(target_date)
            all_live_matches = live_result.get("live_matches", [])

            # Convert BBC format to Sofascore-like format for compatibility
            events = []
            for match in all_live_matches:
                event = {
                    'id': f"{match.get('league', 'Unknown')}_{match.get('home_team', '')}_{match.get('away_team', '')}",
                    'homeTeam': {'name': match.get('home_team', '')},
                    'awayTeam': {'name': match.get('away_team', '')},
                    'status': {'type': match.get('status', 'not_started')},
                    'homeScore': {'current': match.get('home_score', 0)},
                    'awayScore': {'current': match.get('away_score', 0)},
                    'bbc_data': match  # Keep original BBC data
                }
                events.append(event)

            self.api_calls_used += 1
            return {'events': events}

        except Exception as e:
            print(f"Error fetching BBC live scores: {e}")
            return {'events': []}

    def detect_match_events(self, live_data):
        """Detect events from BBC live data."""
        events = []
        if live_data and 'events' in live_data:
            for event in live_data['events']:
                # Check for BTTS events
                home_score = event.get('homeScore', {}).get('current', 0)
                away_score = event.get('awayScore', {}).get('current', 0)
                if home_score > 0 and away_score > 0:
                    events.append({
                        'type': 'btts',
                        'match_id': event['id'],
                        'timestamp': datetime.now(),
                        'score': f"{home_score}-{away_score}",
                        'home_team': event['homeTeam']['name'],
                        'away_team': event['awayTeam']['name']
                    })
        return events

    def get_usage_stats(self):
        """Return usage statistics."""
        return {
            'current_month': datetime.now().strftime('%Y-%m'),
            'api_calls_used': self.api_calls_used,
            'api_calls_target': 'Unlimited (BBC)',
            'cache_hits': 0,
            'cache_misses': 0,
            'events_detected': 0,
            'btts_detected': 0,
            'active_matches': len(self.active_matches),
            'cache_hit_rate': 0.0
        }

    def print_stats(self):
        """Print statistics."""
        print("📊 BBC LIVE SCORES API STATISTICS")
        print("="*50)
        print("🔌 Source: BBC Sport")
        print(f"📊 API Calls: {self.api_calls_used}")
        print("🎯 Status: Active")
        print("="*50)

class LiveScoreManager:
    """
    Manages live football score updates with minimal API usage.
    Integrates Sofascore live scores with the data management system.
    """

    def __init__(self, data_manager_instance=None, cache_dir="cache"):
        """
        Initialize the Live Score Manager

        Args:
            data_manager_instance: Instance of DataManager (uses global if None)
            cache_dir (str): Directory for caching live score data
        """
        self.data_manager = data_manager_instance or data_manager

        # Using BBC API for live scores
        self.live_api = BBCLiveScoresAPI(cache_dir=cache_dir)

        # Event callbacks
        self.event_callbacks = {
            'kickoff': [],
            'halftime': [],
            'fulltime': [],
            'goal': [],
            'btts': []
        }

        # BTTS tracking for accumulator
        self.btts_matches = {}  # Track matches where BTTS occurred
        self.live_data_storage = {}  # Store live data for each match

        # Control flags
        self.is_running = False
        self.update_thread = None
        self.stop_event = threading.Event()

        # Update intervals (event-driven, not time-based)
        self.min_update_interval = 60  # Minimum 1 minute between checks
        self.last_update = datetime.min

        # Setup logging
        self.logger = self._setup_logging()

        # Statistics
        self.stats = {
            'total_updates': 0,
            'events_processed': 0,
            'btts_detected': 0,
            'api_calls_made': 0,
            'last_activity': None
        }

    def _setup_logging(self) -> logging.Logger:
        """Setup logging for live score operations."""
        logger = logging.getLogger("LiveScoreManager")
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def add_event_callback(self, event_type: str, callback: Callable):
        """
        Add callback function for specific event types.

        Args:
            event_type (str): Type of event ('kickoff', 'halftime', 'fulltime', 'goal', 'btts')
            callback (Callable): Function to call when event occurs
        """
        if event_type in self.event_callbacks:
            self.event_callbacks[event_type].append(callback)
            self.logger.info(f"Added callback for event type: {event_type}")
        else:
            self.logger.warning(f"Unknown event type: {event_type}")

    def remove_event_callback(self, event_type: str, callback: Callable):
        """
        Remove callback function for specific event type.

        Args:
            event_type (str): Type of event
            callback (Callable): Function to remove
        """
        if event_type in self.event_callbacks:
            try:
                self.event_callbacks[event_type].remove(callback)
                self.logger.info(f"Removed callback for event type: {event_type}")
            except ValueError:
                self.logger.warning(f"Callback not found for event type: {event_type}")

    def _trigger_event_callbacks(self, event_type: str, event_data: Dict):
        """
        Trigger all callbacks for a specific event type.

        Args:
            event_type (str): Type of event
            event_data (Dict): Event data to pass to callbacks
        """
        for callback in self.event_callbacks.get(event_type, []):
            try:
                callback(event_data)
            except Exception as e:
                self.logger.error(f"Error in {event_type} callback: {str(e)}")

    def _should_update(self) -> bool:
        """
        Determine if we should perform an update based on timing and API limits.

        Returns:
            bool: True if update should proceed
        """
        now = datetime.now()

        # Check minimum interval
        if now - self.last_update < timedelta(seconds=self.min_update_interval):
            return False

        # Check API usage limits
        usage_stats = self.live_api.get_usage_stats()
        if usage_stats['api_calls_used'] >= 16:  # Strict limit
            self.logger.warning("API usage limit reached, skipping update")
            return False

        return True

    def _process_live_scores(self, live_data: Dict) -> List[Dict]:
        """
        Process live scores data and detect events.

        Args:
            live_data (Dict): Live scores data from Sofascore API

        Returns:
            List[Dict]: List of detected events
        """
        if not live_data or 'events' not in live_data:
            return []

        # Detect events using the API's event detection
        detected_events = self.live_api.detect_match_events(live_data)

        # Process each detected event
        for event in detected_events:
            self.stats['events_processed'] += 1
            event_type = event['type']
            match_id = event['match_id']

            # Store live data for this match
            if match_id not in self.live_data_storage:
                self.live_data_storage[match_id] = []

            self.live_data_storage[match_id].append({
                'event': event,
                'timestamp': event['timestamp'],
                'processed_at': datetime.now()
            })

            # Trigger callbacks for this event
            self._trigger_event_callbacks(event_type, event)

            # Special handling for BTTS events
            if event_type == 'btts':
                self.btts_matches[match_id] = event
                self.stats['btts_detected'] += 1
                self.logger.info(f"BTTS detected for match {match_id}")

                # Store BTTS result in data manager
                self._store_btts_result(match_id, event)

                # Notify BTTS detector if available
                if BTTS_DETECTOR_AVAILABLE:
                    try:
                        from btts_detector import btts_detector
                        btts_detector._process_btts_event(match_id, event)
                    except Exception as e:
                        self.logger.error(f"Error notifying BTTS detector: {str(e)}")

        return detected_events

    def _store_btts_result(self, match_id: str, btts_event: Dict):
        """
        Store BTTS result in the data manager for accumulator tracking.

        Args:
            match_id (str): Match identifier
            btts_event (Dict): BTTS event data
        """
        try:
            # Create BTTS result data structure
            btts_data = {
                'match_id': match_id,
                'detected_at': btts_event['timestamp'].isoformat(),
                'final_score': btts_event.get('score', 'Unknown'),
                'result': 'BTTS_YES'
            }

            # Store in data manager using the new live results methods
            success = self.data_manager.add_live_result(btts_data)

            if success:
                self.logger.info(f"BTTS result stored for match {match_id}: {btts_data['final_score']}")
            else:
                self.logger.error(f"Failed to store BTTS result for match {match_id}")

        except Exception as e:
            self.logger.error(f"Error storing BTTS result: {str(e)}")

    def update_live_scores(self) -> Dict[str, Any]:
        """
        Perform a live scores update if conditions are met.

        Returns:
            Dict: Update results and statistics
        """
        if not self._should_update():
            return {
                'success': False,
                'reason': 'Update skipped (timing or API limits)',
                'events_detected': 0
            }

        try:
            # Get live scores from API
            live_data = self.live_api.get_live_scores_batch()

            if not live_data:
                return {
                    'success': False,
                    'reason': 'No live data received from API',
                    'events_detected': 0
                }

            # Process the live data and detect events
            detected_events = self._process_live_scores(live_data)

            # Update statistics
            self.stats['total_updates'] += 1
            self.stats['api_calls_made'] += 1
            self.stats['last_activity'] = datetime.now()
            self.last_update = datetime.now()

            result = {
                'success': True,
                'events_detected': len(detected_events),
                'event_types': [event['type'] for event in detected_events],
                'matches_tracked': len(self.live_api.active_matches),
                'api_calls_used': self.live_api.get_usage_stats()['api_calls_used']
            }

            if detected_events:
                self.logger.info(f"Live update successful: {len(detected_events)} events detected")
            else:
                self.logger.debug("Live update completed: No new events")

            return result

        except Exception as e:
            self.logger.error(f"Error during live scores update: {str(e)}")
            return {
                'success': False,
                'reason': f'Update error: {str(e)}',
                'events_detected': 0
            }

    def start_continuous_updates(self, update_interval: int = 120):
        """
        Start continuous live score updates in a background thread.

        Args:
            update_interval (int): Seconds between update attempts (minimum 60)
        """
        if self.is_running:
            self.logger.warning("Continuous updates already running")
            return

        # Enforce minimum interval
        update_interval = max(update_interval, self.min_update_interval)

        self.is_running = True
        self.stop_event.clear()

        self.update_thread = threading.Thread(
            target=self._continuous_update_loop,
            args=(update_interval,),
            daemon=True
        )
        self.update_thread.start()

        self.logger.info(f"Started continuous live score updates (interval: {update_interval}s)")

    def stop_continuous_updates(self):
        """Stop continuous live score updates."""
        if not self.is_running:
            return

        self.is_running = False
        self.stop_event.set()

        if self.update_thread and self.update_thread.is_alive():
            self.update_thread.join(timeout=5.0)

        self.logger.info("Stopped continuous live score updates")

    def _continuous_update_loop(self, update_interval: int):
        """
        Background thread loop for continuous updates.

        Args:
            update_interval (int): Seconds between update attempts
        """
        self.logger.info("Live score update loop started")

        while not self.stop_event.is_set():
            try:
                # Perform update
                result = self.update_live_scores()

                # Log if we actually made an API call
                if result.get('success', False):
                    self.logger.debug(f"Update completed: {result['events_detected']} events")

                # Wait for next interval (or until stopped)
                if self.stop_event.wait(update_interval):
                    break  # Stop event was set

            except Exception as e:
                self.logger.error(f"Error in update loop: {str(e)}")
                if self.stop_event.wait(30):  # Wait 30s on error
                    break

        self.logger.info("Live score update loop stopped")

    def get_btts_matches(self) -> Dict[str, Dict]:
        """
        Get all matches where BTTS was detected.

        Returns:
            Dict: BTTS match data by match_id
        """
        return self.btts_matches.copy()

    def get_live_match_data(self, match_id: str) -> List[Dict]:
        """
        Get live data history for a specific match.

        Args:
            match_id (str): Match identifier

        Returns:
            List[Dict]: Live data events for the match
        """
        return self.live_data_storage.get(match_id, [])

    def get_manager_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive manager statistics.

        Returns:
            Dict: Manager statistics and performance data
        """
        api_stats = self.live_api.get_usage_stats()

        return {
            'manager_stats': self.stats.copy(),
            'api_stats': api_stats,
            'is_running': self.is_running,
            'active_matches': len(self.live_api.active_matches),
            'btts_matches_count': len(self.btts_matches),
            'last_update': self.last_update.isoformat() if self.last_update != datetime.min else None,
            'update_thread_alive': self.update_thread.is_alive() if self.update_thread else False
        }

    def reset_manager(self):
        """Reset manager state and statistics."""
        self.btts_matches.clear()
        self.live_data_storage.clear()
        self.stats = {
            'total_updates': 0,
            'events_processed': 0,
            'btts_detected': 0,
            'api_calls_made': 0,
            'last_activity': None
        }
        self.last_update = datetime.min
        self.logger.info("Live Score Manager reset")

    def cleanup_old_data(self, max_age_hours: int = 24):
        """
        Clean up old live data to prevent memory bloat.

        Args:
            max_age_hours (int): Maximum age of data to keep (hours)
        """
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

        # Clean up live data storage
        matches_to_remove = []
        for match_id, events in self.live_data_storage.items():
            # Keep only recent events
            recent_events = [
                event for event in events
                if event['processed_at'] > cutoff_time
            ]

            if recent_events:
                self.live_data_storage[match_id] = recent_events
            else:
                matches_to_remove.append(match_id)

        # Remove old matches
        for match_id in matches_to_remove:
            self.live_data_storage.pop(match_id, None)
            self.btts_matches.pop(match_id, None)

        if matches_to_remove:
            self.logger.info(f"Cleaned up {len(matches_to_remove)} old matches")

# Global instance for easy importing
live_score_manager = LiveScoreManager()

def main():
    """Main function demonstrating the Live Score Manager"""
    print("⚽ Live Score Manager for Football Predictions")
    print("="*60)
    print("🎯 Event-driven live score updates")
    print("🎯 Ultra-low API usage (12-16 calls/month)")
    print("🎯 Real-time BTTS detection")
    print("="*60)

    # Initialize manager
    manager = LiveScoreManager()

    # Add example event callbacks
    def on_kickoff(event_data):
        print(f"🏁 Kick-off: {event_data['home_team']} vs {event_data['away_team']}")

    def on_btts(event_data):
        print(f"🎯 BTTS DETECTED: Match {event_data['match_id']} - Score: {event_data['score']}")

    manager.add_event_callback('kickoff', on_kickoff)
    manager.add_event_callback('btts', on_btts)

    # Display initial stats
    manager.live_api.print_stats()

    print("\n🔄 Testing Live Score Manager:")
    print("-" * 40)

    # Test manual update
    print("\n1. Manual live score update...")
    result = manager.update_live_scores()

    if result['success']:
        print(f"✅ Update successful: {result['events_detected']} events detected")
        print(f"   Active matches: {result['matches_tracked']}")
        print(f"   API calls used: {result['api_calls_used']}/16")
    else:
        print(f"❌ Update failed: {result['reason']}")

    # Display final stats
    print("\n📊 Final Statistics:")
    stats = manager.get_manager_stats()
    print(f"   Total Updates: {stats['manager_stats']['total_updates']}")
    print(f"   Events Processed: {stats['manager_stats']['events_processed']}")
    print(f"   BTTS Detected: {stats['manager_stats']['btts_detected']}")
    print(f"   API Calls Made: {stats['manager_stats']['api_calls_made']}")

    print("\n✨ Live Score Manager features demonstrated:")
    print("   • Event-driven updates (not time-based)")
    print("   • Ultra-low API usage tracking")
    print("   • Real-time BTTS detection")
    print("   • Event callback system")
    print("   • Live data storage and retrieval")
    print("   • Comprehensive statistics")

if __name__ == "__main__":
    main()