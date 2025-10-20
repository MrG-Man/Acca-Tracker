"""
Enhanced Data Storage & Caching System for Football Predictions
Central coordinator for all data operations with validation and backup features
"""

import json
import os
import shutil
import threading
import gzip
import pickle
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
import time

class DataManager:
    """
    Central data management class for football predictions application.

    Handles:
    - Weekly selection storage and retrieval
    - BBC scraper result caching with 24-hour TTL
    - Data validation and integrity checks
    - Automated backup and recovery
    - Performance optimized read/write operations
    """

    def __init__(self, base_path: str = "data"):
        """
        Initialize DataManager with base data path and fallback options.

        Args:
            base_path: Base directory for all data operations
        """
        self.base_path = base_path
        self.selections_path = os.path.join(base_path, "selections")
        self.fixtures_path = os.path.join(base_path, "fixtures")
        self.backups_path = os.path.join(base_path, "backups")

        # Setup logging first (before directory creation)
        self.logger = self._setup_logging()

        # Create necessary directories with fallback options
        self._ensure_directories_with_fallback()

        # Track initialization status for production debugging
        self.initialization_errors = []

        # Cache TTL for BBC fixtures - MORE AGGRESSIVE (was 24 hours)
        self.bbc_cache_ttl = timedelta(hours=72)  # 3 days for BBC fixtures

        # Extended cache for selections (was not cached in memory before)
        self.selections_cache_ttl = timedelta(hours=12)  # 12 hours for selections

        # Performance optimizations
        self._file_locks = {}  # File-based locking for thread safety
        self._memory_cache = {}  # In-memory cache for frequently accessed data
        self._cache_timestamps = {}  # Track cache entry times
        self._memory_cache_ttl = timedelta(minutes=5)  # Memory cache TTL
        self._lock = threading.RLock()  # General purpose lock

        # Performance monitoring
        self._operation_stats = {
            "reads": 0,
            "writes": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_read_time": 0.0,
            "total_write_time": 0.0
        }

        # File size threshold for compression (1MB)
        self.compression_threshold = 1024 * 1024

    def _ensure_directories(self):
        """Create necessary data directories if they don't exist."""
        directories = [
            self.selections_path,
            self.fixtures_path,
            self.backups_path
        ]

        for directory in directories:
            try:
                os.makedirs(directory, exist_ok=True)
                self.logger.debug(f"Created/verified directory: {directory}")
            except Exception as e:
                self.logger.error(f"Failed to create directory {directory}: {e}")
                raise

    def _ensure_directories_with_fallback(self):
        """Create necessary data directories with fallback options for production environments."""
        directories = [
            self.selections_path,
            self.fixtures_path,
            self.backups_path
        ]

        # Try primary locations first
        success = True
        for directory in directories:
            try:
                os.makedirs(directory, exist_ok=True)
                self.logger.debug(f"Created/verified directory: {directory}")
            except Exception as e:
                self.logger.error(f"Failed to create directory {directory}: {e}")
                self.initialization_errors.append(f"Directory creation failed for {directory}: {e}")
                success = False

        # If primary locations failed, try fallback locations
        if not success:
            self.logger.warning("Primary directory creation failed, trying fallback locations...")
            self._try_fallback_directories()

    def _try_fallback_directories(self):
        """Try alternative directory locations for production environments."""
        fallback_paths = [
            "/tmp/football_data",
            "/tmp/app_data",
            "./tmp_data",
            "/var/tmp/football_data"
        ]

        for fallback_base in fallback_paths:
            try:
                self.logger.info(f"Trying fallback directory: {fallback_base}")

                # Update paths to use fallback location
                self.base_path = fallback_base
                self.selections_path = os.path.join(fallback_base, "selections")
                self.fixtures_path = os.path.join(fallback_base, "fixtures")
                self.backups_path = os.path.join(fallback_base, "backups")

                # Try to create fallback directories
                directories = [self.selections_path, self.fixtures_path, self.backups_path]
                for directory in directories:
                    os.makedirs(directory, exist_ok=True)

                self.logger.info(f"Successfully created fallback directories in {fallback_base}")
                self.initialization_errors.append(f"Using fallback directories: {fallback_base}")
                return True

            except Exception as e:
                self.logger.warning(f"Fallback directory {fallback_base} also failed: {e}")
                self.initialization_errors.append(f"Fallback {fallback_base} failed: {e}")
                continue

        # If all fallbacks failed, log critical error but don't crash
        critical_error = "All directory creation attempts failed. Application may not function correctly."
        self.logger.critical(critical_error)
        self.initialization_errors.append(critical_error)
        return False

    def _setup_logging(self) -> logging.Logger:
        """Setup logging for data operations."""
        logger = logging.getLogger("DataManager")
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def _get_file_lock(self, filepath: str) -> threading.RLock:
        """Get or create a file-specific lock for thread safety."""
        if filepath not in self._file_locks:
            self._file_locks[filepath] = threading.RLock()
        return self._file_locks[filepath]

    def _get_memory_cache_key(self, operation: str, *args) -> str:
        """Generate a key for memory caching."""
        key_parts = [operation] + [str(arg) for arg in args]
        return "|".join(key_parts)

    def _get_memory_cache(self, key: str) -> Optional[Any]:
        """Get data from memory cache if not expired."""
        with self._lock:
            if key in self._memory_cache:
                cache_time = self._cache_timestamps.get(key, datetime.min)
                if datetime.now() - cache_time < self._memory_cache_ttl:
                    self._operation_stats["cache_hits"] += 1
                    return self._memory_cache[key]
                else:
                    # Cache expired
                    del self._memory_cache[key]
                    del self._cache_timestamps[key]

            self._operation_stats["cache_misses"] += 1
            return None

    def _set_memory_cache(self, key: str, data: Any):
        """Store data in memory cache."""
        with self._lock:
            self._memory_cache[key] = data
            self._cache_timestamps[key] = datetime.now()

    def _compress_data(self, data: str) -> bytes:
        """Compress data using gzip."""
        return gzip.compress(data.encode('utf-8'), compresslevel=6)

    def _decompress_data(self, compressed_data: bytes) -> str:
        """Decompress gzip data."""
        return gzip.decompress(compressed_data).decode('utf-8')

    def _should_compress_file(self, filepath: str) -> bool:
        """Check if file should be compressed based on size."""
        try:
            return os.path.getsize(filepath) > self.compression_threshold
        except (OSError, FileNotFoundError):
            return False

    def _save_json_file(self, filepath: str, data: Dict[str, Any], use_compression: bool = False) -> bool:
        """Save JSON data to file with optional compression and performance monitoring."""
        start_time = time.time()

        try:
            # Get file lock for thread safety
            with self._get_file_lock(filepath):
                if use_compression:
                    json_str = json.dumps(data, indent=2, ensure_ascii=False)
                    compressed_data = self._compress_data(json_str)

                    with open(filepath + '.gz', 'wb') as f:
                        f.write(compressed_data)
                else:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)

            # Update performance stats
            end_time = time.time()
            self._operation_stats["writes"] += 1
            self._operation_stats["total_write_time"] += (end_time - start_time)

            return True

        except Exception as e:
            self.logger.error(f"Error saving JSON file {filepath}: {str(e)}")
            return False

    def _load_json_file(self, filepath: str) -> Optional[Dict[str, Any]]:
        """Load JSON data from file with optional decompression and performance monitoring."""
        start_time = time.time()

        try:
            # Get file lock for thread safety
            with self._get_file_lock(filepath):
                # Check if compressed version exists
                compressed_file = filepath + '.gz'

                if os.path.exists(compressed_file):
                    with open(compressed_file, 'rb') as f:
                        compressed_data = f.read()
                    json_str = self._decompress_data(compressed_data)
                    data = json.loads(json_str)
                else:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)

            # Update performance stats
            end_time = time.time()
            self._operation_stats["reads"] += 1
            self._operation_stats["total_read_time"] += (end_time - start_time)

            return data

        except Exception as e:
            self.logger.error(f"Error loading JSON file {filepath}: {str(e)}")
            return None

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for monitoring."""
        with self._lock:
            stats = self._operation_stats.copy()

            # Calculate averages
            if stats["reads"] > 0:
                stats["avg_read_time"] = stats["total_read_time"] / stats["reads"]
            else:
                stats["avg_read_time"] = 0.0

            if stats["writes"] > 0:
                stats["avg_write_time"] = stats["total_write_time"] / stats["writes"]
            else:
                stats["avg_write_time"] = 0.0

            # Cache performance
            total_requests = stats["cache_hits"] + stats["cache_misses"]
            if total_requests > 0:
                stats["cache_hit_rate"] = stats["cache_hits"] / total_requests
            else:
                stats["cache_hit_rate"] = 0.0

            # Memory cache info
            stats["memory_cache_size"] = len(self._memory_cache)
            stats["active_file_locks"] = len(self._file_locks)

            return stats

    def clear_memory_cache(self):
        """Clear the memory cache to free up memory."""
        with self._lock:
            self._memory_cache.clear()
            self._cache_timestamps.clear()
            self.logger.info("Memory cache cleared")

    def cleanup_locks(self):
        """Clean up unused file locks to prevent memory leaks."""
        with self._lock:
            # Remove locks for files that no longer exist
            files_to_remove = []
            for filepath in self._file_locks:
                if not os.path.exists(filepath) and not os.path.exists(filepath + '.gz'):
                    files_to_remove.append(filepath)

            for filepath in files_to_remove:
                del self._file_locks[filepath]

            if files_to_remove:
                self.logger.info(f"Cleaned up {len(files_to_remove)} unused file locks")

    def save_weekly_selections(self, selections_data: Dict[str, Any], date: Optional[str] = None) -> bool:
        """
        Save weekly match selections to JSON file with performance optimizations.

        Args:
            selections_data: Dictionary containing match selections
            date: Date string in YYYY-MM-DD format. If None, uses current date.

        Returns:
            bool: True if saved successfully, False otherwise
        """
        try:
            if date is None:
                date = datetime.now().strftime("%Y-%m-%d")

            # Validate selections data
            if not self.validate_selections(selections_data):
                self.logger.error(f"Invalid selections data for date {date}")
                return False

            filename = f"week_{date}.json"
            filepath = os.path.join(self.selections_path, filename)

            # Check memory cache first
            cache_key = self._get_memory_cache_key("selections", date)
            cached_data = self._get_memory_cache(cache_key)
            if cached_data == selections_data:
                self.logger.debug(f"Selections unchanged for {date}, skipping save")
                return True

            # Add metadata
            data_to_save = {
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "version": "1.0",
                    "date": date
                },
                "selections": selections_data
            }

            # Determine if compression is needed
            temp_json = json.dumps(data_to_save, indent=2, ensure_ascii=False)
            use_compression = len(temp_json.encode('utf-8')) > self.compression_threshold

            # Save using optimized method
            if not self._save_json_file(filepath, data_to_save, use_compression):
                return False

            # Update memory cache
            self._set_memory_cache(cache_key, selections_data)

            self.logger.info(f"Weekly selections saved successfully for {date}")
            return True

        except Exception as e:
            self.logger.error(f"Error saving weekly selections for {date}: {str(e)}")
            return False

    def load_weekly_selections(self, date: str) -> Optional[Dict[str, Any]]:
        """
        Load weekly match selections for a specific date with performance optimizations.

        Args:
            date: Date string in YYYY-MM-DD format

        Returns:
            Dictionary containing selections or None if not found/error
        """
        try:
            # Check memory cache first
            cache_key = self._get_memory_cache_key("selections", date)
            cached_data = self._get_memory_cache(cache_key)
            if cached_data:
                self.logger.debug(f"Returning cached selections for {date}")
                return cached_data

            filename = f"week_{date}.json"
            filepath = os.path.join(self.selections_path, filename)

            if not os.path.exists(filepath) and not os.path.exists(filepath + '.gz'):
                self.logger.warning(f"No selections file found for date {date}")
                return None

            # Load using optimized method
            data = self._load_json_file(filepath)
            if data is None:
                return None

            # Validate loaded data
            selections = data.get("selections", {})
            if not self.validate_selections(selections):
                self.logger.error(f"Invalid selections data in file for date {date}")
                return None

            # Update memory cache
            self._set_memory_cache(cache_key, selections)

            self.logger.info(f"Weekly selections loaded successfully for {date}")
            return selections

        except Exception as e:
            self.logger.error(f"Error loading weekly selections for {date}: {str(e)}")
            return None

    def cache_bbc_fixtures(self, fixtures_data: List[Dict[str, Any]], date: Optional[str] = None) -> bool:
        """
        Cache BBC scraper results with 24-hour TTL and performance optimizations.

        Args:
            fixtures_data: List of fixture dictionaries from BBC scraper
            date: Date string in YYYY-MM-DD format. If None, uses current date.

        Returns:
            bool: True if cached successfully, False otherwise
        """
        try:
            if date is None:
                date = datetime.now().strftime("%Y-%m-%d")

            filename = f"bbc_cache_{date}.json"
            filepath = os.path.join(self.fixtures_path, filename)

            # Check memory cache first
            cache_key = self._get_memory_cache_key("bbc_fixtures", date)
            cached_data = self._get_memory_cache(cache_key)
            if cached_data == fixtures_data:
                self.logger.debug(f"BBC fixtures unchanged for {date}, skipping cache")
                return True

            # Add cache metadata
            cache_data = {
                "metadata": {
                    "cached_at": datetime.now().isoformat(),
                    "expires_at": (datetime.now() + self.bbc_cache_ttl).isoformat(),
                    "ttl_hours": 24,
                    "date": date
                },
                "fixtures": fixtures_data
            }

            # Determine if compression is needed
            temp_json = json.dumps(cache_data, indent=2, ensure_ascii=False)
            use_compression = len(temp_json.encode('utf-8')) > self.compression_threshold

            # Save using optimized method
            if not self._save_json_file(filepath, cache_data, use_compression):
                return False

            # Update memory cache
            self._set_memory_cache(cache_key, fixtures_data)

            self.logger.info(f"BBC fixtures cached successfully for {date}")
            return True

        except Exception as e:
            self.logger.error(f"Error caching BBC fixtures for {date}: {str(e)}")
            return False

    def get_bbc_fixtures(self, date: str, league: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieve cached BBC fixtures for a specific date with enhanced validation.

        Args:
            date: Date string in YYYY-MM-DD format
            league: Optional league name for league-specific caching

        Returns:
            List of fixture dictionaries or None if not found/expired
        """
        try:
            if league:
                # Use league-specific cache file
                filename = f"bbc_cache_{date}_{league.replace(' ', '_').lower()}.json"
            else:
                # Use generic cache file for backward compatibility
                filename = f"bbc_cache_{date}.json"
            filepath = os.path.join(self.fixtures_path, filename)

            if not os.path.exists(filepath) and not os.path.exists(filepath + '.gz'):
                self.logger.warning(f"No BBC cache file found for date {date}")
                return None

            # Load using optimized method
            cache_data = self._load_json_file(filepath)
            if cache_data is None:
                return None

            # Enhanced cache validation
            metadata = cache_data.get("metadata", {})

            # Check if cache has expired
            expires_at = datetime.fromisoformat(metadata["expires_at"])
            if datetime.now() > expires_at:
                self.logger.info(f"BBC cache expired for date {date}")
                self._cleanup_expired_cache(filepath)
                return None

            # Check if target date is reasonable (not too far in future/past)
            try:
                target_date = datetime.strptime(date, "%Y-%m-%d")
                now = datetime.now()

                # Reject cache if target date is more than 14 days in future
                if target_date > now + timedelta(days=14):
                    self.logger.warning(f"Cache date {date} is too far in future - rejecting cache")
                    self._cleanup_expired_cache(filepath)
                    return None

                # Reject cache if target date is more than 7 days in past
                if target_date < now - timedelta(days=7):
                    self.logger.warning(f"Cache date {date} is too old - rejecting cache")
                    self._cleanup_expired_cache(filepath)
                    return None

            except ValueError:
                self.logger.warning(f"Invalid date format in cache: {date}")
                self._cleanup_expired_cache(filepath)
                return None

            fixtures = cache_data.get("fixtures", [])

            # Validate fixture data structure
            if not self._validate_fixture_data(fixtures):
                self.logger.warning(f"Invalid fixture data structure for {date}")
                self._cleanup_expired_cache(filepath)
                return None

            # Update memory cache only if all validations pass
            cache_key = self._get_memory_cache_key("bbc_fixtures", date)
            self._set_memory_cache(cache_key, fixtures)

            self.logger.info(f"BBC fixtures retrieved from validated cache for {date}")
            return fixtures

        except Exception as e:
            self.logger.error(f"Error retrieving BBC fixtures for {date}: {str(e)}")
            return None

    def _cleanup_expired_cache(self, filepath: str):
        """Clean up expired cache files."""
        with self._get_file_lock(filepath):
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
                if os.path.exists(filepath + '.gz'):
                    os.remove(filepath + '.gz')
            except OSError:
                pass  # File may already be removed

    def _validate_fixture_data(self, fixtures: List[Dict[str, Any]]) -> bool:
        """Validate fixture data structure."""
        if not isinstance(fixtures, list):
            return False

        for fixture in fixtures:
            if not isinstance(fixture, dict):
                return False

            # Required fields for each fixture
            required_fields = ["league", "home_team", "away_team", "kickoff"]
            for field in required_fields:
                if field not in fixture:
                    return False

            # Validate field types and values
            if not isinstance(fixture["league"], str) or len(fixture["league"]) == 0:
                return False
            if not isinstance(fixture["home_team"], str) or len(fixture["home_team"]) == 0:
                return False
            if not isinstance(fixture["away_team"], str) or len(fixture["away_team"]) == 0:
                return False
            if not isinstance(fixture["kickoff"], str) or fixture["kickoff"] not in ["15:00"]:
                return False

        return True

    def validate_selections(self, selections: Dict[str, Any]) -> bool:
        """
        Validate selections data structure and content.

        Args:
            selections: Dictionary containing match selections

        Returns:
            bool: True if valid, False otherwise
        """
        try:
            if not isinstance(selections, dict):
                return False

            # Check each match selection
            for match_id, selection in selections.items():
                if not isinstance(selection, dict):
                    return False

                # Required fields for each selection
                required_fields = ["home_team", "away_team", "prediction", "confidence"]
                for field in required_fields:
                    if field not in selection:
                        return False

                # Validate prediction values
                valid_predictions = ["HOME", "AWAY", "DRAW", "BTTS_YES", "BTTS_NO", "TBD"]
                if selection.get("prediction") not in valid_predictions:
                    return False

                # Validate confidence (should be 1-10)
                confidence = selection.get("confidence")
                if not isinstance(confidence, int) or confidence < 1 or confidence > 10:
                    return False

            return True

        except Exception as e:
            self.logger.error(f"Error validating selections: {str(e)}")
            return False

    def backup_data(self) -> bool:
        """
        Create a backup of all data files.

        Returns:
            bool: True if backup successful, False otherwise
        """
        try:
            # Create backup directory with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = os.path.join(self.backups_path, f"backup_{timestamp}")

            # Copy all data directories
            directories_to_backup = [
                self.selections_path,
                self.fixtures_path
            ]

            os.makedirs(backup_dir, exist_ok=True)

            for directory in directories_to_backup:
                if os.path.exists(directory):
                    dest_dir = os.path.join(backup_dir, os.path.basename(directory))
                    if os.path.exists(dest_dir):
                        shutil.rmtree(dest_dir)
                    shutil.copytree(directory, dest_dir)

            # Create backup metadata
            metadata = {
                "backup_date": datetime.now().isoformat(),
                "directories_backed_up": [os.path.basename(d) for d in directories_to_backup],
                "total_files": sum([len(files) for _, _, files in os.walk(backup_dir)])
            }

            metadata_path = os.path.join(backup_dir, "backup_metadata.json")
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)

            self.logger.info(f"Data backup created successfully: {backup_dir}")
            return True

        except Exception as e:
            self.logger.error(f"Error creating data backup: {str(e)}")
            return False

    def cleanup_old_backups(self, keep_days: int = 30) -> int:
        """
        Remove old backup directories older than specified days.

        Args:
            keep_days: Number of days to keep backups

        Returns:
            int: Number of backups removed
        """
        try:
            removed_count = 0
            cutoff_date = datetime.now() - timedelta(days=keep_days)

            for item in os.listdir(self.backups_path):
                backup_dir = os.path.join(self.backups_path, item)

                if os.path.isdir(backup_dir) and item.startswith("backup_"):
                    try:
                        # Extract timestamp from directory name
                        timestamp_str = item.replace("backup_", "")
                        backup_date = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")

                        if backup_date < cutoff_date:
                            shutil.rmtree(backup_dir)
                            removed_count += 1
                            self.logger.info(f"Removed old backup: {item}")

                    except ValueError:
                        # Skip directories with invalid timestamp format
                        continue

            if removed_count > 0:
                self.logger.info(f"Cleaned up {removed_count} old backups")
            return removed_count

        except Exception as e:
            self.logger.error(f"Error cleaning up old backups: {str(e)}")
            return 0

    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics for all data directories.

        Returns:
            Dictionary containing storage statistics
        """
        try:
            stats = {
                "selections": {"files": 0, "size": 0},
                "fixtures": {"files": 0, "size": 0},
                "backups": {"files": 0, "size": 0}
            }

            # Calculate selections stats
            if os.path.exists(self.selections_path):
                for file in os.listdir(self.selections_path):
                    filepath = os.path.join(self.selections_path, file)
                    if os.path.isfile(filepath):
                        stats["selections"]["files"] += 1
                        stats["selections"]["size"] += os.path.getsize(filepath)

            # Calculate fixtures stats
            if os.path.exists(self.fixtures_path):
                for file in os.listdir(self.fixtures_path):
                    filepath = os.path.join(self.fixtures_path, file)
                    if os.path.isfile(filepath):
                        stats["fixtures"]["files"] += 1
                        stats["fixtures"]["size"] += os.path.getsize(filepath)

            # Calculate backups stats
            if os.path.exists(self.backups_path):
                for file in os.listdir(self.backups_path):
                    filepath = os.path.join(self.backups_path, file)
                    if os.path.isfile(filepath):
                        stats["backups"]["files"] += 1
                        stats["backups"]["size"] += os.path.getsize(filepath)

            return stats

        except Exception as e:
            self.logger.error(f"Error getting storage stats: {str(e)}")
            return {}

    def optimize_performance(self):
        """Perform performance optimization tasks."""
        try:
            # Clean up old memory cache entries
            current_time = datetime.now()
            expired_keys = []

            with self._lock:
                for key, timestamp in self._cache_timestamps.items():
                    if current_time - timestamp > self._memory_cache_ttl:
                        expired_keys.append(key)

                for key in expired_keys:
                    self._memory_cache.pop(key, None)
                    self._cache_timestamps.pop(key, None)

            # Clean up unused file locks
            self.cleanup_locks()

            if expired_keys:
                self.logger.info(f"Cleaned up {len(expired_keys)} expired memory cache entries")

        except Exception as e:
            self.logger.error(f"Error during performance optimization: {str(e)}")

    def benchmark_operation(self, operation_func, *args, **kwargs):
        """Benchmark a data operation for performance monitoring."""
        start_time = time.time()

        try:
            result = operation_func(*args, **kwargs)
            success = True
        except Exception as e:
            result = None
            success = False
            self.logger.error(f"Benchmark operation failed: {str(e)}")

        end_time = time.time()
        duration = end_time - start_time

        self.logger.info(f"Operation benchmark: {duration:.4f}s, success: {success}")

        return result, duration, success

    def save_live_results(self, live_results_data: List[Dict[str, Any]]) -> bool:
        """
        Save live match results (BTTS, scores, etc.) to JSON file.

        Args:
            live_results_data: List of live result dictionaries

        Returns:
            bool: True if saved successfully, False otherwise
        """
        try:
            filename = "live_results.json"
            filepath = os.path.join(self.base_path, filename)

            # Add metadata
            data_to_save = {
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "version": "1.0",
                    "total_results": len(live_results_data)
                },
                "live_results": live_results_data
            }

            # Save using optimized method (no compression for live data)
            if not self._save_json_file(filepath, data_to_save, use_compression=False):
                return False

            self.logger.info(f"Live results saved successfully ({len(live_results_data)} results)")
            return True

        except Exception as e:
            self.logger.error(f"Error saving live results: {str(e)}")
            return False

    def load_live_results(self) -> Optional[List[Dict[str, Any]]]:
        """
        Load live match results from JSON file.

        Returns:
            List of live result dictionaries or None if not found/error
        """
        try:
            filename = "live_results.json"
            filepath = os.path.join(self.base_path, filename)

            if not os.path.exists(filepath) and not os.path.exists(filepath + '.gz'):
                self.logger.debug("No live results file found")
                return []

            # Load using optimized method
            data = self._load_json_file(filepath)
            if data is None:
                return []

            live_results = data.get("live_results", [])
            self.logger.info(f"Live results loaded successfully ({len(live_results)} results)")
            return live_results

        except Exception as e:
            self.logger.error(f"Error loading live results: {str(e)}")
            return []

    def add_live_result(self, result_data: Dict[str, Any]) -> bool:
        """
        Add a single live result to the live results file.

        Args:
            result_data: Dictionary containing live result data

        Returns:
            bool: True if added successfully, False otherwise
        """
        try:
            # Load existing results
            existing_results = self.load_live_results() or []

            # Add new result
            existing_results.append(result_data)

            # Save back to file
            return self.save_live_results(existing_results)

        except Exception as e:
            self.logger.error(f"Error adding live result: {str(e)}")
            return False

    def get_live_results_by_match(self, match_id: str) -> List[Dict[str, Any]]:
        """
        Get live results for a specific match.

        Args:
            match_id: Match identifier

        Returns:
            List of live results for the match
        """
        try:
            all_results = self.load_live_results()
            if all_results is None:
                return []
            return [result for result in all_results if result.get('match_id') == match_id]

        except Exception as e:
            self.logger.error(f"Error getting live results for match {match_id}: {str(e)}")
            return []

    def cleanup_old_live_results(self, keep_days: int = 7) -> int:
        """
        Remove live results older than specified days.

        Args:
            keep_days: Number of days to keep live results

        Returns:
            int: Number of results removed
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=keep_days)
            results = self.load_live_results()

            if not results:
                return 0

            # Filter out old results
            filtered_results = []
            removed_count = 0

            for result in results:
                detected_at_str = result.get('detected_at')
                if detected_at_str:
                    try:
                        detected_at = datetime.fromisoformat(detected_at_str.replace('Z', '+00:00'))
                        if detected_at > cutoff_date:
                            filtered_results.append(result)
                        else:
                            removed_count += 1
                    except ValueError:
                        # Keep results with invalid dates
                        filtered_results.append(result)
                else:
                    # Keep results without date
                    filtered_results.append(result)

            # Save filtered results back
            if removed_count > 0:
                self.save_live_results(filtered_results)
                self.logger.info(f"Cleaned up {removed_count} old live results")

            return removed_count

        except Exception as e:
            self.logger.error(f"Error cleaning up old live results: {str(e)}")
            return 0

# Global instance for easy importing
data_manager = DataManager()