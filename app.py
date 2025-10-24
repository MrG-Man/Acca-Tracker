#!/usr/bin/env python3
"""
Football Predictions Admin Interface - Production Ready

Flask web interface for match selection using BBC scraper data.
Provides admin panel for assigning Saturday 3pm matches to selectors.

TRACKER BEHAVIOR:
- Shows ONLY games selected by selectors in the Admin panel
- Displays placeholders for unselected games during the week
- Updates dynamically as more selections are made
- Shows live scores only for selected games on match day

WEEKLY TRANSITION LOGIC:
- Sunday-Friday: Shows next Saturday's matches for selection
- Saturday (all day): Maintains current Saturday's matches for live monitoring
- Safe transition to next Saturday occurs on Sunday after games finish

API ENDPOINTS:
- /api/tracker-data: Complete tracker data with selections and placeholders
- /api/bbc-fixtures: BBC fixtures for selected games only
- /api/bbc-live-scores: Live scores for selected games only

Author: Football Predictions System
Date: 2024
Updated: 2025 - Enhanced with safer weekly transition logic and selection-only tracker
"""

import os
import sys
import json
import logging
import traceback
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler

# Import Flask and extensions
from flask import Flask, render_template, request, jsonify, redirect
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Import configuration first for logging
from config import get_config

# Import custom modules with enhanced error handling for production
try:
    from bbc_scraper import BBCSportScraper
    print("BBC scraper imported successfully")
except Exception as e:
    print(f"ERROR: Failed to import BBC scraper: {e}")
    print(f"Traceback: {traceback.format_exc()}")
    BBCSportScraper = None

try:
    from data_manager import data_manager
    print("Data manager imported successfully")

    # Log initialization status for production debugging
    if hasattr(data_manager, 'initialization_errors') and data_manager.initialization_errors:
        print(f"WARNING: DataManager initialized with errors: {data_manager.initialization_errors}")

except Exception as e:
    print(f"ERROR: Failed to import data manager: {e}")
    print(f"Traceback: {traceback.format_exc()}")
    data_manager = None

# Initialize configuration
try:
    config = get_config()
    print(f"Configuration loaded successfully. DEBUG: {config.DEBUG}, LOG_LEVEL: {config.LOG_LEVEL}")
except Exception as e:
    print(f"ERROR: Failed to load configuration: {e}")
    raise

# Create Flask app with configuration
app = Flask(__name__)
app.config.from_object(config)

# Log critical environment variables (without exposing secrets)
print(f"Environment check - HOST: {config.HOST}, PORT: {config.PORT}")
print(f"Feature flags - BBC: {config.ENABLE_BBC_SCRAPER}")

# Setup CORS
CORS(app, origins=config.CORS_ORIGINS, supports_credentials=True)

# Setup rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=[f"{config.RATE_LIMIT_PER_MINUTE} per minute"]
)


# Setup logging
def setup_logging():
    """Setup production-grade logging"""
    log_level = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)

    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(config.LOG_FILE)
    if log_dir and not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir, exist_ok=True)
            app.logger.info(f"Created logs directory: {log_dir}")
        except Exception as e:
            print(f"ERROR: Cannot create logs directory {log_dir}: {e}")
            # Fallback to current directory
            config.LOG_FILE = 'app.log'

    # Configure logging
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # File handler with rotation
    file_handler = RotatingFileHandler(
        config.LOG_FILE,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)

    # Console handler for development
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG if config.DEBUG else log_level)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(file_handler)

    if config.DEBUG:
        root_logger.addHandler(console_handler)

    # Reduce noise from external libraries
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

setup_logging()

# Validate critical components before starting
def validate_critical_components():
    """Validate that all critical components are available before starting the app."""
    errors = []

    if BBCSportScraper is None:
        errors.append("BBC scraper module failed to import")
    else:
        print("✓ BBC scraper module available")

    if data_manager is None:
        errors.append("Data manager module failed to import")
    else:
        print("✓ Data manager module available")


    if config.SECRET_KEY:
        print("✓ Flask secret key configured")
    else:
        errors.append("SECRET_KEY environment variable not set")

    # Try to create necessary directories
    try:
        os.makedirs('logs', exist_ok=True)
        os.makedirs('data', exist_ok=True)
        os.makedirs('data/selections', exist_ok=True)
        os.makedirs('data/fixtures', exist_ok=True)
        os.makedirs('data/backups', exist_ok=True)
        print("✓ Data directories created/verified")
    except Exception as e:
        errors.append(f"Cannot create data directories: {e}")

    # Clean up any corrupted cache files on startup
    if data_manager is not None:
        try:
            corrupted_count = data_manager.cleanup_corrupted_cache_files()
            if corrupted_count > 0:
                print(f"✓ Cleaned up {corrupted_count} corrupted cache files on startup")
            else:
                print("✓ No corrupted cache files found")
        except Exception as e:
            print(f"⚠ Warning: Could not clean up corrupted cache files: {e}")

    return errors


# Validate components and log results
startup_errors = validate_critical_components()
if startup_errors:
    print(f"CRITICAL: {len(startup_errors)} startup errors detected:")
    for error in startup_errors:
        print(f"  - {error}")
else:
    print("✓ All critical components validated successfully")

# Import BTTS detector for integration
try:
    from btts_detector import btts_detector  # noqa: F401
    BTTS_DETECTOR_AVAILABLE = True
    app.logger.info("BTTS detector loaded successfully")
except ImportError:
    BTTS_DETECTOR_AVAILABLE = False
    app.logger.warning("BTTS detector not available")

# BBC live scores integration active

# Panel members in assignment order
SELECTORS = [
    "Glynny", "Eamonn Bone", "Mickey D", "Rob Carney",
    "Steve H", "Danny", "Eddie Lee", "Fran Radar"
]

def get_current_prediction_week():
    """Get the current prediction week string in YYYY-MM-DD format.

    IMPROVED SAFER LOGIC:
    - Sunday-Friday: Use next Saturday's date
    - Saturday (all day): Use current Saturday's date
    - Next Sunday: Use following Saturday's date

    This eliminates the risky Saturday afternoon switch and maintains
    current Saturday's matches throughout the entire match day.
    """
    now = datetime.now()
    current_day = now.weekday()  # 0=Monday, 6=Sunday

    if current_day == 5:  # Saturday - use current Saturday all day long
        # Maintain current Saturday throughout the entire day for stable match day experience
        target_date = now.date()
    else:
        # Sunday through Friday - use next Saturday
        # Calculate days until next Saturday
        if current_day == 6:  # Sunday
            days_until_saturday = 6  # Next Saturday is 6 days away
        else:  # Monday-Friday
            days_until_saturday = 5 - current_day  # Days until Saturday

        target_date = now.date() + timedelta(days=days_until_saturday)

    week_str = target_date.strftime('%Y-%m-%d')
    print(f"[DEBUG] get_current_prediction_week() - Current day: {current_day}, Target date: {week_str}")
    return week_str

def find_next_available_fixtures_date(target_date=None, max_days_ahead=14):
    """Find the next date that has available fixtures, within a reasonable range.

    Args:
        target_date: Starting date to search from (defaults to current prediction week)
        max_days_ahead: Maximum days to search ahead

    Returns:
        str: Date string in YYYY-MM-DD format with available fixtures, or None if none found
    """
    if target_date is None:
        target_date = get_current_prediction_week()

    try:
        current_date = datetime.strptime(target_date, '%Y-%m-%d').date()
    except ValueError:
        current_date = datetime.now().date()

    # Try dates from target_date up to max_days_ahead
    for days_ahead in range(max_days_ahead + 1):
        test_date = current_date + timedelta(days=days_ahead)
        test_date_str = test_date.strftime('%Y-%m-%d')

        # Skip if date is too far in the past (more than 7 days ago)
        if test_date < datetime.now().date() - timedelta(days=7):
            continue

        # Test if this date has fixtures
        try:
            if BBCSportScraper is not None:
                scraper = BBCSportScraper(rate_limit=2.0)
                result = scraper.scrape_unified_bbc_matches(test_date_str, 'fixtures')

                if result.get('matches') and len(result['matches']) > 0:
                    # Filter for 15:00 matches
                    matches_3pm = [match for match in result['matches'] if match.get('kickoff') == '15:00']
                    if matches_3pm:
                        app.logger.info(f"Found {len(matches_3pm)} 15:00 matches for {test_date_str}")
                        return test_date_str
        except Exception as e:
            app.logger.warning(f"Error testing fixtures for {test_date_str}: {e}")
            continue

    app.logger.warning(f"No fixtures found within {max_days_ahead} days of {target_date}")
    return None


def load_selections():
    """Load existing selections for the current week using DataManager."""
    week = get_current_prediction_week()
    app.logger.info(f"[DEBUG] load_selections() - Loading selections for week: {week}")

    # Check if data_manager is available before calling methods
    if data_manager is None:
        app.logger.error("ERROR: data_manager is None - cannot load selections")
        return {"selectors": {}, "matches": [], "last_updated": None}

    # Load selections using DataManager
    app.logger.info(f"[DEBUG] load_selections() - Calling data_manager.load_weekly_selections({week})")
    selections = data_manager.load_weekly_selections(week)
    app.logger.info(f"[DEBUG] load_selections() - DataManager returned: {selections}")

    if selections is None:
        app.logger.info(f"[DEBUG] load_selections() - No selections found for week {week}")
        return {"selectors": {}, "matches": [], "last_updated": None}

    app.logger.info(f"[DEBUG] load_selections() - Found {len(selections)} selections: {list(selections.keys())}")

    # Convert DataManager format to expected format for template
    # Add assigned_at field for template compatibility
    enhanced_selections = {}
    for selector, match_data in selections.items():
        enhanced_match_data = match_data.copy()
        # Add assigned_at field if missing (for template compatibility)
        if 'assigned_at' not in enhanced_match_data:
            enhanced_match_data['assigned_at'] = datetime.now().isoformat()
        enhanced_selections[selector] = enhanced_match_data

    result = {
        "selectors": enhanced_selections,
        "matches": [],  # This will be populated from scraper data
        "last_updated": None  # Could be enhanced to track this
    }
    app.logger.info(f"[DEBUG] load_selections() - Returning: {len(enhanced_selections)} enhanced selections")
    return result

def save_selections(selections_data):
    """Save selections using DataManager."""
    week = get_current_prediction_week()
    app.logger.info(f"[DEBUG] save_selections() - Saving selections for week: {week}")
    app.logger.info(f"[DEBUG] save_selections() - Input data: {selections_data}")

    # Check if data_manager is available before calling methods
    if data_manager is None:
        app.logger.error("ERROR: data_manager is None - cannot save selections")
        return False

    # Extract just the selections part for DataManager
    selections_only = selections_data.get("selectors", {})
    app.logger.info(f"[DEBUG] save_selections() - Extracted {len(selections_only)} selections: {list(selections_only.keys())}")

    # Save using DataManager
    app.logger.info(f"[DEBUG] save_selections() - Calling data_manager.save_weekly_selections() with {len(selections_only)} selections")
    success = data_manager.save_weekly_selections(selections_only, week)
    app.logger.info(f"[DEBUG] save_selections() - DataManager save returned: {success}")

    if success:
        # Update the last_updated timestamp in the original data
        selections_data["last_updated"] = datetime.now().isoformat()
        app.logger.info(f"[DEBUG] save_selections() - Successfully saved selections for week {week}")
        return True
    else:
        app.logger.error(f"[DEBUG] save_selections() - Failed to save selections for week {week}")
        return False

@app.route('/')
def index():
    """Redirect to modern tracker interface."""
    return redirect('/modern')

@app.route('/modern')
def modern_tracker():
    """Modern single-page interface for Acca Tracker."""
    try:
        return render_template('modern-tracker.html')
    except Exception as e:
        app.logger.error(f"Error loading modern tracker interface: {str(e)}")
        return f"Error loading modern tracker interface: {str(e)}", 500

@app.route('/demo')
def demo():
    """Demo page showcasing current accumulator selections in modern format."""
    try:
        return render_template('demo.html')
    except Exception as e:
        app.logger.error(f"Error loading demo interface: {str(e)}")
        return f"Error loading demo interface: {str(e)}", 500

@app.route('/admin')
def admin():
    """Main admin interface for match selection."""
    # Ultimate fallback - if anything goes wrong, show basic info
    try:
        # Get matches from BBC scraper with enhanced error handling
        matches = []
        target_date = get_current_prediction_week()
        scraper_result = {
            "scraping_date": datetime.now().strftime("%Y-%m-%d"),
            "next_saturday": target_date,
            "matches_3pm": [],
            "all_matches": [],
            "total_3pm_matches": 0,
            "total_all_matches": 0,
            "using_alternative_date": False,
            "original_target_date": target_date
        }

        # Try to get matches from DataManager cache first
        matches = []
        if data_manager is not None:
            try:
                app.logger.info(f"[DEBUG] Admin route: Attempting to load cached fixtures for {target_date}")
                cached_fixtures = data_manager.get_bbc_fixtures(target_date)
                app.logger.info(f"[DEBUG] Admin route: DataManager returned: {len(cached_fixtures) if cached_fixtures else 0} fixtures")

                if cached_fixtures:
                    # Filter for 15:00 matches only
                    matches = [match for match in cached_fixtures if match.get('kickoff') == '15:00']
                    app.logger.info(f"[DEBUG] Admin route: Filtered to {len(matches)} 15:00 matches for {target_date}")

                    # Debug: Show all matches
                    for i, match in enumerate(matches):
                        app.logger.info(f"[DEBUG] Admin route: Match {i+1}: {match['league']} - {match['home_team']} vs {match['away_team']} at {match['kickoff']}")
                else:
                    app.logger.warning(f"[DEBUG] Admin route: No cached fixtures found for {target_date}")
            except Exception as e:
                app.logger.error(f"[DEBUG] Admin route: Error loading cached fixtures: {e}")
                import traceback
                app.logger.error(f"[DEBUG] Admin route: Traceback: {traceback.format_exc()}")

        # If no cached data, fall back to scraping
        if not matches:
            if BBCSportScraper is not None:
                try:
                    app.logger.info(f"[DEBUG] Admin route: Starting BBC scraping for {target_date}")
                    scraper = BBCSportScraper()
                    scraper_result = scraper.scrape_saturday_3pm_fixtures()
                    matches = scraper_result.get("matches_3pm", [])
                    target_date = scraper_result.get("next_saturday", target_date)
                    app.logger.info(f"[DEBUG] Admin route: Scraped {len(matches)} matches for {target_date}")

                    # Debug: Show all scraped matches
                    for i, match in enumerate(matches):
                        app.logger.info(f"[DEBUG] Admin route: Scraped match {i+1}: {match['league']} - {match['home_team']} vs {match['away_team']} at {match['kickoff']}")

                    # If no matches found, try to find an alternative date
                    if not matches:
                        app.logger.info(f"[DEBUG] Admin route: No matches found for {target_date}, searching for alternative date")
                        try:
                            alternative_date = find_next_available_fixtures_date(target_date, max_days_ahead=14)

                            if alternative_date and alternative_date != target_date:
                                app.logger.info(f"[DEBUG] Admin route: Found alternative date with matches: {alternative_date}")
                                try:
                                    # Re-scrape for the alternative date
                                    alt_scraper_result = scraper.scrape_unified_bbc_matches(alternative_date, 'fixtures')
                                    alt_matches = [match for match in alt_scraper_result.get("matches", []) if match.get('kickoff') == '15:00']

                                    if alt_matches:
                                        # Update scraper result with alternative date data
                                        scraper_result = {
                                            "scraping_date": alt_scraper_result.get("scraping_date"),
                                            "next_saturday": alternative_date,
                                            "matches_3pm": alt_matches,
                                            "all_matches": alt_scraper_result.get("matches", []),
                                            "total_3pm_matches": len(alt_matches),
                                            "total_all_matches": len(alt_scraper_result.get("matches", [])),
                                            "using_alternative_date": True,
                                            "original_target_date": target_date
                                        }
                                        matches = alt_matches
                                        target_date = alternative_date
                                        app.logger.info(f"[DEBUG] Admin route: Using alternative date {alternative_date} with {len(matches)} matches")
                                except Exception as e:
                                    app.logger.warning(f"[DEBUG] Admin route: Error scraping alternative date {alternative_date}: {e}")
                                    # Continue with empty matches list
                        except Exception as e:
                            app.logger.warning(f"[DEBUG] Admin route: Error finding alternative date: {e}")
                            # Continue with empty matches list
                except Exception as e:
                    app.logger.error(f"[DEBUG] Admin route: Error with BBC scraper: {e}")
                    # Continue with empty matches list - don't fail completely
            else:
                app.logger.warning("[DEBUG] Admin route: BBC scraper not available - showing admin interface without live data")

        # Load existing selections with enhanced error handling
        if data_manager is None:
            error_msg = "Data manager module not available - check filesystem permissions and directory creation"
            app.logger.error(error_msg)
            return f"""
            <html><head><title>Admin Interface - Error</title></head><body>
            <h1>Football Predictions Admin</h1>
            <div style="background: #fee; border: 1px solid #fcc; padding: 20px; border-radius: 5px; margin: 20px 0;">
                <h2 style="color: #c33;">⚠️ System Error</h2>
                <p><strong>Error:</strong> {error_msg}</p>
                <p><strong>Debug Info:</strong></p>
                <ul>
                    <li>BBC Scraper: {"Available" if BBCSportScraper else "Unavailable"}</li>
                    <li>Data Manager: {"Available" if data_manager else "Unavailable"}</li>
                    <li>Current Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</li>
                    <li>Target Date: {get_current_prediction_week()}</li>
                </ul>
            </div>
            <div style="margin: 20px 0;">
                <h3>🔧 Troubleshooting:</h3>
                <ul>
                    <li>Check filesystem permissions in production environment</li>
                    <li>Verify all required directories can be created</li>
                    <li>Check Railway deployment logs for detailed errors</li>
                    <li><a href="/health">Check Health Status</a></li>
                </ul>
            </div>
            </body></html>
            """, 500

        app.logger.info(f"[DEBUG] Admin route: Loading selections for week {target_date}")
        selections_data = load_selections()
        app.logger.info(f"[DEBUG] Admin route: Loaded {len(selections_data.get('selectors', {}))} selections")

        # Get available selectors (those not yet assigned)
        assigned_selectors = set(selections_data.get("selectors", {}).keys())

        # Prepare match data for template
        selections = selections_data.get("selectors", {})

        # Calculate progress percentage with safety check
        try:
            if len(SELECTORS) > 0 and isinstance(len(selections), int):
                progress_percentage = max(0, min(100, int((len(selections) / len(SELECTORS)) * 100)))
            else:
                progress_percentage = 0
        except (ZeroDivisionError, TypeError, ValueError):
            progress_percentage = 0

        # Ensure it's always an integer
        progress_percentage = int(progress_percentage) if progress_percentage is not None else 0

        # Add diagnostic information for debugging
        diagnostic_info = {
            "total_matches_found": len(matches),
            "target_date": target_date,
            "original_target_date": scraper_result.get("original_target_date", target_date),
            "scraping_date": scraper_result.get("scraping_date"),
            "bbc_scraper_available": BBCSportScraper is not None,
            "data_manager_available": data_manager is not None,
            "selections_count": len(selections),
            "using_alternative_date": scraper_result.get("using_alternative_date", False)
        }

        try:
            return render_template('admin.html',
                                   matches=matches,
                                   all_selectors_for_dropdown=SELECTORS,
                                   selections=selections,
                                   all_selectors=SELECTORS,
                                   scraping_date=scraper_result.get("scraping_date"),
                                   next_saturday=target_date,
                                   progress_percentage=progress_percentage,
                                   diagnostic_info=diagnostic_info)
        except Exception as template_error:
            app.logger.error(f"Template rendering error: {template_error}")
            # Fallback to basic error page if template fails
            return f"""
            <html><head><title>Admin Interface</title></head><body>
            <h1>Football Predictions Admin</h1>
            <p><strong>Template Error:</strong> {str(template_error)}</p>
            <p><strong>Debug Info:</strong> {diagnostic_info}</p>
            <p><a href="/health">Check Health Status</a></p>
            </body></html>
            """, 500

    except Exception as e:
        app.logger.error(f"Error loading admin interface: {str(e)}")
        # Return a basic HTML response if template rendering fails
        return f"""
        <html>
        <head><title>Admin Interface - Error</title></head>
        <body style="font-family: Arial, sans-serif; margin: 40px;">
        <h1>Football Predictions Admin</h1>
        <div style="background: #fee; border: 1px solid #fcc; padding: 20px; border-radius: 5px; margin: 20px 0;">
            <h2 style="color: #c33;">⚠️ Application Error</h2>
            <p><strong>Error:</strong> {str(e)}</p>
            <p><strong>Time:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            <p><strong>Target Date:</strong> {get_current_prediction_week()}</p>
            <p><strong>BBC Scraper:</strong> {"Available" if BBCSportScraper else "Unavailable"}</p>
            <p><strong>Data Manager:</strong> {"Available" if data_manager else "Unavailable"}</p>
        </div>
        <div style="margin: 20px 0;">
            <h3>🔧 Troubleshooting:</h3>
            <ul>
                <li><a href="/health">Check Health Status</a></li>
                <li><a href="/">Return to Home</a></li>
                <li>Check application logs for detailed error information</li>
            </ul>
        </div>
        </body>
        </html>
        """, 500

@app.route('/api/assign', methods=['POST'])
def assign_match():
    """API endpoint for assigning a match to a selector with enhanced error handling and debugging."""
    # Initialize variables for error handling
    match_id = None
    selector = None
    timestamp = datetime.now().isoformat()
    attempt = 1

    try:
        print("[DEBUG] /api/assign endpoint called")
        data = request.get_json()
        print(f"[DEBUG] /api/assign - Request data: {data}")

        match_id = data.get('match_id')
        selector = data.get('selector')
        timestamp = data.get('timestamp', timestamp)
        attempt = data.get('attempt', attempt)

        print(f"[DEBUG] /api/assign - Extracted match_id: {match_id}, selector: {selector}, attempt: {attempt}")

        # Enhanced validation with detailed error messages
        if not match_id or not selector:
            error_msg = "Missing required parameters"
            print(f"[DEBUG] /api/assign - {error_msg}")
            return jsonify({
                "success": False,
                "error": error_msg,
                "debug_info": {
                    "received_match_id": match_id,
                    "received_selector": selector,
                    "timestamp": timestamp,
                    "attempt": attempt
                }
            }), 400

        # Validate selector against allowed list
        if selector not in SELECTORS:
            error_msg = f"Invalid selector: {selector}"
            print(f"[DEBUG] /api/assign - {error_msg}")
            return jsonify({
                "success": False,
                "error": error_msg,
                "debug_info": {
                    "valid_selectors": SELECTORS,
                    "received_selector": selector,
                    "timestamp": timestamp,
                    "attempt": attempt
                }
            }), 400

        # Load current selections
        print("[DEBUG] /api/assign - Loading current selections")
        selections_data = load_selections()
        print(f"[DEBUG] /api/assign - Current selections loaded: {len(selections_data.get('selectors', {}))} selectors")

        # Check if selector already has a match - allow reassignment
        if selector in selections_data.get("selectors", {}):
            app.logger.info(f"[API DEBUG] Selector {selector} already has assignment, removing existing")
            # Remove the existing assignment to allow reassignment
            del selections_data["selectors"][selector]

        # Check if match is already assigned
        for sel, match in selections_data.get("selectors", {}).items():
            if match.get("id") == match_id:
                app.logger.error(f"[API DEBUG] Match {match_id} already assigned to {sel}")
                return jsonify({"success": False, "error": "Match already assigned to another selector"}), 400

        # Find the match details - try to use cached data first
        match_details = None
        app.logger.info(f"[API DEBUG] Looking for match details for match_id: {match_id}")

        # First, try to get cached match data from DataManager
        try:
            week = get_current_prediction_week()
            app.logger.info(f"[API DEBUG] Current prediction week: {week}")

            # Check if data_manager is available before calling methods
            if data_manager is None:
                app.logger.error("ERROR: data_manager is None - cannot get cached fixtures")
            else:
                cached_fixtures = data_manager.get_bbc_fixtures(week)
                app.logger.info(f"[API DEBUG] Cached fixtures loaded: {len(cached_fixtures) if cached_fixtures else 0} matches")
                if cached_fixtures:
                    for match in cached_fixtures:
                        current_id = f"{match['league']}_{match['home_team']}_{match['away_team']}"
                        app.logger.debug(f"[API DEBUG] Checking match: {current_id}")
                        if current_id == match_id:
                            match_details = match
                            app.logger.info(f"[API DEBUG] Match found in cache: {match_details}")
                            break
        except Exception as e:
            app.logger.error(f"[API DEBUG] Error loading cached fixtures: {e}")

        # If no cached data or match not found, try scraping (but handle errors gracefully)
        if not match_details:
            app.logger.info("[API DEBUG] Match not found in cache, trying scraper")
            try:
                if BBCSportScraper is None:
                    app.logger.error("[API DEBUG] BBC scraper not available")
                    return jsonify({"success": False, "error": "BBC scraper not available"}), 500

                scraper = BBCSportScraper()
                scraper_result = scraper.scrape_saturday_3pm_fixtures()
                matches = scraper_result.get("matches_3pm", [])
                app.logger.info(f"[API DEBUG] Scraped {len(matches)} matches")

                for match in matches:
                    current_id = f"{match['league']}_{match['home_team']}_{match['away_team']}"
                    app.logger.debug(f"[API DEBUG] Checking scraped match: {current_id}")
                    if current_id == match_id:
                        match_details = match
                        app.logger.info(f"[API DEBUG] Match found in scraped data: {match_details}")
                        break
            except Exception as e:
                app.logger.error(f"[API DEBUG] Error scraping fixtures: {e}")
                return jsonify({"success": False, "error": "Unable to retrieve match data. Please try again later."}), 500

        if not match_details:
            app.logger.error(f"[API DEBUG] Match {match_id} not found in any data source")
            return jsonify({"success": False, "error": "Match not found"}), 404

        # Assign the match - update selections_data for API compatibility
        if "selectors" not in selections_data:
            selections_data["selectors"] = {}

        new_assignment = {
            "home_team": match_details["home_team"],
            "away_team": match_details["away_team"],
            "prediction": "TBD",  # Required by DataManager validation
            "confidence": 5       # Required by DataManager validation
        }

        selections_data["selectors"][selector] = new_assignment
        app.logger.info(f"[API DEBUG] Assignment prepared: {selector} -> {new_assignment}")

        # Save selections using DataManager
        app.logger.info("[API DEBUG] Calling save_selections()")
        save_result = save_selections(selections_data)
        app.logger.info(f"[API DEBUG] save_selections() returned: {save_result}")

        if save_result:
            app.logger.info(f"[API DEBUG] Assignment successful for {selector}")
            return jsonify({
                "success": True,
                "message": f"Match assigned to {selector}",
                "debug_info": {
                    "selector": selector,
                    "match_id": match_id,
                    "timestamp": timestamp,
                    "attempt": attempt,
                    "save_result": save_result
                }
            })
        else:
            app.logger.error(f"[API DEBUG] Failed to save selections for {selector}")
            return jsonify({
                "success": False,
                "error": "Failed to save selections",
                "debug_info": {
                    "selector": selector,
                    "match_id": match_id,
                    "timestamp": timestamp,
                    "attempt": attempt,
                    "data_manager_available": data_manager is not None
                }
            }), 500

    except Exception as e:
        app.logger.error(f"[API DEBUG] Exception in assign_match: {str(e)}")
        import traceback
        app.logger.error(f"[API DEBUG] Traceback: {traceback.format_exc()}")

        return jsonify({
            "success": False,
            "error": "Internal server error",
            "debug_info": {
                "exception_type": type(e).__name__,
                "exception_message": str(e),
                "timestamp": timestamp,
                "attempt": attempt,
                "traceback_available": True
            }
        }), 500

@app.route('/api/unassign', methods=['POST'])
def unassign_match():
    """API endpoint for unassigning a match from a selector."""
    try:
        data = request.get_json()
        selector = data.get('selector')

        if not selector:
            return jsonify({"success": False, "error": "Missing selector"}), 400

        # Load current selections
        selections_data = load_selections()

        if selector not in selections_data.get("selectors", {}):
            return jsonify({"success": False, "error": f"Selector {selector} has no assigned match"}), 404

        # Remove the assignment
        del selections_data["selectors"][selector]

        # Save selections using DataManager
        if save_selections(selections_data):
            return jsonify({"success": True, "message": f"Match unassigned from {selector}"})
        else:
            return jsonify({"success": False, "error": "Failed to save selections"}), 500

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/selections')
def get_selections():
    """API endpoint to get current selections with enhanced data structure."""
    try:
        selections_data = load_selections()

        # Ensure consistent data structure
        enhanced_data = {
            "selectors": {},
            "matches": [],
            "last_updated": datetime.now().isoformat(),
            "statistics": {
                "total_selectors": len(SELECTORS),
                "selected_count": len(selections_data.get("selectors", {})),
                "completion_percentage": 0
            }
        }

        # Process selections with null safety
        if selections_data and "selectors" in selections_data:
            selected_count = 0
            for selector, match_data in selections_data["selectors"].items():
                if match_data and isinstance(match_data, dict):
                    # Ensure all required fields are present with defaults
                    enhanced_match = {
                        "home_team": match_data.get("home_team"),
                        "away_team": match_data.get("away_team"),
                        "prediction": match_data.get("prediction", "TBD"),
                        "confidence": match_data.get("confidence", 5),
                        "assigned_at": match_data.get("assigned_at", datetime.now().isoformat()),
                        "league": match_data.get("league", "Unknown"),
                        "status": match_data.get("status", "not_started")
                    }
                    enhanced_data["selectors"][selector] = enhanced_match
                    selected_count += 1

            # Add completion percentage
            enhanced_data["statistics"]["completion_percentage"] = max(0, min(100, int((selected_count / len(SELECTORS)) * 100))) if len(SELECTORS) > 0 else 0

        return jsonify(enhanced_data)
    except Exception as e:
        # Enhanced error handling with fallback data structure
        fallback_data = {
            "selectors": {},
            "matches": [],
            "last_updated": datetime.now().isoformat(),
            "statistics": {
                "total_selectors": len(SELECTORS),
                "selected_count": 0,
                "completion_percentage": 0,
                "error": True,
                "error_message": str(e)
            },
            "fallback": True
        }
        return jsonify(fallback_data), 500

@app.route('/api/selections/<week>')
def get_selections_for_week(week):
    """API endpoint to get selections for a specific week."""
    try:
        # Validate week format (YYYY-MM-DD)
        try:
            datetime.strptime(week, '%Y-%m-%d')
        except ValueError:
            return jsonify({"error": "Invalid week format. Use YYYY-MM-DD"}), 400

        # Check if data_manager is available before calling methods
        if data_manager is None:
            return jsonify({"error": "Data manager not available"}), 500

        # Load selections for the specific week
        selections = data_manager.load_weekly_selections(week)

        if selections is None:
            return jsonify({
                "selectors": {},
                "matches": [],
                "last_updated": None,
                "message": f"No selections found for week {week}"
            }), 404

        # Convert DataManager format to expected format for API
        enhanced_selections = {}
        for selector, match_data in selections.items():
            enhanced_match_data = match_data.copy()
            # Add assigned_at field if missing (for API compatibility)
            if 'assigned_at' not in enhanced_match_data:
                enhanced_match_data['assigned_at'] = datetime.now().isoformat()
            enhanced_selections[selector] = enhanced_match_data

        result = {
            "selectors": enhanced_selections,
            "matches": [],  # This will be populated from scraper data if needed
            "last_updated": None,  # Could be enhanced to track this
            "week": week
        }

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": f"Error getting selections for week {week}: {str(e)}"}), 500

@app.route('/api/override', methods=['POST'])
def override_selections():
    """API endpoint for overriding with less than 8 selections."""
    try:
        data = request.get_json()
        confirm_message = data.get('confirm_message', '')

        # Require specific confirmation message
        required_confirmation = "I confirm that I want to proceed with fewer than 8 selections"
        if confirm_message != required_confirmation:
            return jsonify({"success": False, "error": "Invalid confirmation message"}), 400

        # Load current selections
        selections_data = load_selections()

        # Add override flag
        selections_data["override_confirmed"] = True
        selections_data["override_confirmed_at"] = datetime.now().isoformat()
        selections_data["override_confirmed_by"] = "admin"  # Could be enhanced with user authentication

        # Save selections using DataManager
        if save_selections(selections_data):
            return jsonify({"success": True, "message": "Override confirmed"})
        else:
            return jsonify({"success": False, "error": "Failed to save selections"}), 500

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/report-error', methods=['POST'])
def report_error():
    """API endpoint for client-side error reporting and debugging."""
    try:
        error_data = request.get_json()

        # Log the error report for debugging
        app.logger.error(f"Client-side error report received: {error_data}")

        # Store error report for analysis
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        error_filename = f"client_error_{timestamp}.json"

        # Save to logs directory for analysis
        error_filepath = os.path.join('logs', error_filename)
        with open(error_filepath, 'w', encoding='utf-8') as f:
            json.dump(error_data, f, indent=2, ensure_ascii=False)

        return jsonify({
            "success": True,
            "message": "Error report received and logged",
            "error_id": timestamp
        })

    except Exception as e:
        app.logger.error(f"Failed to process error report: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Failed to process error report"
        }), 500

# ===== BTTS TRACKER ROUTES =====

@app.route('/btts-tracker')
def btts_tracker():
    """Main BTTS accumulator tracker interface."""
    try:
        # Load current week's selections for context
        week = get_current_prediction_week()

        # Check if data_manager is available before calling methods
        if data_manager is None:
            print("ERROR: data_manager is None - cannot load selections for BTTS tracker")
            return render_template('tracker.html')

        selections = data_manager.load_weekly_selections(week)

        return render_template('tracker.html')

    except Exception as e:
        return f"Error loading BTTS tracker: {str(e)}", 500


@app.route('/mobile-test')
def mobile_test():
    """Mobile device testing interface for testing responsive design across multiple devices."""
    try:
        app.logger.info("Mobile test route accessed - rendering mobile_test.html")
        return render_template('mobile_test.html')
    except Exception as e:
        app.logger.error(f"Error loading mobile test interface: {str(e)}")
        return f"Error loading mobile test interface: {str(e)}", 500


def get_team_color(team_name):
    """Get a color for the team logo based on team name."""
    colors = [
        '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7',
        '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9',
        '#F8C471', '#82E0AA', '#F1948A', '#85C1E9', '#D7BDE2'
    ]
    # Simple hash based on team name
    hash_value = sum(ord(c) for c in team_name) % len(colors)
    return colors[hash_value]


@app.route('/mobile-demo')
def mobile_demo():
    """Mobile demo page showcasing current accumulator selections in mobile format."""
    try:
        # Load current selections
        selections_data = load_selections()
        selections = selections_data.get('selectors', {})

        # Create demo matches for all 8 selectors
        demo_matches = []
        for selector in SELECTORS:
            if selector in selections:
                # Use real match data for selected matches
                match_data = selections[selector]
                # Simulate realistic match statuses and scores
                import random
                statuses = ['FT', 'HT', '82\'', '65\'', '45\'', 'Live']
                status = random.choice(statuses)
                if status == 'FT':
                    home_score = random.randint(0, 4)
                    away_score = random.randint(0, 4)
                    btts = home_score > 0 and away_score > 0
                elif status in ['HT', '45\'']:
                    home_score = random.randint(0, 2)
                    away_score = random.randint(0, 2)
                    btts = home_score > 0 and away_score > 0
                else:
                    home_score = random.randint(0, 3)
                    away_score = random.randint(0, 3)
                    btts = home_score > 0 and away_score > 0

                demo_matches.append({
                    'selector': selector,
                    'home_team': match_data.get('home_team'),
                    'away_team': match_data.get('away_team'),
                    'home_score': home_score,
                    'away_score': away_score,
                    'status': status,
                    'btts': btts,
                    'league': match_data.get('league', 'Premier League'),
                    'home_color': get_team_color(match_data.get('home_team')),
                    'away_color': get_team_color(match_data.get('away_team'))
                })
            else:
                # Create placeholder for unselected selectors
                demo_matches.append({
                    'selector': selector,
                    'home_team': None,
                    'away_team': None,
                    'home_score': 0,
                    'away_score': 0,
                    'status': '—',
                    'btts': False,
                    'league': None,
                    'home_color': '#666666',
                    'away_color': '#666666'
                })

        return render_template('mobile-demo.html', matches=demo_matches, get_team_color=get_team_color)
    except Exception as e:
        app.logger.error(f"Error loading mobile demo interface: {str(e)}")
        return f"Error loading mobile demo interface: {str(e)}", 500



@app.route('/api/btts-status')
def get_btts_status():
    """API endpoint to get current BTTS status for all matches."""
    try:
        # Load current week's selections
        week = get_current_prediction_week()
        print(f"[DEBUG] /api/btts-status - Loading BTTS status for week: {week}")

        # Get target date for live scores
        target_date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))

        # Check if data_manager is available before calling methods
        if data_manager is None:
            print("ERROR: data_manager is None - cannot load selections for BTTS status")
            return jsonify({
                "status": "ERROR",
                "message": "Data manager not available",
                "matches": {},
                "statistics": {
                    "total_matches_tracked": 0,
                    "btts_detected": 0,
                    "btts_pending": 0,
                    "last_update": datetime.now().isoformat()
                },
                "last_updated": datetime.now().isoformat()
            })

        print(f"[DEBUG] /api/btts-status - Calling data_manager.load_weekly_selections({week})")
        selections = data_manager.load_weekly_selections(week)
        print(f"[DEBUG] /api/btts-status - DataManager returned: {len(selections) if selections else 0} selections")

        if not selections:
            print(f"[DEBUG] /api/btts-status - No selections found for week {week}")
            # Generate placeholders for all selectors
            placeholder_matches = {}
            for selector in SELECTORS:
                placeholder_matches[selector] = {
                    "home_team": None,
                    "away_team": None,
                    "home_score": 0,
                    "away_score": 0,
                    "status": "no_selection",
                    "league": None,
                    "btts_detected": False,
                    "placeholder": True,
                    "placeholder_text": "Awaiting Match Assignment",
                    "last_updated": datetime.now().isoformat()
                }
            return jsonify({
                "status": "NO_SELECTIONS",
                "message": "No selections found for current week",
                "matches": placeholder_matches,
                "statistics": {
                    "total_matches_tracked": len(SELECTORS),
                    "btts_detected": 0,
                    "btts_pending": len(SELECTORS),
                    "last_update": datetime.now().isoformat()
                },
                "last_updated": datetime.now().isoformat()
            })

        # Populate matches_data with selections first
        matches_data = {}
        for selector, match_data in selections.items():
            matches_data[selector] = {
                "home_team": match_data.get('home_team'),
                "away_team": match_data.get('away_team'),
                "home_score": 0,
                "away_score": 0,
                "status": "not_started",
                "league": "Unknown",
                "btts_detected": False,
                "last_updated": datetime.now().isoformat()
            }

        # Add placeholders for unselected selectors
        for selector in SELECTORS:
            if selector not in matches_data:
                matches_data[selector] = {
                    "home_team": None,
                    "away_team": None,
                    "home_score": 0,
                    "away_score": 0,
                    "status": "no_selection",
                    "league": None,
                    "btts_detected": False,
                    "placeholder": True,
                    "placeholder_text": "Awaiting Match Assignment",
                    "last_updated": datetime.now().isoformat()
                }

        # Get live scores from BBC for BTTS detection
        try:
            if BBCSportScraper is not None:
                scraper = BBCSportScraper()
                live_result = scraper.scrape_live_scores(target_date)
                all_live_matches = live_result.get("live_matches", [])
                app.logger.info(f"[DEBUG] /api/btts-status - Scraped {len(all_live_matches)} live matches from BBC")
            else:
                all_live_matches = []
                app.logger.warning("[DEBUG] /api/btts-status - BBC scraper not available")
        except Exception as e:
            app.logger.error(f"[DEBUG] /api/btts-status - Error scraping BBC live scores: {e}")
            all_live_matches = []

        # Match selections with BBC live data
        for selector, match_data in selections.items():
            home_team = match_data.get('home_team')
            away_team = match_data.get('away_team')

            # Find matching live data
            live_match = None
            for bbc_match in all_live_matches:
                if (bbc_match.get('home_team') == home_team and
                    bbc_match.get('away_team') == away_team):
                    live_match = bbc_match
                    break

            if live_match:
                # Use BBC live data
                home_score = live_match.get('home_score', 0)
                away_score = live_match.get('away_score', 0)
                status = live_match.get('status', 'not_started')
                match_time = live_match.get('match_time', '0\'')
                league = live_match.get('league', 'Unknown')
                btts_detected = home_score > 0 and away_score > 0

                matches_data[selector] = {
                    "home_team": home_team,
                    "away_team": away_team,
                    "home_score": home_score,
                    "away_score": away_score,
                    "status": status,
                    "match_time": match_time,
                    "league": league,
                    "btts_detected": btts_detected,
                    "last_updated": datetime.now().isoformat()
                }
                app.logger.debug(f"[DEBUG] /api/btts-status - Updated {selector}: {home_team} vs {away_team} - {home_score}-{away_score} ({status})")
            else:
                # No live data found - set to not_started
                matches_data[selector] = {
                    "home_team": match_data.get('home_team'),
                    "away_team": match_data.get('away_team'),
                    "home_score": 0,
                    "away_score": 0,
                    "status": "not_started",
                    "league": "Unknown",
                    "btts_detected": False,
                    "last_updated": datetime.now().isoformat()
                }

        # Calculate statistics for all matches
        btts_detected = 0
        btts_pending = 0
        for selector, match_data in matches_data.items():
            if match_data.get('btts_detected'):
                btts_detected += 1
            elif match_data.get('status') in ['not_started', 'live', 'no_selection']:
                btts_pending += 1

        # Sofascore integration removed - no API stats
        api_stats = {}

        # Calculate completion percentage
        total_selectors = len(SELECTORS)
        selected_matches = len([m for m in matches_data.values() if m.get('status') != 'no_selection'])
        completion_percentage = max(0, min(100, int((selected_matches / total_selectors) * 100))) if total_selectors > 0 else 0

        return jsonify({
            "status": "ACTIVE" if matches_data else "NO_LIVE_DATA",
            "message": f"Tracking {len(matches_data)} matches with BBC live scores",
            "matches": matches_data,
            "statistics": {
                "total_matches_tracked": len(matches_data),
                "btts_detected": btts_detected,
                "btts_pending": btts_pending,
                "btts_failed": len(matches_data) - btts_detected - btts_pending,
                "last_update": datetime.now().isoformat(),
                "api_calls_used": api_stats.get('api_calls_used', 0),
                "api_calls_target": api_stats.get('api_calls_target', '12-16'),
                "completion_percentage": completion_percentage
            },
            "last_updated": datetime.now().isoformat(),
        })

    except Exception as e:
        # Enhanced error handling with fallback data structure
        fallback_matches = {}
        for selector in SELECTORS:
            fallback_matches[selector] = {
                "home_team": None,
                "away_team": None,
                "home_score": 0,
                "away_score": 0,
                "status": "error",
                "league": None,
                "btts_detected": False,
                "error": True,
                "error_message": "Unable to load live data",
                "last_updated": datetime.now().isoformat()
            }

        return jsonify({
            "status": "ERROR",
            "message": "Unable to retrieve live BTTS status - showing fallback data",
            "matches": fallback_matches,
            "statistics": {
                "total_matches_tracked": len(SELECTORS),
                "btts_detected": 0,
                "btts_pending": 0,
                "btts_failed": 0,
                "completion_percentage": 0,
                "error": True,
                "error_message": str(e),
                "last_update": datetime.now().isoformat()
            },
            "last_updated": datetime.now().isoformat(),
            "fallback": True
        }), 500


@app.route('/api/btts-summary')
def get_btts_summary():
    """API endpoint to get BTTS accumulator summary."""
    try:
        # Load current week's selections
        week = get_current_prediction_week()

        # Get target date for live scores
        target_date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))

        # Check if data_manager is available before calling methods
        if data_manager is None:
            print("ERROR: data_manager is None - cannot load selections for BTTS summary")
            return jsonify({
                "status": "ERROR",
                "message": "Data manager not available",
                "selectors": {},
                "total_matches": 0,
                "btts_success": 0,
                "btts_pending": 0,
                "btts_failed": 0,
                "accumulator_status": "ERROR"
            })

        selections = data_manager.load_weekly_selections(week)

        if not selections or len(selections) == 0:
            return jsonify({
                "status": "NO_SELECTIONS",
                "message": "No selections found for current week",
                "selectors": {},
                "total_matches": 0,
                "btts_success": 0,
                "btts_pending": 0,
                "btts_failed": 0,
                "accumulator_status": "NO_DATA"
            })

        # Get live scores from BBC for BTTS detection
        try:
            if BBCSportScraper is not None:
                scraper = BBCSportScraper()
                live_result = scraper.scrape_live_scores(target_date)
                all_live_matches = live_result.get("live_matches", [])
                app.logger.info(f"[DEBUG] /api/btts-summary - Scraped {len(all_live_matches)} live matches from BBC")
            else:
                all_live_matches = []
                app.logger.warning("[DEBUG] /api/btts-summary - BBC scraper not available")
        except Exception as e:
            app.logger.error(f"[DEBUG] /api/btts-summary - Error scraping BBC live scores: {e}")
            all_live_matches = []

        # Calculate summary statistics using BBC data
        selectors_data = {}
        btts_success = 0
        btts_pending = 0
        btts_failed = 0

        if selections:
            for selector, match_data in selections.items():
                home_team = match_data.get('home_team')
                away_team = match_data.get('away_team')

                # Find corresponding match in BBC live data
                match_info = None
                for bbc_match in all_live_matches:
                    if (bbc_match.get('home_team') == home_team and
                        bbc_match.get('away_team') == away_team):
                        match_info = bbc_match
                        break

                if match_info:
                    home_score = match_info.get('home_score', 0)
                    away_score = match_info.get('away_score', 0)
                    status = match_info.get('status', 'not_started')
                    is_btts = home_score > 0 and away_score > 0

                    selectors_data[selector] = {
                        "home_team": home_team,
                        "away_team": away_team,
                        "btts_detected": is_btts,
                        "status": status,
                        "home_score": home_score,
                        "away_score": away_score
                    }

                    if is_btts:
                        btts_success += 1
                    elif status == 'finished':
                        btts_failed += 1
                    else:
                        btts_pending += 1
                else:
                    # Match not found in live data yet
                    selectors_data[selector] = {
                        "home_team": home_team,
                        "away_team": away_team,
                        "btts_detected": False,
                        "status": "not_started",
                        "home_score": 0,
                        "away_score": 0
                    }
                    btts_pending += 1

        # Determine accumulator status
        total_selections = len(selections) if selections else 0
        if btts_failed > 0:
            accumulator_status = "FAILED"
        elif btts_success == total_selections:
            accumulator_status = "COMPLETE_SUCCESS"
        elif btts_success > 0:
            accumulator_status = "PARTIAL_SUCCESS"
        elif btts_pending > 0:
            accumulator_status = "IN_PROGRESS"
        else:
            accumulator_status = "NOT_STARTED"

        return jsonify({
            "status": "ACTIVE",
            "message": f"BTTS accumulator tracking active for {total_selections} selections with BBC live scores",
            "selectors": selectors_data,
            "total_matches": total_selections,
            "btts_success": btts_success,
            "btts_pending": btts_pending,
            "btts_failed": btts_failed,
            "accumulator_status": accumulator_status,
            "last_updated": datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({
            "error": f"Error getting BTTS summary: {str(e)}",
            "status": "ERROR",
            "accumulator_status": "ERROR"
        }), 500


# ===== ENHANCED BBC SCRAPER API ENDPOINTS =====

@app.route('/api/bbc-fixtures')
def get_bbc_fixtures():
    """API endpoint to get BBC fixtures for next Saturday - ONLY selected games."""
    try:
        # Get current week's selections
        week = get_current_prediction_week()

        # Check if data_manager is available before calling methods
        if data_manager is None:
            print("ERROR: data_manager is None - cannot load selections for BBC fixtures")
            return jsonify({
                "success": False,
                "error": "Data manager not available",
                "last_updated": datetime.now().isoformat()
            }), 500

        selections = data_manager.load_weekly_selections(week) or {}

        if not selections:
            # No selections yet - return empty with placeholder structure
            return jsonify({
                "success": True,
                "scraping_date": datetime.now().strftime("%Y-%m-%d"),
                "next_saturday": week,
                "matches": [],
                "selected_matches": [],
                "total_matches": 0,
                "selected_count": 0,
                "placeholder_count": len(SELECTORS),
                "last_updated": datetime.now().isoformat()
            })

        # Try to get matches from DataManager cache first
        cached_fixtures = None
        if data_manager is not None:
            try:
                app.logger.info(f"Attempting to load cached fixtures for {week}")
                cached_fixtures = data_manager.get_bbc_fixtures(week)
                app.logger.info(f"DataManager returned: {len(cached_fixtures) if cached_fixtures else 0} fixtures")

                if cached_fixtures:
                    # Filter for 15:00 matches only
                    matches_3pm = [match for match in cached_fixtures if match.get('kickoff') == '15:00']
                    app.logger.info(f"Filtered to {len(matches_3pm)} 15:00 matches for {week}")
                else:
                    app.logger.warning(f"No cached fixtures found for {week}")
            except Exception as e:
                app.logger.error(f"Error loading cached fixtures: {e}")
                import traceback
                app.logger.error(f"Traceback: {traceback.format_exc()}")

        # If no cached data, fall back to scraping
        if not cached_fixtures:
            if BBCSportScraper is not None:
                try:
                    scraper = BBCSportScraper()
                    scraper_result = scraper.scrape_saturday_3pm_fixtures()
                    all_bbc_matches = scraper_result.get("matches_3pm", [])
                    week = scraper_result.get("next_saturday", week)
                    app.logger.info(f"Scraped {len(all_bbc_matches)} matches for {week}")

                    # Cache successful scraping results
                    if all_bbc_matches:
                        try:
                            # Convert scraper matches to cache format if needed
                            cache_data = []
                            for match in all_bbc_matches:
                                cache_match = match.copy()
                                # Ensure required fields for caching
                                if 'id' not in cache_match:
                                    cache_match['id'] = f"{match.get('league', 'Unknown')}_{match.get('home_team', '')}_{match.get('away_team', '')}"
                                cache_data.append(cache_match)

                            # Cache the scraped data
                            if data_manager is not None:
                                data_manager.cache_bbc_fixtures(cache_data, week)
                                app.logger.info(f"Cached {len(cache_data)} scraped fixtures for {week}")
                        except Exception as cache_error:
                            app.logger.warning(f"Failed to cache scraped fixtures: {cache_error}")

                    # Filter to only selected matches
                    selected_matches = []

                    for selector, match_data in selections.items():
                        home_team = match_data.get('home_team')
                        away_team = match_data.get('away_team')

                        # Find matching BBC data for this selection
                        for bbc_match in all_bbc_matches:
                            if (bbc_match.get('home_team') == home_team and
                                bbc_match.get('away_team') == away_team):
                                # Add selector info to BBC match data
                                enhanced_match = bbc_match.copy()
                                enhanced_match['selector'] = selector
                                enhanced_match['prediction'] = match_data.get('prediction', 'TBD')
                                enhanced_match['confidence'] = match_data.get('confidence', 5)
                                selected_matches.append(enhanced_match)
                                break

                    return jsonify({
                        "success": True,
                        "scraping_date": scraper_result.get("scraping_date"),
                        "next_saturday": scraper_result.get("next_saturday"),
                        "matches": selected_matches,  # Only selected matches
                        "selected_matches": selected_matches,
                        "total_matches": len(selected_matches),
                        "selected_count": len(selected_matches),
                        "placeholder_count": len(SELECTORS) - len(selected_matches),
                        "last_updated": datetime.now().isoformat()
                    })
                except Exception as e:
                    app.logger.error(f"Error with BBC scraper: {e}")
                    # Continue with empty matches list - don't fail completely
            else:
                app.logger.warning("BBC scraper not available - returning empty fixtures")

        # Use cached data if available
        if cached_fixtures:
            # Filter for 15:00 matches only
            matches_3pm = [match for match in cached_fixtures if match.get('kickoff') == '15:00']

            # Filter to only selected matches
            selected_matches = []

            for selector, match_data in selections.items():
                home_team = match_data.get('home_team')
                away_team = match_data.get('away_team')

                # Find matching BBC data for this selection
                for bbc_match in matches_3pm:
                    if (bbc_match.get('home_team') == home_team and
                        bbc_match.get('away_team') == away_team):
                        # Add selector info to BBC match data
                        enhanced_match = bbc_match.copy()
                        enhanced_match['selector'] = selector
                        enhanced_match['prediction'] = match_data.get('prediction', 'TBD')
                        enhanced_match['confidence'] = match_data.get('confidence', 5)
                        selected_matches.append(enhanced_match)
                        break

            return jsonify({
                "success": True,
                "scraping_date": datetime.now().strftime("%Y-%m-%d"),
                "next_saturday": week,
                "matches": selected_matches,  # Only selected matches
                "selected_matches": selected_matches,
                "total_matches": len(selected_matches),
                "selected_count": len(selected_matches),
                "placeholder_count": len(SELECTORS) - len(selected_matches),
                "last_updated": datetime.now().isoformat(),
                "cache_used": True
            })

        # Fallback: return empty structure if no data available
        return jsonify({
            "success": True,
            "scraping_date": datetime.now().strftime("%Y-%m-%d"),
            "next_saturday": week,
            "matches": [],
            "selected_matches": [],
            "total_matches": 0,
            "selected_count": 0,
            "placeholder_count": len(SELECTORS),
            "last_updated": datetime.now().isoformat()
        })

    except Exception as e:
        # Enhanced error handling with fallback data structure
        fallback_matches = []
        for selector in SELECTORS:
            fallback_matches.append({
                "selector": selector,
                "home_team": None,
                "away_team": None,
                "league": None,
                "kickoff": "15:00",
                "prediction": "TBD",
                "confidence": 5,
                "is_selected": False,
                "placeholder_text": "Error loading fixtures",
                "error": True,
                "last_updated": datetime.now().isoformat()
            })

        return jsonify({
            "success": False,
            "error": f"Error getting BBC fixtures: {str(e)}",
            "scraping_date": datetime.now().strftime("%Y-%m-%d"),
            "next_saturday": get_current_prediction_week(),
            "matches": fallback_matches,
            "selected_matches": [],
            "total_matches": 0,
            "selected_count": 0,
            "placeholder_count": len(SELECTORS),
            "last_updated": datetime.now().isoformat(),
            "fallback": True,
            "statistics": {
                "completion_percentage": 0,
                "error": True,
                "error_message": str(e)
            }
        }), 500

@app.route('/api/bbc-live-scores')
def get_bbc_live_scores():
    """API endpoint to get live scores from BBC - ONLY for selected games."""
    try:
        # Get target date (today by default, or specified date)
        target_date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))

        # Get current week's selections
        week = get_current_prediction_week()

        # Check if data_manager is available before calling methods
        if data_manager is None:
            print("ERROR: data_manager is None - cannot load selections for BBC live scores")
            return jsonify({
                "success": False,
                "error": "Data manager not available",
                "last_updated": datetime.now().isoformat()
            }), 500

        selections = data_manager.load_weekly_selections(week) or {}

        if not selections:
            # No selections yet - return empty structure
            return jsonify({
                "success": True,
                "target_date": target_date,
                "scraping_date": datetime.now().strftime("%Y-%m-%d"),
                "live_matches": [],
                "total_matches": 0,
                "selected_count": 0,
                "placeholder_count": len(SELECTORS),
                "last_updated": datetime.now().isoformat()
            })

        # Get live scores from enhanced BBC scraper
        if BBCSportScraper is None:
            return jsonify({
                "success": False,
                "error": "BBC scraper not available",
                "last_updated": datetime.now().isoformat()
            }), 500

        scraper = BBCSportScraper()
        live_result = scraper.scrape_live_scores(target_date)

        # Filter to only selected matches and enhance with selector info
        all_live_matches = live_result.get("live_matches", [])
        selected_live_matches = []

        for selector, match_data in selections.items():
            home_team = match_data.get('home_team')
            away_team = match_data.get('away_team')

            # Find matching live data for this selection
            for live_match in all_live_matches:
                if (live_match.get('home_team') == home_team and
                    live_match.get('away_team') == away_team):
                    # Add selector info to live match data
                    enhanced_match = live_match.copy()
                    enhanced_match['selector'] = selector
                    enhanced_match['prediction'] = match_data.get('prediction', 'TBD')
                    enhanced_match['confidence'] = match_data.get('confidence', 5)
                    selected_live_matches.append(enhanced_match)
                    break

        return jsonify({
            "success": True,
            "target_date": live_result.get("target_date"),
            "scraping_date": live_result.get("scraping_date"),
            "live_matches": selected_live_matches,  # Only selected matches
            "total_matches": len(selected_live_matches),
            "selected_count": len(selected_live_matches),
            "placeholder_count": len(SELECTORS) - len(selected_live_matches),
            "last_updated": datetime.now().isoformat()
        })

    except Exception as e:
        # Enhanced error handling with fallback data structure
        fallback_matches = []
        for selector in SELECTORS:
            fallback_matches.append({
                "selector": selector,
                "home_team": None,
                "away_team": None,
                "home_score": 0,
                "away_score": 0,
                "status": "error",
                "match_time": "—",
                "league": None,
                "prediction": "TBD",
                "confidence": 5,
                "is_selected": False,
                "placeholder_text": "Error loading live scores",
                "error": True,
                "last_updated": datetime.now().isoformat()
            })

        return jsonify({
            "success": False,
            "error": f"Error getting BBC live scores: {str(e)}",
            "target_date": datetime.now().strftime('%Y-%m-%d'),
            "scraping_date": datetime.now().strftime("%Y-%m-%d"),
            "live_matches": fallback_matches,
            "total_matches": 0,
            "selected_count": 0,
            "placeholder_count": len(SELECTORS),
            "last_updated": datetime.now().isoformat(),
            "fallback": True,
            "statistics": {
                "completion_percentage": 0,
                "error": True,
                "error_message": str(e)
            }
        }), 500

@app.route('/api/bbc-matches/<date>')
def get_bbc_matches_for_date(date):
    """API endpoint to get BBC matches for a specific date."""
    try:
        # Validate date format
        try:
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            return jsonify({
                "success": False,
                "error": "Invalid date format. Use YYYY-MM-DD",
                "last_updated": datetime.now().isoformat()
            }), 400

        # Try to get matches from DataManager cache first
        cached_fixtures = None
        if data_manager is not None:
            try:
                app.logger.info(f"Attempting to load cached fixtures for {date}")
                cached_fixtures = data_manager.get_bbc_fixtures(date)
                app.logger.info(f"DataManager returned: {len(cached_fixtures) if cached_fixtures else 0} fixtures")

                if cached_fixtures:
                    app.logger.info(f"Using cached fixtures for {date}")
                else:
                    app.logger.warning(f"No cached fixtures found for {date}")
            except Exception as e:
                app.logger.error(f"Error loading cached fixtures: {e}")
                import traceback
                app.logger.error(f"Traceback: {traceback.format_exc()}")

        # If no cached data, fall back to scraping
        if not cached_fixtures:
            if BBCSportScraper is not None:
                try:
                    scraper = BBCSportScraper()

                    # Use the unified scraping approach for both fixtures and live scores
                    try:
                        fixtures_result = scraper.scrape_unified_bbc_matches(date, "fixtures").get("matches", [])
                    except:
                        fixtures_result = []

                    try:
                        live_result = scraper.scrape_unified_bbc_matches(date, "live").get("matches", [])
                    except:
                        live_result = []

                    # Combine results
                    all_matches = fixtures_result + live_result

                    # Cache successful scraping results if we got data
                    if all_matches:
                        try:
                            # Convert scraper matches to cache format if needed
                            cache_data = []
                            for match in all_matches:
                                cache_match = match.copy()
                                # Ensure required fields for caching
                                if 'id' not in cache_match:
                                    cache_match['id'] = f"{match.get('league', 'Unknown')}_{match.get('home_team', '')}_{match.get('away_team', '')}"
                                cache_data.append(cache_match)

                            # Cache the scraped data
                            if data_manager is not None:
                                data_manager.cache_bbc_fixtures(cache_data, date)
                                app.logger.info(f"Cached {len(cache_data)} scraped fixtures for {date}")
                        except Exception as cache_error:
                            app.logger.warning(f"Failed to cache scraped fixtures: {cache_error}")

                    return jsonify({
                        "success": True,
                        "date": date,
                        "fixtures": fixtures_result,
                        "live_scores": live_result,
                        "total_matches": len(all_matches),
                        "last_updated": datetime.now().isoformat()
                    })
                except Exception as e:
                    app.logger.error(f"Error with BBC scraper: {e}")
                    # Continue with empty matches list - don't fail completely
            else:
                app.logger.warning("BBC scraper not available - returning empty matches")

        # Use cached data if available
        if cached_fixtures:
            # Separate cached fixtures into fixtures and live scores based on status
            fixtures_result = []
            live_result = []

            for match in cached_fixtures:
                status = match.get('status', 'not_started')
                if status in ['live', 'finished', 'first_half', 'second_half']:
                    # Treat as live score
                    live_match = match.copy()
                    live_match['match_time'] = match.get('match_time', '0\'')
                    live_result.append(live_match)
                else:
                    # Treat as fixture
                    fixtures_result.append(match)

            # Combine results
            all_matches = fixtures_result + live_result

            return jsonify({
                "success": True,
                "date": date,
                "fixtures": fixtures_result,
                "live_scores": live_result,
                "total_matches": len(all_matches),
                "last_updated": datetime.now().isoformat(),
                "cache_used": True
            })

        # Fallback: return empty structure if no data available
        return jsonify({
            "success": True,
            "date": date,
            "fixtures": [],
            "live_scores": [],
            "total_matches": 0,
            "last_updated": datetime.now().isoformat()
        })

    except Exception as e:
        # Enhanced error handling with fallback data structure
        return jsonify({
            "success": False,
            "error": f"Error getting BBC matches for date: {str(e)}",
            "date": date,
            "fixtures": [],
            "live_scores": [],
            "total_matches": 0,
            "last_updated": datetime.now().isoformat(),
            "fallback": True,
            "statistics": {
                "completion_percentage": 0,
                "error": True,
                "error_message": str(e)
            }
        }), 500

@app.route('/api/modern-tracker-data')
def get_modern_tracker_data():
    """Enhanced API endpoint specifically for modern interface with unified data structure."""
    try:
        # Get current week's selections
        week = get_current_prediction_week()

        # Check if data_manager is available before calling methods
        if data_manager is None:
            print("ERROR: data_manager is None - cannot load selections for modern tracker data")
            return jsonify({
                "success": False,
                "error": "Data manager not available",
                "last_updated": datetime.now().isoformat(),
                "fallback": True
            }), 500

        selections = data_manager.load_weekly_selections(week)

        # Get current live scores for selected matches
        target_date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))

        # Initialize response structure
        response_data = {
            "success": True,
            "target_date": target_date,
            "week": week,
            "selectors": SELECTORS,
            "selections": {},
            "matches": {},
            "statistics": {
                "total_selectors": len(SELECTORS),
                "selected_count": 0,
                "placeholder_count": len(SELECTORS),
                "btts_detected": 0,
                "btts_pending": 0,
                "btts_failed": 0,
                "completion_percentage": 0,
                "live_matches": 0,
                "finished_matches": 0,
                "not_started_matches": 0
            },
            "last_updated": datetime.now().isoformat()
        }

        # Process selections with enhanced data structure
        if selections:
            selected_count = 0
            for selector in SELECTORS:
                if selector in selections:
                    match_data = selections[selector]
                    if match_data and isinstance(match_data, dict):
                        # Enhanced match data structure
                        enhanced_match = {
                            "home_team": match_data.get("home_team"),
                            "away_team": match_data.get("away_team"),
                            "prediction": match_data.get("prediction", "TBD"),
                            "confidence": match_data.get("confidence", 5),
                            "assigned_at": match_data.get("assigned_at", datetime.now().isoformat()),
                            "league": match_data.get("league", "Unknown"),
                            "status": "not_started",
                            "home_score": 0,
                            "away_score": 0,
                            "match_time": "0'",
                            "btts_detected": False,
                            "is_selected": True,
                            "last_updated": datetime.now().isoformat()
                        }
                        response_data["selections"][selector] = enhanced_match
                        response_data["matches"][selector] = enhanced_match
                        selected_count += 1
                else:
                    # Placeholder for unselected selector
                    placeholder_match = {
                        "home_team": None,
                        "away_team": None,
                        "prediction": "TBD",
                        "confidence": 0,
                        "assigned_at": None,
                        "league": None,
                        "status": "no_selection",
                        "home_score": 0,
                        "away_score": 0,
                        "match_time": "—",
                        "btts_detected": False,
                        "is_selected": False,
                        "placeholder_text": "Awaiting Match Assignment",
                        "last_updated": datetime.now().isoformat()
                    }
                    response_data["matches"][selector] = placeholder_match

            # Update statistics
            response_data["statistics"]["selected_count"] = selected_count
            response_data["statistics"]["placeholder_count"] = len(SELECTORS) - selected_count
            response_data["statistics"]["completion_percentage"] = max(0, min(100, int((selected_count / len(SELECTORS)) * 100))) if len(SELECTORS) > 0 else 0

        # Get live scores from BBC for BTTS detection
        try:
            if BBCSportScraper is not None:
                scraper = BBCSportScraper()
                live_result = scraper.scrape_live_scores(target_date)
                all_live_matches = live_result.get("live_matches", [])
                app.logger.info(f"[DEBUG] /api/modern-tracker-data - Scraped {len(all_live_matches)} live matches from BBC")
            else:
                all_live_matches = []
                app.logger.warning("[DEBUG] /api/modern-tracker-data - BBC scraper not available")
        except Exception as e:
            app.logger.error(f"[DEBUG] /api/modern-tracker-data - Error scraping BBC live scores: {e}")
            all_live_matches = []

        # Update matches with BBC live data
        for selector in SELECTORS:
            if selector in response_data["matches"]:
                match_data = response_data["matches"][selector]
                if match_data.get('is_selected'):
                    home_team = match_data.get('home_team')
                    away_team = match_data.get('away_team')

                    # Find matching live data
                    live_match = None
                    for bbc_match in all_live_matches:
                        if (bbc_match.get('home_team') == home_team and
                            bbc_match.get('away_team') == away_team):
                            live_match = bbc_match
                            break

                    if live_match:
                        # Update with BBC data
                        home_score = live_match.get('home_score', 0)
                        away_score = live_match.get('away_score', 0)
                        status = live_match.get('status', 'not_started')
                        match_time = live_match.get('match_time', '0\'')
                        league = live_match.get('league', 'Unknown')
                        btts_detected = home_score > 0 and away_score > 0

                        response_data["matches"][selector].update({
                            "home_score": home_score,
                            "away_score": away_score,
                            "status": status,
                            "match_time": match_time,
                            "league": league,
                            "btts_detected": btts_detected,
                            "last_updated": datetime.now().isoformat()
                        })
                        app.logger.debug(f"[DEBUG] /api/modern-tracker-data - Updated {selector}: {home_team} vs {away_team} - {home_score}-{away_score} ({status})")

        # Calculate final statistics
        btts_detected = sum(1 for match in response_data["matches"].values() if match.get('btts_detected'))
        btts_pending = sum(1 for match in response_data["matches"].values() if match.get('is_selected') and match.get('status') in ['not_started', 'live'])
        btts_failed = sum(1 for match in response_data["matches"].values() if match.get('status') == 'finished' and not match.get('btts_detected'))
        live_matches = sum(1 for match in response_data["matches"].values() if match.get('status') == 'live')
        finished_matches = sum(1 for match in response_data["matches"].values() if match.get('status') == 'finished')
        not_started_matches = sum(1 for match in response_data["matches"].values() if match.get('status') == 'not_started')

        response_data["statistics"].update({
            "btts_detected": btts_detected,
            "btts_pending": btts_pending,
            "btts_failed": btts_failed,
            "live_matches": live_matches,
            "finished_matches": finished_matches,
            "not_started_matches": not_started_matches
        })

        return jsonify(response_data)

    except Exception as e:
        # Enhanced error handling with fallback data structure
        fallback_matches = {}
        for selector in SELECTORS:
            fallback_matches[selector] = {
                "home_team": None,
                "away_team": None,
                "prediction": "TBD",
                "confidence": 0,
                "assigned_at": None,
                "league": None,
                "status": "error",
                "home_score": 0,
                "away_score": 0,
                "match_time": "—",
                "btts_detected": False,
                "is_selected": False,
                "placeholder_text": "Error loading data",
                "error": True,
                "last_updated": datetime.now().isoformat()
            }

        return jsonify({
            "success": False,
            "error": f"Error getting modern tracker data: {str(e)}",
            "target_date": datetime.now().strftime('%Y-%m-%d'),
            "week": get_current_prediction_week(),
            "selectors": SELECTORS,
            "selections": {},
            "matches": fallback_matches,
            "statistics": {
                "total_selectors": len(SELECTORS),
                "selected_count": 0,
                "placeholder_count": len(SELECTORS),
                "btts_detected": 0,
                "btts_pending": 0,
                "btts_failed": 0,
                "completion_percentage": 0,
                "live_matches": 0,
                "finished_matches": 0,
                "not_started_matches": 0,
                "error": True,
                "error_message": str(e)
            },
            "last_updated": datetime.now().isoformat(),
            "fallback": True
        }), 500


@app.route('/api/tracker-data')
def get_tracker_data():
    """API endpoint to get complete tracker data with selections and placeholders."""
    try:
        # Get current week's selections
        week = get_current_prediction_week()

        # Check if data_manager is available before calling methods
        if data_manager is None:
            print("ERROR: data_manager is None - cannot load selections for tracker data")
            return jsonify({
                "success": False,
                "error": "Data manager not available",
                "last_updated": datetime.now().isoformat()
            }), 500

        selections = data_manager.load_weekly_selections(week)

        # Get current live scores for selected matches
        target_date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))

        tracker_matches = []
        selected_count = 0
        placeholder_count = 0

        # Process each selector
        for selector in SELECTORS:
            if selections and selector in selections:
                # Selector has a match assigned
                match_data = selections[selector]
                home_team = match_data.get('home_team')
                away_team = match_data.get('away_team')

                # Try to get live score data for this match
                live_score_data = None
                try:
                    if BBCSportScraper is None:
                        pass  # Continue without live data if scraper not available
                    else:
                        scraper = BBCSportScraper()
                        live_result = scraper.scrape_live_scores(target_date)
                        live_matches = live_result.get("live_matches", [])

                        for live_match in live_matches:
                            if (live_match.get('home_team') == home_team and
                                live_match.get('away_team') == away_team):
                                live_score_data = live_match
                                break
                except:
                    pass  # Continue without live data if scraping fails

                if live_score_data:
                    # Use live score data
                    match_info = {
                        "selector": selector,
                        "home_team": home_team,
                        "away_team": away_team,
                        "home_score": live_score_data.get('home_score', 0),
                        "away_score": live_score_data.get('away_score', 0),
                        "status": live_score_data.get('status', 'not_started'),
                        "match_time": live_score_data.get('match_time', '0\''),
                        "league": live_score_data.get('league', 'Unknown'),
                        "prediction": match_data.get('prediction', 'TBD'),
                        "confidence": match_data.get('confidence', 5),
                        "is_selected": True,
                        "last_updated": datetime.now().isoformat()
                    }
                else:
                    # Use fixture data (no live scores yet)
                    match_info = {
                        "selector": selector,
                        "home_team": home_team,
                        "away_team": away_team,
                        "home_score": 0,
                        "away_score": 0,
                        "status": "not_started",
                        "match_time": "0'",
                        "league": "Unknown",  # Would need to get from BBC fixture data
                        "prediction": match_data.get('prediction', 'TBD'),
                        "confidence": match_data.get('confidence', 5),
                        "is_selected": True,
                        "last_updated": datetime.now().isoformat()
                    }

                tracker_matches.append(match_info)
                selected_count += 1
            else:
                # Selector has no match assigned - create placeholder
                placeholder_info = {
                    "selector": selector,
                    "home_team": None,
                    "away_team": None,
                    "home_score": 0,
                    "away_score": 0,
                    "status": "no_selection",
                    "match_time": "—",
                    "league": None,
                    "prediction": "TBD",
                    "confidence": 0,
                    "is_selected": False,
                    "placeholder_text": "Awaiting Match Assignment",
                    "last_updated": datetime.now().isoformat()
                }
                tracker_matches.append(placeholder_info)
                placeholder_count += 1

        # Calculate BTTS statistics
        btts_detected = sum(1 for match in tracker_matches if match.get('home_score', 0) > 0 and match.get('away_score', 0) > 0)
        btts_pending = sum(1 for match in tracker_matches if match.get('is_selected') and match.get('status') in ['not_started', 'live'])
        btts_failed = sum(1 for match in tracker_matches if match.get('status') == 'finished' and not (match.get('home_score', 0) > 0 and match.get('away_score', 0) > 0))

        # Calculate enhanced statistics
        completion_percentage = max(0, min(100, int((selected_count / len(SELECTORS)) * 100))) if len(SELECTORS) > 0 else 0

        # Enhanced match statistics
        live_matches = len([m for m in tracker_matches if m.get('status') == 'live'])
        finished_matches = len([m for m in tracker_matches if m.get('status') == 'finished'])
        not_started_matches = len([m for m in tracker_matches if m.get('status') == 'not_started'])

        return jsonify({
            "success": True,
            "target_date": target_date,
            "week": week,
            "matches": tracker_matches,
            "selectors": SELECTORS,
            "statistics": {
                "total_selectors": len(SELECTORS),
                "selected_count": selected_count,
                "placeholder_count": placeholder_count,
                "btts_detected": btts_detected,
                "btts_pending": btts_pending,
                "btts_failed": btts_failed,
                "completion_percentage": completion_percentage,
                "live_matches": live_matches,
                "finished_matches": finished_matches,
                "not_started_matches": not_started_matches,
            },
            "last_updated": datetime.now().isoformat()
        })

    except Exception as e:
        # Enhanced error handling with fallback data structure
        fallback_matches = []
        for selector in SELECTORS:
            fallback_matches.append({
                "selector": selector,
                "home_team": None,
                "away_team": None,
                "home_score": 0,
                "away_score": 0,
                "status": "error",
                "match_time": "—",
                "league": None,
                "prediction": "TBD",
                "confidence": 0,
                "is_selected": False,
                "placeholder_text": "Error loading data",
                "error": True,
                "last_updated": datetime.now().isoformat()
            })

        return jsonify({
            "success": False,
            "error": f"Error getting tracker data: {str(e)}",
            "target_date": datetime.now().strftime('%Y-%m-%d'),
            "week": get_current_prediction_week(),
            "matches": fallback_matches,
            "selectors": SELECTORS,
            "statistics": {
                "total_selectors": len(SELECTORS),
                "selected_count": 0,
                "placeholder_count": len(SELECTORS),
                "btts_detected": 0,
                "btts_pending": 0,
                "btts_failed": 0,
                "completion_percentage": 0,
                "error": True,
                "error_message": str(e)
            },
            "last_updated": datetime.now().isoformat(),
            "fallback": True
        }), 500


# ===== HEALTH CHECK AND MONITORING =====

@app.route('/health')
def health_check():
    """Enhanced health check endpoint for monitoring with production debugging info"""
    try:
        # Enhanced service status checking
        services = {
            'bbc_scraper': BBCSportScraper is not None,
            'btts_detector': BTTS_DETECTOR_AVAILABLE,
            'data_manager': data_manager is not None
        }

        # Check filesystem permissions
        filesystem_status = {}
        test_directories = ['data', 'logs']
        for directory in test_directories:
            try:
                os.makedirs(directory, exist_ok=True)
                test_file = os.path.join(directory, '.health_check_test')
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)
                filesystem_status[directory] = 'writable'
            except Exception as e:
                filesystem_status[directory] = f'error: {e}'

        # Check data_manager initialization errors
        data_manager_errors = []
        if data_manager and hasattr(data_manager, 'initialization_errors'):
            data_manager_errors = data_manager.initialization_errors

        health_status = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0',
            'environment': 'production' if not config.DEBUG else 'development',
            'services': services,
            'filesystem': filesystem_status,
            'data_manager_errors': data_manager_errors,
            'working_directory': os.getcwd(),
            'python_path': sys.executable
        }

        # Determine overall health
        critical_issues = []

        # Check if required services are missing
        if config.ENABLE_BBC_SCRAPER and not services['bbc_scraper']:
            critical_issues.append('BBC scraper not available but enabled')

        if not services['data_manager']:
            critical_issues.append('Data manager not available')

        # Check filesystem issues
        for directory, status in filesystem_status.items():
            if 'error' in status:
                critical_issues.append(f'Filesystem issue with {directory}: {status}')

        # Check data manager initialization issues
        if data_manager_errors:
            critical_issues.extend([f'DataManager: {error}' for error in data_manager_errors])

        if critical_issues:
            health_status['status'] = 'degraded'
            health_status['issues'] = critical_issues

        status_code = 200 if health_status['status'] == 'healthy' else 503
        return jsonify(health_status), status_code

    except Exception as e:
        app.logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat(),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/metrics')
def metrics():
    """Application metrics endpoint"""
    if not os.getenv('METRICS_ENABLED', 'False').lower() == 'true':
        return jsonify({'error': 'Metrics not enabled'}), 404

    try:
        metrics_data = {
            'timestamp': datetime.now().isoformat(),
            'uptime_seconds': 0,  # Would need to track this
            'api_usage': {},
            'cache_stats': {},
            'system': {
                'python_version': sys.version,
                'platform': sys.platform
            }
        }

        return jsonify(metrics_data)

    except Exception as e:
        app.logger.error(f"Metrics endpoint failed: {e}")
        return jsonify({'error': str(e)}), 500

# ===== ERROR HANDLERS =====

@app.errorhandler(404)
def not_found(error):
    app.logger.warning(f"404 error: {request.url}")
    return jsonify({'error': 'Not found', 'status_code': 404}), 404

@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f"500 error: {error}")
    return jsonify({'error': 'Internal server error', 'status_code': 500}), 500

@app.errorhandler(429)
def rate_limit_exceeded(error):
    app.logger.warning(f"Rate limit exceeded: {request.remote_addr}")
    return jsonify({
        'error': 'Rate limit exceeded',
        'status_code': 429,
        'message': 'Too many requests'
    }), 429

# ===== REQUEST LOGGING =====

@app.before_request
def log_request_info():
    """Log request information"""
    app.logger.info(f"{request.method} {request.url} from {request.remote_addr}")

@app.after_request
def log_response_info(response):
    """Log response information"""
    app.logger.info(f"Response: {response.status_code}")
    return response

# ===== GRACEFUL SHUTDOWN =====

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    app.logger.info(f"Received signal {signum}. Shutting down gracefully...")
    sys.exit(0)

if __name__ == '__main__':
    import signal

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Run with production settings
    app.logger.info(f"Starting application in {'development' if config.DEBUG else 'production'} mode")
    app.logger.info(f"Listening on {config.HOST}:{config.PORT}")

    # Check for port override from command line
    import sys
    port = 5000  # Default port
    host = '127.0.0.1'  # Bind to localhost for testing
    if len(sys.argv) > 2 and sys.argv[1] == '--port':
        try:
            port = int(sys.argv[2])
        except ValueError:
            pass

    if config.DEBUG:
        # Development server
        app.run(
            debug=config.DEBUG,
            host=host,
            port=port,
            use_reloader=False  # Disable reloader in production-like environment
        )
    else:
        # Production-like server (still using Flask dev server for now)
        # In production, use gunicorn: gunicorn --config gunicorn.conf.py app:app
        app.run(
            debug=False,
            host=host,
            port=port,
            use_reloader=False
        )