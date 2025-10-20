#!/usr/bin/env python3
"""
Diagnostic script to test BBC scraper for 2025-10-25 and identify parsing issues.
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime

def test_bbc_page_structure(target_date="2025-10-25"):
    """Test the BBC page structure for the target date."""
    print("=" * 80)
    print(f"DIAGNOSTIC: BBC Page Structure for {target_date}")
    print("=" * 80)
    print()
    
    # Build BBC URL
    url = f"https://www.bbc.co.uk/sport/football/scores-fixtures/{target_date}"
    print(f"Testing URL: {url}")
    print()
    
    # Make request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        print(f"✓ Successfully retrieved page (Status: {response.status_code})")
        print()
    except Exception as e:
        print(f"✗ Failed to retrieve page: {e}")
        return None
    
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Test 1: Look for league headers
    print("=" * 80)
    print("TEST 1: Finding League Headers")
    print("=" * 80)
    
    league_patterns = [
        "Premier League", "Championship", "League One", "League Two", 
        "National League", "Scottish Premiership", "Scottish Championship",
        "Scottish League One", "Scottish League Two"
    ]
    
    found_leagues = []
    for pattern in league_patterns:
        elements = soup.find_all(string=re.compile(pattern, re.IGNORECASE))
        if elements:
            found_leagues.append(pattern)
            print(f"✓ Found '{pattern}' - {len(elements)} occurrences")
    
    if not found_leagues:
        print("✗ No league headers found!")
    print()
    
    # Test 2: Look for "versus" patterns (match indicators)
    print("=" * 80)
    print("TEST 2: Finding Match Patterns")
    print("=" * 80)
    
    versus_elements = soup.find_all(string=re.compile(r'versus', re.IGNORECASE))
    print(f"Found {len(versus_elements)} elements containing 'versus'")
    print()
    
    if versus_elements:
        print("Sample match texts (first 10):")
        for i, elem in enumerate(versus_elements[:10], 1):
            match_text = elem.strip()
            # Try to extract kickoff time
            kickoff_match = re.search(r'kick off (\d{1,2}:\d{2})', match_text, re.IGNORECASE)
            kickoff = kickoff_match.group(1) if kickoff_match else "N/A"
            print(f"  {i}. {match_text[:80]}... [Kickoff: {kickoff}]")
    print()
    
    # Test 3: Look for 15:00 kickoff matches specifically
    print("=" * 80)
    print("TEST 3: Finding 15:00 Kickoff Matches")
    print("=" * 80)
    
    matches_15_00 = []
    for elem in versus_elements:
        match_text = elem.strip()
        if 'kick off 15:00' in match_text.lower():
            matches_15_00.append(match_text)
    
    print(f"Found {len(matches_15_00)} matches with 15:00 kickoff")
    if matches_15_00:
        print("\nMatches at 15:00:")
        for i, match in enumerate(matches_15_00, 1):
            print(f"  {i}. {match}")
    print()
    
    # Test 4: Test league identification logic
    print("=" * 80)
    print("TEST 4: League Identification Analysis")
    print("=" * 80)
    
    matches_with_context = []
    for elem in versus_elements:
        if 'kick off 15:00' in elem.lower():
            match_text = elem.strip()
            
            # Extract teams
            versus_pattern = re.search(r'(.+?)\s+versus\s+(.+?)\s+kick off (\d{1,2}:\d{2})', 
                                      match_text, re.IGNORECASE)
            if versus_pattern:
                home_team = versus_pattern.group(1).strip()
                away_team = versus_pattern.group(2).strip()
                kickoff = versus_pattern.group(3).strip()
                
                # Try to find league by looking at context
                parent = elem.parent
                league_found = None
                
                # Look backwards through parents/siblings for league header
                current = parent
                for _ in range(15):
                    if current:
                        context_text = current.get_text()
                        for league in league_patterns:
                            if league.lower() in context_text.lower():
                                league_found = league
                                break
                        if league_found:
                            break
                        
                        # Move up/back in the tree
                        if current.previous_sibling:
                            current = current.previous_sibling
                        elif current.parent:
                            current = current.parent
                        else:
                            break
                
                matches_with_context.append({
                    'home': home_team,
                    'away': away_team,
                    'kickoff': kickoff,
                    'league': league_found or 'UNKNOWN'
                })
    
    print(f"Analyzed {len(matches_with_context)} matches with league context:")
    print()
    
    # Group by league
    by_league = {}
    for match in matches_with_context:
        league = match['league']
        if league not in by_league:
            by_league[league] = []
        by_league[league].append(match)
    
    for league, matches in sorted(by_league.items()):
        print(f"{league}: {len(matches)} matches")
        for match in matches:
            print(f"  • {match['home']} vs {match['away']}")
    print()
    
    # Test 5: Compare with cached data
    print("=" * 80)
    print("TEST 5: Comparison with Cached Data")
    print("=" * 80)
    
    try:
        with open('data/fixtures/bbc_cache_2025-10-25.json', 'r') as f:
            cached_data = json.load(f)
            cached_matches = cached_data.get('fixtures', [])
            
        print(f"Cached data contains {len(cached_matches)} matches")
        print()
        
        # Show mismatches
        cached_15_00 = [m for m in cached_matches if m['kickoff'] == '15:00']
        print(f"Cached 15:00 matches: {len(cached_15_00)}")
        print(f"Live scraped 15:00 matches: {len(matches_with_context)}")
        print()
        
        print("Cached matches by league:")
        cached_by_league = {}
        for match in cached_15_00:
            league = match['league']
            if league not in cached_by_league:
                cached_by_league[league] = []
            cached_by_league[league].append(f"{match['home_team']} vs {match['away_team']}")
        
        for league, matches in sorted(cached_by_league.items()):
            print(f"\n{league}: {len(matches)} matches")
            for match in matches:
                print(f"  • {match}")
        
        # Identify mismatches
        print("\n" + "=" * 80)
        print("IDENTIFIED ISSUES:")
        print("=" * 80)
        
        issues_found = []
        
        # Check for wrong league assignments
        for match in cached_15_00:
            league = match['league']
            home = match['home_team']
            away = match['away_team']
            
            # Scottish Premiership should only have Scottish teams
            if league == "Scottish Premiership":
                english_indicators = ['coventry', 'ipswich', 'middlesbrough', 'watford', 
                                     'west bromwich', 'cheadle']
                if any(ind in home.lower() or ind in away.lower() for ind in english_indicators):
                    issues_found.append(
                        f"✗ WRONG LEAGUE: '{home} vs {away}' marked as {league} "
                        f"but appears to be English teams"
                    )
            
            # Check for teams in wrong leagues
            championship_teams = ['coventry', 'ipswich', 'middlesbrough', 'watford', 
                                'west bromwich', 'sunderland']
            if league == "Premier League":
                if any(team in home.lower() or team in away.lower() for team in championship_teams):
                    issues_found.append(
                        f"✗ WRONG LEAGUE: '{home} vs {away}' marked as {league} "
                        f"but appears to be Championship team"
                    )
        
        if issues_found:
            for issue in issues_found:
                print(issue)
        else:
            print("No obvious issues found in cached data")
            
    except FileNotFoundError:
        print("Cached data file not found - skipping comparison")
    except Exception as e:
        print(f"Error reading cached data: {e}")
    
    print()
    return soup, matches_with_context


if __name__ == "__main__":
    result = test_bbc_page_structure("2025-10-25")
    
    if result:
        soup, matches = result
        print("=" * 80)
        print("DIAGNOSIS COMPLETE")
        print("=" * 80)
        print()
        print("NEXT STEPS:")
        print("1. Review the league identification issues above")
        print("2. Check if BBC page structure has changed")
        print("3. Verify the _identify_league_from_context() function in bbc_scraper.py")
        print("4. Consider improving league detection logic")
    else:
        print("Diagnostic failed - unable to retrieve BBC page")