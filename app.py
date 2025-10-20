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
import logging
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler

# Import Flask and extensions
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Import configuration first for logging
from config import get_config

# Import custom modules with error handling
try:
    from bbc_scraper import BBCSportScraper
    print("BBC scraper imported successfully")
except Exception as e:
    print(f"ERROR: Failed to import BBC scraper: {e}")
    BBCSportScraper = None

try:
    from data_manager import data_manager
    print("Data manager imported successfully")
except Exception as e:
    print(f"ERROR: Failed to import data manager: {e}")
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
print(f"Feature flags - BBC: {config.ENABLE_BBC_SCRAPER}, Sofascore: {config.ENABLE_SOFA_SCORE_API}")
print(f"API Keys configured - Sofascore: {'Yes' if config.SOFASCORE_API_KEY else 'No'}")

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

    if config.SOFASCORE_API_KEY:
        print("✓ Sofascore API key configured")
    else:
        print("⚠ Sofascore API key not configured - live scores will be disabled")

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

# Import Sofascore Live Scores API for live tracking
try:
    from sofascore_optimized import SofascoreLiveScoresAPI
    # Only initialize if API key is available
    if config.SOFASCORE_API_KEY:
        sofascore_api = SofascoreLiveScoresAPI(api_key=config.SOFASCORE_API_KEY)
        SOFASCORE_AVAILABLE = True
        app.logger.info("Sofascore API loaded successfully")
    else:
        sofascore_api = None
        SOFASCORE_AVAILABLE = False
        app.logger.warning("Sofascore API key not configured - live scores disabled")
except ImportError:
    sofascore_api = None
    SOFASCORE_AVAILABLE = False
    app.logger.warning("Sofascore API not available")
except Exception as e:
    sofascore_api = None
    SOFASCORE_AVAILABLE = False
    app.logger.error(f"Error initializing Sofascore API: {e}")

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

    return target_date.strftime('%Y-%m-%d')

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

def map_selections_to_sofascore_ids(selections):
    """
    Map current week's selections to Sofascore match IDs.

    Args:
        selections (dict): Current week's selections

    Returns:
        dict: Mapping of selector names to Sofascore match IDs
    """
    if not SOFASCORE_AVAILABLE or not sofascore_api:
        return {}

    try:
        # Get current week's BBC fixtures for team name matching
        week = get_current_prediction_week()

        # Check if data_manager is available before calling methods
        if data_manager is None:
            print("ERROR: data_manager is None - cannot get BBC fixtures")
            return {}

        bbc_fixtures = data_manager.get_bbc_fixtures(week)

        if not bbc_fixtures:
            return {}

        # Get live scores from Sofascore to find match IDs
        live_data = sofascore_api.get_live_scores_batch()

        if not live_data or 'events' not in live_data:
            return {}

        match_mapping = {}

        # For each selection, find the corresponding Sofascore match ID
        for selector, match_data in selections.items():
            home_team = match_data.get('home_team')
            away_team = match_data.get('away_team')

            if not home_team or not away_team:
                continue

            # Find matching Sofascore event
            for event in live_data['events']:
                sofascore_home = event.get('homeTeam', {}).get('name', '')
                sofascore_away = event.get('awayTeam', {}).get('name', '')

                # Try exact match first
                if (sofascore_home == home_team and sofascore_away == away_team):
                    match_mapping[selector] = {
                        'sofascore_id': event.get('id'),
                        'home_team': home_team,
                        'away_team': away_team,
                        'status': event.get('status', {}).get('type', 'not_started')
                    }
                    break

                # Try partial match (for team name variations)
                if (home_team.lower() in sofascore_home.lower() and
                    away_team.lower() in sofascore_away.lower()):
                    match_mapping[selector] = {
                        'sofascore_id': event.get('id'),
                        'home_team': home_team,
                        'away_team': away_team,
                        'status': event.get('status', {}).get('type', 'not_started'),
                        'note': 'partial_match'
                    }
                    break

        return match_mapping

    except Exception as e:
        print(f"Error mapping selections to Sofascore IDs: {e}")
        return {}

def load_selections():
    """Load existing selections for the current week using DataManager."""
    week = get_current_prediction_week()

    # Check if data_manager is available before calling methods
    if data_manager is None:
        print("ERROR: data_manager is None - cannot load selections")
        return {"selectors": {}, "matches": [], "last_updated": None}

    # Load selections using DataManager
    selections = data_manager.load_weekly_selections(week)

    if selections is None:
        return {"selectors": {}, "matches": [], "last_updated": None}

    # Convert DataManager format to expected format for template
    # Add assigned_at field for template compatibility
    enhanced_selections = {}
    for selector, match_data in selections.items():
        enhanced_match_data = match_data.copy()
        # Add assigned_at field if missing (for template compatibility)
        if 'assigned_at' not in enhanced_match_data:
            enhanced_match_data['assigned_at'] = datetime.now().isoformat()
        enhanced_selections[selector] = enhanced_match_data

    return {
        "selectors": enhanced_selections,
        "matches": [],  # This will be populated from scraper data
        "last_updated": None  # Could be enhanced to track this
    }

def save_selections(selections_data):
    """Save selections using DataManager."""
    week = get_current_prediction_week()

    # Check if data_manager is available before calling methods
    if data_manager is None:
        print("ERROR: data_manager is None - cannot save selections")
        return False

    # Extract just the selections part for DataManager
    selections_only = selections_data.get("selectors", {})

    # Save using DataManager
    success = data_manager.save_weekly_selections(selections_only, week)

    if success:
        # Update the last_updated timestamp in the original data
        selections_data["last_updated"] = datetime.now().isoformat()
        return True
    else:
        return False

@app.route('/')
def index():
    """Redirect to admin interface."""
    return app.redirect('/admin')

@app.route('/admin')
def admin():
    """Main admin interface for match selection."""
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

        # Try to get matches from BBC scraper
        if BBCSportScraper is not None:
            try:
                scraper = BBCSportScraper()
                scraper_result = scraper.scrape_saturday_3pm_fixtures()
                matches = scraper_result.get("matches_3pm", [])
                target_date = scraper_result.get("next_saturday", target_date)

                # If no matches found, try to find an alternative date
                if not matches:
                    app.logger.info(f"No matches found for {target_date}, searching for alternative date")
                    try:
                        alternative_date = find_next_available_fixtures_date(target_date, max_days_ahead=14)

                        if alternative_date and alternative_date != target_date:
                            app.logger.info(f"Found alternative date with matches: {alternative_date}")
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
                            except Exception as e:
                                app.logger.warning(f"Error scraping alternative date {alternative_date}: {e}")
                                # Continue with empty matches list
                    except Exception as e:
                        app.logger.warning(f"Error finding alternative date: {e}")
                        # Continue with empty matches list
            except Exception as e:
                app.logger.error(f"Error with BBC scraper: {e}")
                # Continue with empty matches list - don't fail completely
        else:
            app.logger.warning("BBC scraper not available - showing admin interface without live data")

        # Load existing selections
        if data_manager is None:
            return "Error: Data manager module not available", 500

        selections_data = load_selections()

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
    """API endpoint for assigning a match to a selector."""
    try:
        data = request.get_json()
        match_id = data.get('match_id')
        selector = data.get('selector')

        if not match_id or not selector:
            return jsonify({"success": False, "error": "Missing match_id or selector"}), 400

        # Load current selections
        selections_data = load_selections()

        # Check if selector already has a match - allow reassignment
        if selector in selections_data.get("selectors", {}):
            # Remove the existing assignment to allow reassignment
            del selections_data["selectors"][selector]

        # Check if match is already assigned
        for sel, match in selections_data.get("selectors", {}).items():
            if match.get("id") == match_id:
                return jsonify({"success": False, "error": "Match already assigned to another selector"}), 400

        # Find the match details - try to use cached data first
        match_details = None

        # First, try to get cached match data from DataManager
        try:
            week = get_current_prediction_week()

            # Check if data_manager is available before calling methods
            if data_manager is None:
                print("ERROR: data_manager is None - cannot get cached fixtures")
            else:
                cached_fixtures = data_manager.get_bbc_fixtures(week)
                if cached_fixtures:
                    for match in cached_fixtures:
                        current_id = f"{match['league']}_{match['home_team']}_{match['away_team']}"
                        if current_id == match_id:
                            match_details = match
                            break
        except Exception as e:
            print(f"Error loading cached fixtures: {e}")

        # If no cached data or match not found, try scraping (but handle errors gracefully)
        if not match_details:
            try:
                if BBCSportScraper is None:
                    return jsonify({"success": False, "error": "BBC scraper not available"}), 500

                scraper = BBCSportScraper()
                scraper_result = scraper.scrape_saturday_3pm_fixtures()
                matches = scraper_result.get("matches_3pm", [])

                for match in matches:
                    current_id = f"{match['league']}_{match['home_team']}_{match['away_team']}"
                    if current_id == match_id:
                        match_details = match
                        break
            except Exception as e:
                print(f"Error scraping fixtures: {e}")
                return jsonify({"success": False, "error": "Unable to retrieve match data. Please try again later."}), 500

        # If no cached data or match not found, try scraping (but handle errors gracefully)
        if not match_details:
            try:
                if BBCSportScraper is None:
                    return jsonify({"success": False, "error": "BBC scraper not available"}), 500

                scraper = BBCSportScraper()
                scraper_result = scraper.scrape_saturday_3pm_fixtures()
                matches = scraper_result.get("matches_3pm", [])

                for match in matches:
                    current_id = f"{match['league']}_{match['home_team']}_{match['away_team']}"
                    if current_id == match_id:
                        match_details = match
                        break
            except Exception as e:
                print(f"Error scraping fixtures: {e}")
                return jsonify({"success": False, "error": "Unable to retrieve match data. Please try again later."}), 500

        if not match_details:
            return jsonify({"success": False, "error": "Match not found"}), 404

        # Assign the match - update selections_data for API compatibility
        if "selectors" not in selections_data:
            selections_data["selectors"] = {}

        selections_data["selectors"][selector] = {
            "home_team": match_details["home_team"],
            "away_team": match_details["away_team"],
            "prediction": "TBD",  # Required by DataManager validation
            "confidence": 5       # Required by DataManager validation
        }

        # Save selections using DataManager
        if save_selections(selections_data):
            return jsonify({"success": True, "message": f"Match assigned to {selector}"})
        else:
            return jsonify({"success": False, "error": "Failed to save selections"}), 500

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

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
    """API endpoint to get current selections."""
    try:
        selections_data = load_selections()
        return jsonify(selections_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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

@app.route('/btts-tracker-test')
def btts_tracker_test():
    """Test version of BTTS tracker with mock data for UI testing."""
    try:
        return render_template('test_tracker.html')

    except Exception as e:
        return f"Error loading BTTS tracker test: {str(e)}", 500

@app.route('/mockup')
def mockup():
    """Mockup page showing the final live page vision."""
    try:
        return render_template('mockup.html')

    except Exception as e:
        return f"Error loading mockup: {str(e)}", 500

@app.route('/api/btts-status')
def get_btts_status():
    """API endpoint to get current BTTS status for all matches."""
    try:
        # Load current week's selections
        week = get_current_prediction_week()

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

        selections = data_manager.load_weekly_selections(week)

        if not selections:
            return jsonify({
                "status": "NO_SELECTIONS",
                "message": "No selections found for current week",
                "matches": {},
                "statistics": {
                    "total_matches_tracked": 0,
                    "btts_detected": 0,
                    "btts_pending": 0,
                    "last_update": datetime.now().isoformat()
                },
                "last_updated": datetime.now().isoformat()
            })

        # Map selections to Sofascore match IDs
        match_mapping = map_selections_to_sofascore_ids(selections)

        # Get live scores and detect events
        matches_data = {}
        btts_detected = 0
        btts_pending = 0

        if SOFASCORE_AVAILABLE and sofascore_api:
            try:
                # Get live scores data
                live_data = sofascore_api.get_live_scores_batch()

                if live_data and 'events' in live_data:
                    # Detect match events (including BTTS)
                    detected_events = sofascore_api.detect_match_events(live_data)

                    # Process each tracked match
                    for selector, match_info in match_mapping.items():
                        sofascore_id = match_info.get('sofascore_id')
                        if not sofascore_id:
                            continue

                        # Find the match in live data
                        match_event = None
                        for event in live_data['events']:
                            if event.get('id') == sofascore_id:
                                match_event = event
                                break

                        if match_event:
                            home_score = match_event.get('homeScore', {}).get('current', 0)
                            away_score = match_event.get('awayScore', {}).get('current', 0)
                            status = match_event.get('status', {}).get('type', 'not_started')

                            # Check if BTTS occurred
                            is_btts = home_score > 0 and away_score > 0

                            matches_data[selector] = {
                                "sofascore_id": sofascore_id,
                                "home_team": match_info.get('home_team'),
                                "away_team": match_info.get('away_team'),
                                "home_score": home_score,
                                "away_score": away_score,
                                "status": status,
                                "btts_detected": is_btts,
                                "league": match_info.get('league', 'Unknown League'),
                                "last_updated": datetime.now().isoformat()
                            }

                            if is_btts:
                                btts_detected += 1
                            else:
                                btts_pending += 1

            except Exception as e:
                print(f"Error getting live scores: {e}")
                # Continue with cached/empty data if Sofascore fails

        # Get API usage statistics
        api_stats = {}
        if SOFASCORE_AVAILABLE and sofascore_api:
            api_stats = sofascore_api.get_usage_stats()

        return jsonify({
            "status": "ACTIVE" if matches_data else "NO_LIVE_DATA",
            "message": f"Tracking {len(matches_data)} matches with Sofascore integration",
            "matches": matches_data,
            "statistics": {
                "total_matches_tracked": len(match_mapping),
                "btts_detected": btts_detected,
                "btts_pending": btts_pending,
                "last_update": datetime.now().isoformat(),
                "sofascore_api_available": SOFASCORE_AVAILABLE,
                "api_calls_used": api_stats.get('api_calls_used', 0),
                "api_calls_target": api_stats.get('api_calls_target', '12-16')
            },
            "last_updated": datetime.now().isoformat(),
            "sofascore_integration": {
                "enabled": SOFASCORE_AVAILABLE,
                "cache_hit_rate": api_stats.get('cache_hit_rate', 0),
                "events_detected": api_stats.get('events_detected', 0)
            }
        })

    except Exception as e:
        return jsonify({
            "error": f"Error getting BTTS status: {str(e)}",
            "status": "ERROR",
            "last_updated": datetime.now().isoformat()
        }), 500

@app.route('/api/btts-status-test')
def get_btts_status_test():
    """Test API endpoint with mock BTTS data for UI testing."""
    try:
        # Mock data for testing the UI
        mock_matches = {
            "Glynny": {
                "sofascore_id": 1234567,
                "home_team": "Manchester City",
                "away_team": "Everton",
                "home_score": 2,
                "away_score": 1,
                "status": "live",
                "btts_detected": True,
                "league": "Premier League",
                "last_updated": datetime.now().isoformat()
            },
            "Eamonn Bone": {
                "sofascore_id": 1234568,
                "home_team": "Hull City",
                "away_team": "Charlton Athletic",
                "home_score": 1,
                "away_score": 0,
                "status": "finished",
                "btts_detected": False,
                "league": "Championship",
                "last_updated": datetime.now().isoformat()
            },
            "Mickey D": {
                "sofascore_id": 1234569,
                "home_team": "Burnley",
                "away_team": "Leeds United",
                "home_score": 0,
                "away_score": 0,
                "status": "live",
                "btts_detected": False,
                "league": "Championship",
                "last_updated": datetime.now().isoformat()
            },
            "Rob Carney": {
                "sofascore_id": 1234570,
                "home_team": "St. Mirren",
                "away_team": "Aberdeen",
                "home_score": 1,
                "away_score": 1,
                "status": "finished",
                "btts_detected": True,
                "league": "Scottish Premiership",
                "last_updated": datetime.now().isoformat()
            },
            "Steve H": {
                "sofascore_id": 1234571,
                "home_team": "Shrewsbury Town",
                "away_team": "Cambridge United",
                "home_score": 0,
                "away_score": 0,
                "status": "not_started",
                "btts_detected": False,
                "league": "League One",
                "last_updated": datetime.now().isoformat()
            },
            "Danny": {
                "sofascore_id": 1234572,
                "home_team": "Derby County",
                "away_team": "Queens Park Rangers",
                "home_score": 0,
                "away_score": 0,
                "status": "not_started",
                "btts_detected": False,
                "league": "Championship",
                "last_updated": datetime.now().isoformat()
            },
            "Eddie Lee": {
                "sofascore_id": 1234573,
                "home_team": "Burton Albion",
                "away_team": "Bolton Wanderers",
                "home_score": 0,
                "away_score": 0,
                "status": "not_started",
                "btts_detected": False,
                "league": "League One",
                "last_updated": datetime.now().isoformat()
            },
            "Fran Radar": {
                "sofascore_id": 1234574,
                "home_team": "Forfar Athletic",
                "away_team": "Clyde",
                "home_score": 0,
                "away_score": 0,
                "status": "not_started",
                "btts_detected": False,
                "league": "Scottish League Two",
                "last_updated": datetime.now().isoformat()
            }
        }

        # Calculate statistics
        btts_detected = sum(1 for match in mock_matches.values() if match['btts_detected'])
        btts_pending = sum(1 for match in mock_matches.values() if match['status'] in ['live', 'not_started'])
        btts_failed = sum(1 for match in mock_matches.values() if match['status'] == 'finished' and not match['btts_detected'])

        return jsonify({
            "status": "TEST_MODE",
            "message": "Test data for UI demonstration",
            "matches": mock_matches,
            "statistics": {
                "total_matches_tracked": len(mock_matches),
                "btts_detected": btts_detected,
                "btts_pending": btts_pending,
                "btts_failed": btts_failed,
                "last_update": datetime.now().isoformat(),
                "sofascore_api_available": True,
                "api_calls_used": 0,
                "api_calls_target": "12-16"
            },
            "last_updated": datetime.now().isoformat(),
            "sofascore_integration": {
                "enabled": True,
                "cache_hit_rate": 0,
                "events_detected": len(mock_matches)
            }
        })

    except Exception as e:
        return jsonify({
            "error": f"Error getting test BTTS status: {str(e)}",
            "status": "ERROR",
            "last_updated": datetime.now().isoformat()
        }), 500

@app.route('/api/btts-summary')
def get_btts_summary():
    """API endpoint to get BTTS accumulator summary."""
    try:
        # Load current week's selections
        week = get_current_prediction_week()

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

        # Get current BTTS status data (reuse the logic from get_btts_status)
        try:
            # Load current week's selections
            selections = data_manager.load_weekly_selections(week) if 'selections' not in locals() else selections

            if not selections:
                matches = {}
            else:
                # Map selections to Sofascore match IDs
                match_mapping = map_selections_to_sofascore_ids(selections)

                # Get live scores and detect events
                matches = {}
                if SOFASCORE_AVAILABLE and sofascore_api:
                    live_data = sofascore_api.get_live_scores_batch()
                    if live_data and 'events' in live_data:
                        for selector, match_info in match_mapping.items():
                            sofascore_id = match_info.get('sofascore_id')
                            if not sofascore_id:
                                continue

                            # Find the match in live data
                            for event in live_data['events']:
                                if event.get('id') == sofascore_id:
                                    home_score = event.get('homeScore', {}).get('current', 0)
                                    away_score = event.get('awayScore', {}).get('current', 0)
                                    status = event.get('status', {}).get('type', 'not_started')

                                    matches[selector] = {
                                        "sofascore_id": sofascore_id,
                                        "home_team": match_info.get('home_team'),
                                        "away_team": match_info.get('away_team'),
                                        "home_score": home_score,
                                        "away_score": away_score,
                                        "status": status,
                                        "btts_detected": home_score > 0 and away_score > 0,
                                        "last_updated": datetime.now().isoformat()
                                    }
                                    break
        except Exception as e:
            print(f"Error getting BTTS status for summary: {e}")
            matches = {}

        # Calculate summary statistics
        selectors_data = {}
        btts_success = 0
        btts_pending = 0
        btts_failed = 0

        if selections:
            for selector, match_data in selections.items():
                home_team = match_data.get('home_team')
                away_team = match_data.get('away_team')

                # Find corresponding match in BTTS data
                match_info = None
                for sel, info in matches.items():
                    if (info.get('home_team') == home_team and
                        info.get('away_team') == away_team):
                        match_info = info
                        break

                if match_info:
                    is_btts = match_info.get('btts_detected', False)
                    status = match_info.get('status', 'not_started')

                    selectors_data[selector] = {
                        "home_team": home_team,
                        "away_team": away_team,
                        "btts_detected": is_btts,
                        "status": status,
                        "home_score": match_info.get('home_score', 0),
                        "away_score": match_info.get('away_score', 0)
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
            "message": f"BTTS accumulator tracking active for {total_selections} selections",
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

@app.route('/api/btts-start-monitoring', methods=['POST'])
def start_btts_monitoring():
    """API endpoint to start BTTS monitoring."""
    try:
        if not SOFASCORE_AVAILABLE or not sofascore_api:
            return jsonify({
                "success": False,
                "error": "Sofascore API not available",
                "status": "API_UNAVAILABLE",
                "message": "Sofascore integration is not properly configured"
            }), 503

        # Get current usage stats
        api_stats = sofascore_api.get_usage_stats()

        # Check if we're within usage limits
        if api_stats.get('api_calls_used', 0) >= 20:  # Safety buffer
            return jsonify({
                "success": False,
                "error": "Monthly API limit exceeded",
                "status": "LIMIT_EXCEEDED",
                "message": f"API usage limit reached ({api_stats.get('api_calls_used', 0)}/16 calls this month)"
            }), 429

        return jsonify({
            "success": True,
            "message": "BTTS monitoring is active with Sofascore integration",
            "status": "ACTIVE",
            "api_usage": api_stats,
            "note": "Monitoring uses ultra-conservative API usage (12-16 calls/month target)"
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/btts-stop-monitoring', methods=['POST'])
def stop_btts_monitoring():
    """API endpoint to stop BTTS monitoring."""
    try:
        # Since we're using event-driven updates, "stopping" just means
        # the API won't be called until explicitly requested again
        return jsonify({
            "success": True,
            "message": "BTTS monitoring uses event-driven updates - no persistent monitoring to stop",
            "status": "EVENT_DRIVEN",
            "note": "Live scores are fetched on-demand when endpoints are called"
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/btts-reset', methods=['POST'])
def reset_btts_detector():
    """API endpoint to reset BTTS detector state."""
    try:
        if SOFASCORE_AVAILABLE and sofascore_api:
            # Clear Sofascore cache and reset statistics
            sofascore_api.clear_cache()
            sofascore_api.reset_monthly_usage()

            return jsonify({
                "success": True,
                "message": "BTTS detector state reset successfully",
                "status": "RESET",
                "actions_performed": ["cache_cleared", "monthly_usage_reset"]
            })
        else:
            return jsonify({
                "success": True,
                "message": "BTTS detector not available - no state to reset",
                "status": "NOT_AVAILABLE"
            })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

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

        # Get matches from enhanced BBC scraper
        if BBCSportScraper is None:
            return jsonify({
                "success": False,
                "error": "BBC scraper not available",
                "last_updated": datetime.now().isoformat()
            }), 500

        scraper = BBCSportScraper()
        scraper_result = scraper.scrape_saturday_3pm_fixtures()

        # Filter to only selected matches
        all_bbc_matches = scraper_result.get("matches_3pm", [])
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
        return jsonify({
            "success": False,
            "error": f"Error getting BBC fixtures: {str(e)}",
            "last_updated": datetime.now().isoformat()
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
        return jsonify({
            "success": False,
            "error": f"Error getting BBC live scores: {str(e)}",
            "last_updated": datetime.now().isoformat()
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

        # Get both fixtures and live scores for the date
        if BBCSportScraper is None:
            return jsonify({
                "success": False,
                "error": "BBC scraper not available",
                "last_updated": datetime.now().isoformat()
            }), 500

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

        return jsonify({
            "success": True,
            "date": date,
            "fixtures": fixtures_result,
            "live_scores": live_result,
            "total_matches": len(all_matches),
            "last_updated": datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Error getting BBC matches for date: {str(e)}",
            "last_updated": datetime.now().isoformat()
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
                "completion_percentage": max(0, min(100, int((selected_count / len(SELECTORS)) * 100))) if len(SELECTORS) > 0 else 0
            },
            "last_updated": datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Error getting tracker data: {str(e)}",
            "last_updated": datetime.now().isoformat()
        }), 500

# ===== BTTS TEST MODE API ENDPOINTS =====

def get_test_scenarios():
    """Generate various test scenarios for BTTS testing."""
    base_matches = {
        "Glynny": {
            "sofascore_id": 1234567,
            "home_team": "Manchester City",
            "away_team": "Everton",
            "home_score": 0,
            "away_score": 0,
            "status": "not_started",
            "btts_detected": False,
            "league": "Premier League",
            "last_updated": datetime.now().isoformat()
        },
        "Eamonn Bone": {
            "sofascore_id": 1234568,
            "home_team": "Hull City",
            "away_team": "Charlton Athletic",
            "home_score": 0,
            "away_score": 0,
            "status": "not_started",
            "btts_detected": False,
            "league": "Championship",
            "last_updated": datetime.now().isoformat()
        },
        "Mickey D": {
            "sofascore_id": 1234569,
            "home_team": "Burnley",
            "away_team": "Leeds United",
            "home_score": 0,
            "away_score": 0,
            "status": "not_started",
            "btts_detected": False,
            "league": "Championship",
            "last_updated": datetime.now().isoformat()
        },
        "Rob Carney": {
            "sofascore_id": 1234570,
            "home_team": "St. Mirren",
            "away_team": "Aberdeen",
            "home_score": 0,
            "away_score": 0,
            "status": "not_started",
            "btts_detected": False,
            "league": "Scottish Premiership",
            "last_updated": datetime.now().isoformat()
        },
        "Steve H": {
            "sofascore_id": 1234571,
            "home_team": "Shrewsbury Town",
            "away_team": "Cambridge United",
            "home_score": 0,
            "away_score": 0,
            "status": "not_started",
            "btts_detected": False,
            "league": "League One",
            "last_updated": datetime.now().isoformat()
        },
        "Danny": {
            "sofascore_id": 1234572,
            "home_team": "Derby County",
            "away_team": "Queens Park Rangers",
            "home_score": 0,
            "away_score": 0,
            "status": "not_started",
            "btts_detected": False,
            "league": "Championship",
            "last_updated": datetime.now().isoformat()
        },
        "Eddie Lee": {
            "sofascore_id": 1234573,
            "home_team": "Burton Albion",
            "away_team": "Bolton Wanderers",
            "home_score": 0,
            "away_score": 0,
            "status": "not_started",
            "btts_detected": False,
            "league": "League One",
            "last_updated": datetime.now().isoformat()
        },
        "Fran Radar": {
            "sofascore_id": 1234574,
            "home_team": "Forfar Athletic",
            "away_team": "Clyde",
            "home_score": 0,
            "away_score": 0,
            "status": "not_started",
            "btts_detected": False,
            "league": "Scottish League Two",
            "last_updated": datetime.now().isoformat()
        }
    }

    scenarios = {
        "all-pending": {
            "name": "All Pending",
            "description": "All matches not started, scores 0-0",
            "matches": base_matches
        },
        "mixed-results": {
            "name": "Mixed Results",
            "description": "Mix of BTTS success, failures, and pending",
            "matches": {
                **base_matches,
                "Glynny": { **base_matches["Glynny"], "home_score": 2, "away_score": 1, "status": "finished", "btts_detected": True },
                "Eamonn Bone": { **base_matches["Eamonn Bone"], "home_score": 1, "away_score": 0, "status": "finished", "btts_detected": False },
                "Mickey D": { **base_matches["Mickey D"], "home_score": 1, "away_score": 1, "status": "live", "btts_detected": True },
                "Rob Carney": { **base_matches["Rob Carney"], "home_score": 0, "away_score": 0, "status": "live" }
            }
        },
        "early-btts": {
            "name": "Early BTTS",
            "description": "BTTS detected early in matches",
            "matches": {
                **base_matches,
                "Glynny": { **base_matches["Glynny"], "home_score": 1, "away_score": 1, "status": "live", "btts_detected": True },
                "Eamonn Bone": { **base_matches["Eamonn Bone"], "home_score": 1, "away_score": 1, "status": "live", "btts_detected": True },
                "Mickey D": { **base_matches["Mickey D"], "home_score": 0, "away_score": 1, "status": "live" },
                "Rob Carney": { **base_matches["Rob Carney"], "home_score": 1, "away_score": 0, "status": "live" }
            }
        },
        "late-failures": {
            "name": "Late Failures",
            "description": "Matches finishing without BTTS",
            "matches": {
                **base_matches,
                "Glynny": { **base_matches["Glynny"], "home_score": 2, "away_score": 0, "status": "finished", "btts_detected": False },
                "Eamonn Bone": { **base_matches["Eamonn Bone"], "home_score": 0, "away_score": 1, "status": "finished", "btts_detected": False },
                "Mickey D": { **base_matches["Mickey D"], "home_score": 3, "away_score": 0, "status": "finished", "btts_detected": False },
                "Rob Carney": { **base_matches["Rob Carney"], "home_score": 0, "away_score": 0, "status": "finished", "btts_detected": False }
            }
        },
        "halftime-scores": {
            "name": "Halftime Scores",
            "description": "Matches at halftime with various scores",
            "matches": {
                **base_matches,
                "Glynny": { **base_matches["Glynny"], "home_score": 1, "away_score": 0, "status": "first_half" },
                "Eamonn Bone": { **base_matches["Eamonn Bone"], "home_score": 0, "away_score": 1, "status": "first_half" },
                "Mickey D": { **base_matches["Mickey D"], "home_score": 1, "away_score": 1, "status": "first_half", "btts_detected": True },
                "Rob Carney": { **base_matches["Rob Carney"], "home_score": 0, "away_score": 0, "status": "first_half" }
            }
        },
        "live-action": {
            "name": "Live Action",
            "description": "Multiple live matches with goals",
            "matches": {
                **base_matches,
                "Glynny": { **base_matches["Glynny"], "home_score": 2, "away_score": 1, "status": "live", "btts_detected": True },
                "Eamonn Bone": { **base_matches["Eamonn Bone"], "home_score": 1, "away_score": 2, "status": "live", "btts_detected": True },
                "Mickey D": { **base_matches["Mickey D"], "home_score": 0, "away_score": 1, "status": "live" },
                "Rob Carney": { **base_matches["Rob Carney"], "home_score": 1, "away_score": 0, "status": "live" },
                "Steve H": { **base_matches["Steve H"], "home_score": 1, "away_score": 1, "status": "live", "btts_detected": True }
            }
        },
        "random": {
            "name": "Random Scenario",
            "description": "Randomly generated realistic scenario",
            "matches": {}
        }
    }

    # Generate random scenario if requested
    if "random" in scenarios:
        import random
        random_matches = {}
        for selector, match_data in base_matches.items():
            # Randomly assign scores and status
            status_options = ["not_started", "live", "finished", "first_half"]
            status = random.choice(status_options)

            if status == "not_started":
                home_score, away_score = 0, 0
            elif status == "finished":
                home_score = random.randint(0, 4)
                away_score = random.randint(0, 4)
            else:  # live or halftime
                home_score = random.randint(0, 3)
                away_score = random.randint(0, 3)

            random_matches[selector] = {
                **match_data,
                "home_score": home_score,
                "away_score": away_score,
                "status": status,
                "btts_detected": home_score > 0 and away_score > 0
            }

        scenarios["random"]["matches"] = random_matches

    return scenarios

@app.route('/api/btts-test-scenarios')
def get_btts_test_scenarios():
    """API endpoint to get test scenarios for BTTS testing."""
    try:
        scenario_name = request.args.get('scenario', 'all-pending')
        scenarios = get_test_scenarios()

        if scenario_name not in scenarios:
            return jsonify({
                "error": f"Unknown scenario: {scenario_name}",
                "available_scenarios": list(scenarios.keys())
            }), 400

        scenario_data = scenarios[scenario_name]

        # Calculate statistics
        matches = scenario_data["matches"]
        btts_detected = sum(1 for match in matches.values() if match['btts_detected'])
        btts_pending = sum(1 for match in matches.values() if match['status'] in ['live', 'not_started', 'first_half'])
        btts_failed = sum(1 for match in matches.values() if match['status'] == 'finished' and not match['btts_detected'])

        return jsonify({
            "status": "TEST_MODE",
            "message": f"Test scenario: {scenario_data['description']}",
            "scenario": scenario_name,
            "matches": matches,
            "statistics": {
                "total_matches_tracked": len(matches),
                "btts_detected": btts_detected,
                "btts_pending": btts_pending,
                "btts_failed": btts_failed,
                "last_update": datetime.now().isoformat(),
                "sofascore_api_available": False,
                "api_calls_used": 0,
                "api_calls_target": "0 (Test Mode)"
            },
            "last_updated": datetime.now().isoformat(),
            "sofascore_integration": {
                "enabled": False,
                "cache_hit_rate": 0,
                "events_detected": len(matches)
            }
        })

    except Exception as e:
        return jsonify({
            "error": f"Error getting test scenarios: {str(e)}",
            "status": "ERROR",
            "last_updated": datetime.now().isoformat()
        }), 500

@app.route('/api/btts-test-trigger-btts', methods=['POST'])
def trigger_btts_test():
    """API endpoint to manually trigger BTTS for testing."""
    try:
        data = request.get_json()
        selector = data.get('selector')
        action = data.get('action', 'trigger_btts')

        # Get current test data
        scenarios = get_test_scenarios()
        current_matches = scenarios['all-pending']['matches'].copy()

        if action == 'trigger_all_btts':
            # Trigger BTTS for all selectors
            for sel in current_matches:
                current_matches[sel] = {
                    **current_matches[sel],
                    "home_score": 1,
                    "away_score": 1,
                    "status": "live",
                    "btts_detected": True,
                    "last_updated": datetime.now().isoformat()
                }
        elif selector and selector in current_matches:
            # Trigger BTTS for specific selector
            current_matches[selector] = {
                **current_matches[selector],
                "home_score": 1,
                "away_score": 1,
                "status": "live",
                "btts_detected": True,
                "last_updated": datetime.now().isoformat()
            }
        else:
            return jsonify({
                "success": False,
                "error": f"Selector '{selector}' not found"
            }), 404

        # Calculate updated statistics
        btts_detected = sum(1 for match in current_matches.values() if match['btts_detected'])
        btts_pending = sum(1 for match in current_matches.values() if match['status'] in ['live', 'not_started'])
        btts_failed = sum(1 for match in current_matches.values() if match['status'] == 'finished' and not match['btts_detected'])

        return jsonify({
            "success": True,
            "message": f"BTTS {'triggered for all' if action == 'trigger_all_btts' else f'triggered for {selector}'}",
            "match_data" if selector else "matches_data": current_matches[selector] if selector and selector in current_matches else current_matches,
            "statistics": {
                "total_matches_tracked": len(current_matches),
                "btts_detected": btts_detected,
                "btts_pending": btts_pending,
                "btts_failed": btts_failed,
                "last_update": datetime.now().isoformat()
            }
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/btts-test-update-score', methods=['POST'])
def update_score_test():
    """API endpoint to update scores for testing."""
    try:
        data = request.get_json()
        selector = data.get('selector')
        team = data.get('team')  # 'home' or 'away'
        delta = data.get('delta', 0)  # Score change (+1 or -1)
        action = data.get('action', 'update_score')

        # Get current test data
        scenarios = get_test_scenarios()
        current_matches = scenarios['all-pending']['matches'].copy()

        if action == 'reset_all':
            # Reset all scores to 0-0
            for sel in current_matches:
                current_matches[sel] = {
                    **current_matches[sel],
                    "home_score": 0,
                    "away_score": 0,
                    "status": "not_started",
                    "btts_detected": False,
                    "last_updated": datetime.now().isoformat()
                }
        elif selector and selector in current_matches and team in ['home', 'away']:
            # Update specific selector's score
            current_score = current_matches[selector][f'{team}_score']
            new_score = max(0, current_score + delta)  # Don't go below 0

            # Update status to live if score changes
            new_status = "live" if new_score > 0 else current_matches[selector]["status"]

            current_matches[selector] = {
                **current_matches[selector],
                f"{team}_score": new_score,
                "status": new_status,
                "btts_detected": current_matches[selector]["home_score"] > 0 and current_matches[selector]["away_score"] > 0,
                "last_updated": datetime.now().isoformat()
            }
        else:
            return jsonify({
                "success": False,
                "error": f"Invalid parameters: selector='{selector}', team='{team}', delta={delta}"
            }), 400

        # Calculate updated statistics
        btts_detected = sum(1 for match in current_matches.values() if match['btts_detected'])
        btts_pending = sum(1 for match in current_matches.values() if match['status'] in ['live', 'not_started'])
        btts_failed = sum(1 for match in current_matches.values() if match['status'] == 'finished' and not match['btts_detected'])

        return jsonify({
            "success": True,
            "message": f"Score {'reset for all' if action == 'reset_all' else f'updated for {selector} ({team} {delta:+d})'}",
            "match_data" if selector else "matches_data": current_matches[selector] if selector and selector in current_matches else current_matches,
            "statistics": {
                "total_matches_tracked": len(current_matches),
                "btts_detected": btts_detected,
                "btts_pending": btts_pending,
                "btts_failed": btts_failed,
                "last_update": datetime.now().isoformat()
            }
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# ===== HEALTH CHECK AND MONITORING =====

@app.route('/health')
def health_check():
    """Health check endpoint for monitoring"""
    try:
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0',
            'services': {
                'bbc_scraper': config.ENABLE_BBC_SCRAPER,
                'sofascore_api': SOFASCORE_AVAILABLE,
                'btts_detector': BTTS_DETECTOR_AVAILABLE,
                'data_manager': True
            }
        }

        # Check if critical services are available
        critical_issues = []
        if config.ENABLE_BBC_SCRAPER and not data_manager:
            critical_issues.append('DataManager not available')

        if config.ENABLE_SOFA_SCORE_API and not SOFASCORE_AVAILABLE:
            critical_issues.append('Sofascore API not available')

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
            'timestamp': datetime.now().isoformat()
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

        # Add Sofascore API metrics if available
        if SOFASCORE_AVAILABLE and sofascore_api:
            try:
                usage_stats = sofascore_api.get_usage_stats()
                cache_analytics = sofascore_api.get_cache_analytics()
                metrics_data['api_usage'] = usage_stats
                metrics_data['cache_stats'] = cache_analytics
            except Exception as e:
                app.logger.warning(f"Could not get Sofascore metrics: {e}")

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

    if config.DEBUG:
        # Development server
        app.run(
            debug=config.DEBUG,
            host=config.HOST,
            port=config.PORT,
            use_reloader=False  # Disable reloader in production-like environment
        )
    else:
        # Production-like server (still using Flask dev server for now)
        # In production, use gunicorn: gunicorn --config gunicorn.conf.py app:app
        app.run(
            debug=False,
            host=config.HOST,
            port=config.PORT,
            use_reloader=False
        )