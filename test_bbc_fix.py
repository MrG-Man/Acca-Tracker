#!/usr/bin/env python3
"""
Test script to verify the BBC scraper fix for 2025-10-25.
"""

from bbc_scraper import BBCSportScraper
import json

def test_fixed_scraper():
    """Test the fixed BBC scraper with JSON-based parsing."""
    print("=" * 80)
    print("TESTING FIXED BBC SCRAPER")
    print("=" * 80)
    print()
    
    scraper = BBCSportScraper(rate_limit=1.0)
    
    # Test scraping for 2025-10-25
    target_date = "2025-10-25"
    print(f"Testing unified scraping for {target_date}...")
    print()
    
    result = scraper.scrape_unified_bbc_matches(target_date, scraper.MODE_FIXTURES)
    
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"Total matches found: {result['total_matches']}")
    print()
    
    # Group matches by league
    matches_by_league = {}
    for match in result['matches']:
        league = match['league']
        if league not in matches_by_league:
            matches_by_league[league] = []
        matches_by_league[league].append(match)
    
    # Display results by league
    for league in sorted(matches_by_league.keys()):
        matches = matches_by_league[league]
        print(f"\n{league}: {len(matches)} matches")
        print("-" * 60)
        
        # Show 15:00 kickoffs
        matches_15_00 = [m for m in matches if m['kickoff'] == '15:00']
        if matches_15_00:
            print(f"  15:00 kickoffs: {len(matches_15_00)}")
            for match in matches_15_00[:5]:  # Show first 5
                print(f"    • {match['home_team']} vs {match['away_team']}")
            if len(matches_15_00) > 5:
                print(f"    ... and {len(matches_15_00) - 5} more")
        
        # Show other kickoff times
        other_times = [m for m in matches if m['kickoff'] != '15:00']
        if other_times:
            print(f"  Other times: {len(other_times)}")
            for match in other_times[:3]:  # Show first 3
                print(f"    • {match['home_team']} vs {match['away_team']} ({match['kickoff']})")
            if len(other_times) > 3:
                print(f"    ... and {len(other_times) - 3} more")
    
    print()
    print("=" * 80)
    print("VALIDATION CHECKS")
    print("=" * 80)
    
    # Check for issues found in diagnosis
    issues_found = []
    
    for match in result['matches']:
        league = match['league']
        home = match['home_team']
        away = match['away_team']
        
        # Check Chelsea vs Sunderland
        if 'Chelsea' in home and 'Sunderland' in away:
            if league == "Premier League":
                issues_found.append(f"✗ ISSUE PERSISTS: {home} vs {away} still marked as {league}")
            else:
                print(f"✓ FIXED: {home} vs {away} now correctly marked as {league}")
        
        # Check for English Championship teams in wrong leagues
        championship_teams = ['Coventry', 'Ipswich', 'Middlesbrough', 'Watford', 'West Brom']
        if any(team in home or team in away for team in championship_teams):
            if league not in ["English Championship", "Championship"]:
                issues_found.append(f"✗ ISSUE: {home} vs {away} marked as {league} (should be Championship)")
            else:
                print(f"✓ CORRECT: {home} vs {away} in {league}")
    
    if issues_found:
        print("\nISSUES STILL PRESENT:")
        for issue in issues_found:
            print(issue)
    else:
        print("\n✓ All validation checks passed!")
    
    print()
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    
    return result


if __name__ == "__main__":
    result = test_fixed_scraper()