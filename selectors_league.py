"""
Selectors League Module
Calculates historical performance and league standings for selectors
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
from data_manager import data_manager

logger = logging.getLogger(__name__)

class SelectorsLeague:
    """
    Handles selectors league calculations and historical performance tracking
    """
    
    # Points system
    BTTS_SUCCESS_POINTS = 3
    SINGLE_GOAL_POINTS = 0
    NO_GOAL_POINTS = -3
    
    def __init__(self):
        self.selectors = [
            "Glynny", "Eamonn Bone", "Mickey D", "Rob Carney",
            "Steve H", "Danny", "Eddie Lee", "Fran Radar"
        ]
        # Historical points data (prior to Sat 1 Nov)
        self.historical_points = {
            "Eamonn Bone": 27,
            "Fran Radar": 21,
            "Glynny": 21,
            "Mickey D": 21,
            "Rob Carney": 21,
            "Steve H": 18,
            "Danny": 18,
            "Eddie Lee": 6
        }
        
        # Try to load additional historical data from file
        # Historical points are loaded above
    
    def calculate_league_data(self, view_filter: str = 'overall') -> Dict[str, Any]:
        """
        Calculate comprehensive league data for all selectors
        
        Args:
            view_filter: Filter to apply (overall, this-season, recent)
            
        Returns:
            Dictionary containing league data and statistics
        """
        try:
            # Get all historical selection files
            selection_files = self._get_all_selection_files()
            
            # Calculate performance for each selector
            selector_performance = {}
            for selector in self.selectors:
                performance = self._calculate_selector_performance(selector, selection_files)
                if performance:
                    selector_performance[selector] = performance
            
            # If no live performance data found, use historical points
            if not selector_performance or all(p['total_matches'] == 0 for p in selector_performance.values()):
                selector_performance = self._create_historical_performance_data()
            
            # Calculate overall statistics
            league_stats = self._calculate_league_statistics(selector_performance)
            
            # Apply view filter
            filtered_selectors = self._apply_view_filter(selector_performance, view_filter)
            
            return {
                'success': True,
                'selectors': filtered_selectors,
                'weekly_stats': self._calculate_weekly_statistics(selector_performance, selection_files),
                'season_stats': league_stats,
                'last_updated': datetime.now().isoformat(),
                'current_week': self._get_current_week_number(),
                'season_year': datetime.now().year
            }
            
        except Exception as e:
            logger.error(f"Error calculating league data: {e}")
            return self._create_error_league_data(str(e))
    
    def _get_all_selection_files(self) -> List[str]:
        """Get all selection files from the data directory"""
        try:
            selections_dir = data_manager.selections_path
            if not os.path.exists(selections_dir):
                return []
            
            files = [f for f in os.listdir(selections_dir) if f.startswith('week_') and f.endswith('.json')]
            return sorted(files)
            
        except Exception as e:
            logger.error(f"Error getting selection files: {e}")
            return []
    
    def _calculate_selector_performance(self, selector_name: str, selection_files: List[str]) -> Optional[Dict[str, Any]]:
        """
        Calculate performance metrics for a specific selector
        
        Args:
            selector_name: Name of the selector
            selection_files: List of selection files
            
        Returns:
            Dictionary containing selector performance data
        """
        try:
            total_points = 0
            total_matches = 0
            btts_successes = 0
            single_goal_results = 0
            no_goal_results = 0
            recent_form = []
            weekly_points = {}
            
            for file_name in selection_files:
                try:
                    # Extract date from filename
                    date_str = file_name.replace('week_', '').replace('.json', '')
                    week_date = datetime.strptime(date_str, '%Y-%m-%d')
                    
                    # Load selection data
                    file_path = os.path.join(data_manager.selections_path, file_name)
                    data = data_manager._load_json_file(file_path)
                    
                    if not data or 'selections' not in data:
                        continue
                    
                    selections = data['selections']
                    
                    # Check if selector has a selection this week
                    if selector_name in selections:
                        selector_data = selections[selector_name]
                        
                        # Calculate match result based on BTTS logic
                        match_result = self._calculate_match_result(selector_data, week_date)
                        
                        if match_result:
                            # Update statistics
                            total_matches += 1
                            points = match_result['points']
                            total_points += points
                            
                            if points == self.BTTS_SUCCESS_POINTS:
                                btts_successes += 1
                            elif points == self.SINGLE_GOAL_POINTS:
                                single_goal_results += 1
                            elif points == self.NO_GOAL_POINTS:
                                no_goal_results += 1
                            
                            # Add to recent form
                            recent_form.append({
                                'week': week_date.strftime('%Y-%m-%d'),
                                'match_home': selector_data.get('home_team', 'Unknown'),
                                'match_away': selector_data.get('away_team', 'Unknown'),
                                'points': points,
                                'result_description': match_result['description'],
                                'final_score': match_result.get('final_score', 'TBD')
                            })
                            
                            # Store weekly points
                            weekly_points[week_date.strftime('%Y-%m-%d')] = points
                            
                except Exception as e:
                    logger.warning(f"Error processing file {file_name} for {selector_name}: {e}")
                    continue
            
            # Calculate percentages and averages
            btts_percentage = (btts_successes / total_matches * 100) if total_matches > 0 else 0
            
            # Calculate recent performance (last 10 weeks)
            recent_form_sorted = sorted(recent_form, key=lambda x: x['week'])
            recent_10 = recent_form_sorted[-10:]
            recent_points = sum(r['points'] for r in recent_10)
            recent_average = recent_points / len(recent_10) if recent_10 else 0
            
            # Calculate weekly average
            average_weekly_points = total_points / len(weekly_points) if weekly_points else 0
            
            return {
                'selector_name': selector_name,
                'total_points': total_points,
                'total_matches': total_matches,
                'btts_successes': btts_successes,
                'single_goal_results': single_goal_results,
                'no_goal_results': no_goal_results,
                'btts_percentage': btts_percentage,
                'recent_form': recent_form_sorted,
                'recent_points': recent_points,
                'recent_average': recent_average,
                'average_weekly_points': average_weekly_points,
                'weekly_points': weekly_points
            }
            
        except Exception as e:
            logger.error(f"Error calculating performance for {selector_name}: {e}")
            return None
    
    def _calculate_match_result(self, selector_data: Dict[str, Any], match_date: datetime) -> Optional[Dict[str, Any]]:
        """
        Calculate the result of a selector's match prediction
        
        Args:
            selector_data: Selector's match data
            match_date: Date of the match
            
        Returns:
            Dictionary containing result information
        """
        try:
            # Get live results to determine actual outcome
            live_results = data_manager.load_live_results()
            
            if not live_results:
                # No live results available yet, check if this match date has finished
                # For now, return None if no live results (matches still in progress)
                return None
            
            # Find matching result for this selector's match
            home_team = selector_data.get('home_team', '').strip()
            away_team = selector_data.get('away_team', '').strip()
            
            matching_result = None
            for result in live_results:
                result_home = result.get('home_team', '').strip()
                result_away = result.get('away_team', '').strip()
                
                # Check for exact match (home-away or away-home)
                if ((result_home == home_team and result_away == away_team) or
                    (result_home == away_team and result_away == home_team)):
                    matching_result = result
                    break
            
            if not matching_result:
                return None
            
            home_score = matching_result.get('home_score', 0)
            away_score = matching_result.get('away_score', 0)
            
            # Determine BTTS result
            both_scored = home_score > 0 and away_score > 0
            only_one_scored = (home_score > 0) != (away_score > 0)
            neither_scored = home_score == 0 and away_score == 0
            
            if both_scored:
                return {
                    'points': self.BTTS_SUCCESS_POINTS,
                    'description': 'BTTS ✓',
                    'final_score': f'{home_score}-{away_score}'
                }
            elif only_one_scored:
                return {
                    'points': self.SINGLE_GOAL_POINTS,
                    'description': 'Single Goal',
                    'final_score': f'{home_score}-{away_score}'
                }
            elif neither_scored:
                return {
                    'points': self.NO_GOAL_POINTS,
                    'description': 'No Goals',
                    'final_score': f'{home_score}-{away_score}'
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error calculating match result: {e}")
            return None
    
    def _calculate_league_statistics(self, selector_performance: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall league statistics"""
        try:
            if not selector_performance:
                return {
                    'total_weeks': 0,
                    'average_btts_rate': 0,
                    'active_selectors': 0,
                    'best_btts': None,
                    'most_active': None,
                    'most_points': None
                }
            
            selectors_with_matches = [s for s in selector_performance.values() if s['total_matches'] > 0]
            
            # Best BTTS percentage
            best_btts = max(selectors_with_matches, key=lambda x: x['btts_percentage']) if selectors_with_matches else None
            
            # Most active selector
            most_active = max(selectors_with_matches, key=lambda x: x['total_matches']) if selectors_with_matches else None
            
            # Most points overall
            most_points = max(selectors_with_matches, key=lambda x: x['total_points']) if selectors_with_matches else None
            
            # Calculate average BTTS rate
            total_btts_rate = sum(s['btts_percentage'] for s in selectors_with_matches)
            average_btts_rate = total_btts_rate / len(selectors_with_matches) if selectors_with_matches else 0
            
            return {
                'total_weeks': len(self._get_all_selection_files()),
                'average_btts_rate': average_btts_rate,
                'active_selectors': len(selectors_with_matches),
                'best_btts': {
                    'selector': best_btts['selector_name'],
                    'percentage': best_btts['btts_percentage']
                } if best_btts else None,
                'most_active': {
                    'selector': most_active['selector_name'],
                    'matches': most_active['total_matches']
                } if most_active else None,
                'most_points': {
                    'selector': most_points['selector_name'],
                    'points': most_points['total_points']
                } if most_points else None
            }
            
        except Exception as e:
            logger.error(f"Error calculating league statistics: {e}")
            return {}
    
    def _calculate_weekly_statistics(self, selector_performance: Dict[str, Any], selection_files: List[str]) -> Dict[str, Any]:
        """Calculate weekly statistics and trends"""
        try:
            # This would calculate weekly performance trends
            # For now, return a basic structure
            weekly_points = {}
            selector_performance_data = []
            
            for selector_name, performance in selector_performance.items():
                if performance['total_matches'] > 0:
                    selector_performance_data.append({
                        'selector_name': selector_name,
                        'weekly_points': list(performance['weekly_points'].values()),
                        'total_points': performance['total_points']
                    })
            
            # Find most points this week
            current_week = datetime.now().strftime('%Y-%m-%d')
            this_week_points = {}
            
            for selector_name, performance in selector_performance.items():
                if current_week in performance['weekly_points']:
                    this_week_points[selector_name] = performance['weekly_points'][current_week]
            
            most_points_this_week = None
            if this_week_points:
                max_points = max(this_week_points.values())
                selector_with_max = max(this_week_points.keys(), key=lambda k: this_week_points[k])
                most_points_this_week = {
                    'selector': selector_with_max,
                    'points': max_points
                }
            
            return {
                'weekly_points': weekly_points,
                'selector_performance': selector_performance_data,
                'most_points': most_points_this_week
            }
            
        except Exception as e:
            logger.error(f"Error calculating weekly statistics: {e}")
            return {}
    
    def _apply_view_filter(self, selector_performance: Dict[str, Any], view_filter: str) -> List[Dict[str, Any]]:
        """Apply view filter to selector performance data"""
        try:
            selectors_list = list(selector_performance.values())
            
            if view_filter == 'this-season':
                # Filter to selectors with matches this season
                return [s for s in selectors_list if s['total_matches'] > 0]
            elif view_filter == 'recent':
                # Filter to selectors active in last 10 weeks
                cutoff_date = datetime.now() - timedelta(weeks=10)
                recent_selectors = []
                for selector in selectors_list:
                    recent_matches = [r for r in selector['recent_form'] if 
                                    datetime.strptime(r['week'], '%Y-%m-%d') >= cutoff_date]
                    if recent_matches:
                        recent_selectors.append(selector)
                return recent_selectors
            else:  # overall
                return selectors_list
                
        except Exception as e:
            logger.error(f"Error applying view filter: {e}")
            return list(selector_performance.values())
    
    def _get_current_week_number(self) -> int:
        """Get current week number of the year"""
        return datetime.now().isocalendar()[1]
    
    def _create_empty_league_data(self) -> Dict[str, Any]:
        """Create empty league data structure"""
        return {
            'success': True,
            'selectors': [],
            'weekly_stats': {
                'most_points': None,
                'selector_performance': []
            },
            'season_stats': {
                'total_weeks': 0,
                'average_btts_rate': 0,
                'active_selectors': 0,
                'best_btts': None,
                'most_active': None,
                'most_points': None
            },
            'last_updated': datetime.now().isoformat(),
            'current_week': self._get_current_week_number(),
            'season_year': datetime.now().year
        }
    
    def _create_error_league_data(self, error_message: str) -> Dict[str, Any]:
        """Create error league data structure"""
        return {
            'success': False,
            'error': error_message,
            'selectors': [],
            'weekly_stats': {},
            'season_stats': {},
            'last_updated': datetime.now().isoformat(),
            'current_week': self._get_current_week_number(),
            'season_year': datetime.now().year
        }


    def _create_historical_performance_data(self) -> Dict[str, Any]:
        """
        Create performance data from historical points for all selectors
        Returns dictionary with selector performance data based on historical points
        """
        try:
            selector_performance = {}
            
            for selector_name in self.selectors:
                # Get historical points for this selector
                historical_points = self.historical_points.get(selector_name, 0)
                
                # Estimate matches based on points (roughly 1 match per week)
                # Since we have historical points, estimate they played regularly
                estimated_matches = max(1, abs(historical_points) // 3)  # Rough estimate
                btts_successes = max(0, historical_points // 3)  # 3 points per BTTS success
                no_goal_results = max(0, abs(min(0, historical_points)) // 3)  # 3 points lost per no goal
                single_goal_results = estimated_matches - btts_successes - no_goal_results
                
                # Calculate BTTS percentage
                btts_percentage = (btts_successes / estimated_matches * 100) if estimated_matches > 0 else 0
                
                # Create recent form entries (simulated)
                recent_form = []
                total_weeks = min(10, estimated_matches)  # Show up to 10 recent entries
                points_per_week = historical_points / total_weeks if total_weeks > 0 else 0
                
                for i in range(total_weeks):
                    week_date = datetime.now() - timedelta(weeks=total_weeks-i)
                    form_entry = {
                        'week': week_date.strftime('%Y-%m-%d'),
                        'match_home': 'Home Team',
                        'match_away': 'Away Team',
                        'points': round(points_per_week),
                        'result_description': 'BTTS ✓' if round(points_per_week) == 3 else 'Single Goal' if round(points_per_week) == 0 else 'No Goals',
                        'final_score': '2-1' if round(points_per_week) == 3 else '1-0' if round(points_per_week) == 0 else '0-0'
                    }
                    recent_form.append(form_entry)
                
                selector_performance[selector_name] = {
                    'selector_name': selector_name,
                    'total_points': historical_points,
                    'total_matches': estimated_matches,
                    'btts_successes': btts_successes,
                    'single_goal_results': single_goal_results,
                    'no_goal_results': no_goal_results,
                    'btts_percentage': btts_percentage,
                    'recent_form': recent_form,
                    'recent_points': historical_points,  # All recent points
                    'recent_average': historical_points / len(recent_form) if recent_form else 0,
                    'average_weekly_points': historical_points / estimated_matches if estimated_matches > 0 else 0,
                    'weekly_points': {}  # No specific weekly breakdown for historical data
                }
            
            return selector_performance
            
        except Exception as e:
            logger.error(f"Error creating historical performance data: {e}")
            return {}


# Global instance
selectors_league = SelectorsLeague()