#!/usr/bin/env python3
"""
BTTS Detection & Highlighting System for Football Predictions

Dedicated BTTS detector that integrates with the existing live score system
to provide real-time BTTS detection and accumulator tracking.

Author: BTTS Detection System
Date: 2024
"""

import threading
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any, Tuple
import json
import os

# SOFASCORE API TEMPORARILY DISABLED FOR TESTING
# from live_score_manager import live_score_manager
from data_manager import data_manager

# Mock live score manager for testing
class MockLiveScoreManager:
    """Mock live score manager that returns static data for testing."""

    def __init__(self):
        self.active_matches = {}

    def get_live_match_data(self, match_id):
        """Return mock live data for testing."""
        return [
            {
                'event': {
                    'type': 'not_started',
                    'score': {'home': 0, 'away': 0}
                },
                'processed_at': datetime.now()
            }
        ]

    def get_btts_matches(self):
        """Return empty BTTS matches for testing."""
        return {}

# Use mock live score manager for testing
live_score_manager = MockLiveScoreManager()

class BTTSDetector:
    """
    Dedicated BTTS detection system for accumulator tracking.

    Integrates with LiveScoreManager to detect when both teams score
    during the valid KO-FT window and provides clean interface for
    web display and accumulator tracking.
    """

    def __init__(self):
        """Initialize the BTTS Detector."""
        self.live_score_manager = live_score_manager
        self.data_manager = data_manager

        # BTTS tracking state
        self.btts_results = {}  # match_id -> BTTS result data
        self.match_selectors = {}  # match_id -> selector name
        self.active_matches = set()  # Currently active matches

        # Event callbacks for web interface
        self.btts_callbacks = []

        # Control flags
        self.is_monitoring = False
        self.monitor_thread = None
        self.stop_event = threading.Event()

        # Setup logging
        self.logger = self._setup_logging()

        # Statistics
        self.stats = {
            'total_matches_tracked': 0,
            'btts_detected': 0,
            'btts_pending': 0,
            'last_update': None,
            'monitoring_started': None
        }

    def _setup_logging(self) -> logging.Logger:
        """Setup logging for BTTS detection operations."""
        logger = logging.getLogger("BTTSDetector")
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def add_btts_callback(self, callback: Callable):
        """
        Add callback function for BTTS detection events.

        Args:
            callback (Callable): Function to call when BTTS is detected
        """
        self.btts_callbacks.append(callback)
        self.logger.info("Added BTTS detection callback")

    def remove_btts_callback(self, callback: Callable):
        """
        Remove BTTS detection callback.

        Args:
            callback (Callable): Function to remove
        """
        try:
            self.btts_callbacks.remove(callback)
            self.logger.info("Removed BTTS detection callback")
        except ValueError:
            self.logger.warning("BTTS callback not found")

    def _trigger_btts_callbacks(self, match_id: str, btts_data: Dict):
        """
        Trigger all BTTS callbacks for a detected event.

        Args:
            match_id (str): Match identifier
            btts_data (Dict): BTTS detection data
        """
        for callback in self.btts_callbacks:
            try:
                callback(match_id, btts_data)
            except Exception as e:
                self.logger.error(f"Error in BTTS callback: {str(e)}")

    def _process_btts_event(self, match_id: str, event_data: Dict):
        """
        Process BTTS event from LiveScoreManager.

        Args:
            match_id (str): Match identifier
            event_data (Dict): Event data from LiveScoreManager
        """
        try:
            # Extract score information
            home_score, away_score = self._extract_score_from_event_data(event_data)

            # Check if this is a valid BTTS detection
            if self._is_btts_detected(home_score, away_score):
                # Update our tracking
                if match_id not in self.btts_results:
                    self.btts_results[match_id] = {
                        'match_id': match_id,
                        'selector': self.match_selectors.get(match_id, 'Unknown'),
                        'btts_detected': False,
                        'first_detected': None,
                        'final_score': None,
                        'detection_events': []
                    }

                # Update BTTS detection status
                if not self.btts_results[match_id]['btts_detected']:
                    current_score = f"{home_score}-{away_score}"
                    self.btts_results[match_id]['btts_detected'] = True
                    self.btts_results[match_id]['first_detected'] = datetime.now().isoformat()
                    self.btts_results[match_id]['final_score'] = current_score
                    self.btts_results[match_id]['detection_events'].append({
                        'timestamp': datetime.now().isoformat(),
                        'score': current_score,
                        'event_type': 'btts_detected',
                        'source': 'live_score_manager'
                    })

                    # Update statistics
                    self.stats['btts_detected'] += 1
                    self.stats['last_update'] = datetime.now()

                    # Trigger callbacks
                    self._trigger_btts_callbacks(match_id, self.btts_results[match_id])

                    self.logger.info(f"BTTS processed from LiveScoreManager: {match_id} - Score: {current_score}")

        except Exception as e:
            self.logger.error(f"Error processing BTTS event: {str(e)}")

    def _extract_score_from_event_data(self, event_data: Dict) -> Tuple[int, int]:
        """
        Extract score from LiveScoreManager event data.

        Args:
            event_data (Dict): Event data from LiveScoreManager

        Returns:
            Tuple[int, int]: Home and away scores
        """
        try:
            # Try different score field locations
            score_data = None

            # Check direct score field
            if 'score' in event_data:
                score_data = event_data['score']
            # Check nested in event data
            elif 'event' in event_data and 'score' in event_data['event']:
                score_data = event_data['event']['score']

            if score_data and isinstance(score_data, dict):
                home_score = score_data.get('home', 0)
                away_score = score_data.get('away', 0)
                return home_score, away_score

            return 0, 0

        except Exception:
            return 0, 0

    def load_weekly_selections(self) -> Dict[str, Any]:
        """
        Load current week's match selections to map selectors to matches.

        Returns:
            Dict: Selection data with selector->match mapping
        """
        try:
            # Get current week string (next Saturday)
            week = self._get_current_week()

            # Load selections using data manager
            selections = self.data_manager.load_weekly_selections(week)

            if selections:
                # Build reverse mapping: match_id -> selector
                for selector, match_data in selections.items():
                    match_id = match_data.get('id')
                    if match_id:
                        self.match_selectors[match_id] = selector
                        self.active_matches.add(match_id)

                self.logger.info(f"Loaded {len(selections)} selections for week {week}")
                return selections
            else:
                self.logger.warning(f"No selections found for week {week}")
                return {}

        except Exception as e:
            self.logger.error(f"Error loading weekly selections: {str(e)}")
            return {}

    def _get_current_week(self) -> str:
        """Get current week string in YYYY-MM-DD format for next Saturday."""
        from bbc_scraper import BBCSportScraper
        scraper = BBCSportScraper()
        _, next_saturday = scraper._get_next_saturday()
        return next_saturday

    def _is_valid_btts_period(self, match_id: str) -> bool:
        """
        Check if match is in valid BTTS detection period (KO to FT).

        Args:
            match_id (str): Match identifier

        Returns:
            bool: True if in valid period
        """
        # Get live data for this match from live score manager
        live_data = self.live_score_manager.get_live_match_data(match_id)

        if not live_data:
            return False

        # Check latest event to determine match status
        latest_event = live_data[-1] if live_data else None

        if not latest_event:
            return False

        event_type = latest_event.get('event', {}).get('type', '')

        # Valid BTTS period: after kickoff, before fulltime
        if event_type == 'kickoff':
            return True
        elif event_type == 'fulltime':
            return False
        elif event_type in ['halftime', 'goal', 'btts']:
            # During live match period
            return True

        return False

    def _extract_score_from_event(self, event: Dict) -> Tuple[int, int]:
        """
        Extract current score from a match event.

        Args:
            event (Dict): Match event data

        Returns:
            Tuple[int, int]: Home and away scores
        """
        try:
            # Try to get score from event data
            score_data = event.get('event', {}).get('score', {})
            home_score = score_data.get('home', 0)
            away_score = score_data.get('away', 0)

            return home_score, away_score

        except Exception:
            return 0, 0

    def _is_btts_detected(self, home_score: int, away_score: int) -> bool:
        """
        Check if BTTS condition is met (both teams scored).

        Args:
            home_score (int): Home team score
            away_score (int): Away team score

        Returns:
            bool: True if both teams have scored
        """
        return home_score > 0 and away_score > 0

    def check_btts_status(self, match_id: str) -> Dict[str, Any]:
        """
        Check BTTS status for a specific match.
        SOFASCORE API DISABLED - Returning mock data for testing.

        Args:
            match_id (str): Match identifier

        Returns:
            Dict: BTTS status information
        """
        # SOFASCORE API DISABLED - Return mock data for testing
        selector = self.match_selectors.get(match_id, 'Unknown')

        return {
            'match_id': match_id,
            'btts_detected': False,  # Mock: No BTTS detected
            'current_score': '0-0',  # Mock: No goals yet
            'is_live': False,        # Mock: Not live
            'selector': selector,
            'last_updated': datetime.now().isoformat(),
            'status': 'SOFASCORE_API_DISABLED',
            'message': 'Live score tracking disabled for admin interface testing'
        }

    def get_all_btts_status(self) -> Dict[str, Any]:
        """
        Get BTTS status for all tracked matches.
        SOFASCORE API DISABLED - Returning mock data for testing.

        Returns:
            Dict: Complete BTTS status for all matches
        """
        # SOFASCORE API DISABLED - Return mock data for testing
        results = {}

        for match_id in self.active_matches:
            results[match_id] = self.check_btts_status(match_id)

        # Update statistics
        self.stats['total_matches_tracked'] = len(self.active_matches)
        self.stats['btts_pending'] = 0  # Mock: No pending BTTS
        self.stats['last_update'] = datetime.now()

        return {
            'matches': results,
            'statistics': self.stats.copy(),
            'last_updated': datetime.now().isoformat(),
            'status': 'SOFASCORE_API_DISABLED',
            'message': 'Live score tracking disabled for admin interface testing'
        }

    def start_monitoring(self, check_interval: int = 60):
        """
        Start continuous BTTS monitoring in background thread.

        Args:
            check_interval (int): Seconds between checks (minimum 30)
        """
        if self.is_monitoring:
            self.logger.warning("BTTS monitoring already running")
            return

        # Enforce minimum interval
        check_interval = max(check_interval, 30)

        self.is_monitoring = True
        self.stop_event.clear()
        self.stats['monitoring_started'] = datetime.now()

        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(check_interval,),
            daemon=True
        )
        self.monitor_thread.start()

        self.logger.info(f"Started BTTS monitoring (interval: {check_interval}s)")

    def stop_monitoring(self):
        """Stop BTTS monitoring."""
        if not self.is_monitoring:
            return

        self.is_monitoring = False
        self.stop_event.set()

        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5.0)

        self.logger.info("Stopped BTTS monitoring")

    def _monitoring_loop(self, check_interval: int):
        """
        Background monitoring loop.

        Args:
            check_interval (int): Seconds between checks
        """
        self.logger.info("BTTS monitoring loop started")

        while not self.stop_event.is_set():
            try:
                # Check BTTS status for all active matches
                all_status = self.get_all_btts_status()

                # Log summary
                matches_count = len(all_status['matches'])
                btts_count = len([m for m in all_status['matches'].values() if m['btts_detected']])

                if matches_count > 0:
                    self.logger.debug(f"BTTS Monitor: {btts_count}/{matches_count} BTTS detected")

                # Wait for next check (or until stopped)
                if self.stop_event.wait(check_interval):
                    break  # Stop event was set

            except Exception as e:
                self.logger.error(f"Error in BTTS monitoring loop: {str(e)}")
                if self.stop_event.wait(30):  # Wait 30s on error
                    break

        self.logger.info("BTTS monitoring loop stopped")

    def get_btts_summary(self) -> Dict[str, Any]:
        """
        Get BTTS accumulator summary for display.

        Returns:
            Dict: Summary of BTTS results for all selectors
        """
        try:
            summary = {
                'selectors': {},
                'total_matches': len(self.active_matches),
                'btts_success': 0,
                'btts_pending': 0,
                'btts_failed': 0,
                'accumulator_status': 'PENDING'
            }

            # Group results by selector
            selector_results = {}

            for match_id in self.active_matches:
                selector = self.match_selectors.get(match_id, 'Unknown')
                if selector not in selector_results:
                    selector_results[selector] = []

                status = self.check_btts_status(match_id)
                selector_results[selector].append(status)

            # Calculate summary for each selector
            for selector, matches in selector_results.items():
                selector_summary = {
                    'matches': matches,
                    'btts_count': len([m for m in matches if m['btts_detected']]),
                    'pending_count': len([m for m in matches if not m['btts_detected'] and m['is_live']]),
                    'failed_count': len([m for m in matches if not m['btts_detected'] and not m['is_live']]),
                    'total_matches': len(matches)
                }

                summary['selectors'][selector] = selector_summary

                # Update global counts
                summary['btts_success'] += selector_summary['btts_count']
                summary['btts_pending'] += selector_summary['pending_count']
                summary['btts_failed'] += selector_summary['failed_count']

            # Determine accumulator status
            if summary['btts_failed'] > 0:
                summary['accumulator_status'] = 'FAILED'
            elif summary['btts_pending'] > 0:
                summary['accumulator_status'] = 'PENDING'
            else:
                summary['accumulator_status'] = 'SUCCESS'

            return summary

        except Exception as e:
            self.logger.error(f"Error generating BTTS summary: {str(e)}")
            return {
                'selectors': {},
                'total_matches': 0,
                'btts_success': 0,
                'btts_pending': 0,
                'btts_failed': 0,
                'accumulator_status': 'ERROR',
                'error': str(e)
            }

    def reset_detector(self):
        """Reset BTTS detector state."""
        self.btts_results.clear()
        self.match_selectors.clear()
        self.active_matches.clear()
        self.stats = {
            'total_matches_tracked': 0,
            'btts_detected': 0,
            'btts_pending': 0,
            'last_update': None,
            'monitoring_started': None
        }
        self.logger.info("BTTS Detector reset")

    def get_detector_stats(self) -> Dict[str, Any]:
        """Get comprehensive detector statistics."""
        return {
            'detector_stats': self.stats.copy(),
            'is_monitoring': self.is_monitoring,
            'active_matches_count': len(self.active_matches),
            'btts_results_count': len(self.btts_results),
            'monitoring_thread_alive': self.monitor_thread.is_alive() if self.monitor_thread else False,
            'last_activity': self.stats['last_update'].isoformat() if self.stats['last_update'] else None
        }

# Global BTTS detector instance
btts_detector = BTTSDetector()

def main():
    """Main function demonstrating the BTTS Detector"""
    print("🎯 BTTS Detection & Highlighting System")
    print("="*50)
    print("🎯 Real-time BTTS detection for accumulator tracking")
    print("🎯 Integration with live score system")
    print("🎯 Web interface support")
    print("="*50)

    # Initialize detector
    detector = BTTSDetector()

    # Load current selections
    print("\n📋 Loading weekly selections...")
    selections = detector.load_weekly_selections()

    if selections:
        print(f"✅ Loaded {len(selections)} selections")
        for selector, match in selections.items():
            print(f"   {selector}: {match.get('home_team', 'Unknown')} vs {match.get('away_team', 'Unknown')}")
    else:
        print("❌ No selections found")

    # Add example callback
    def on_btts_detected(match_id, btts_data):
        print(f"🎯 BTTS DETECTED: {btts_data['selector']} - Match {match_id}")

    detector.add_btts_callback(on_btts_detected)

    # Start monitoring
    print("\n🔄 Starting BTTS monitoring...")
    detector.start_monitoring(check_interval=30)

    try:
        # Monitor for a short time
        print("Monitoring for 60 seconds...")
        time.sleep(60)
    except KeyboardInterrupt:
        print("\nStopping monitoring...")

    # Stop monitoring
    detector.stop_monitoring()

    # Show final statistics
    print("\n📊 Final Statistics:")
    stats = detector.get_detector_stats()
    print(f"   Total Matches Tracked: {stats['detector_stats']['total_matches_tracked']}")
    print(f"   BTTS Detected: {stats['detector_stats']['btts_detected']}")
    print(f"   BTTS Pending: {stats['detector_stats']['btts_pending']}")

    print("\n✨ BTTS Detector features demonstrated:")
    print("   • Weekly selection loading")
    print("   • Real-time BTTS detection")
    print("   • Event callback system")
    print("   • Accumulator summary generation")
    print("   • Background monitoring")
    print("   • Comprehensive statistics")

if __name__ == "__main__":
    main()