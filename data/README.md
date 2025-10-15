# Data Storage Structure

This directory contains the data files for the Football Predictions Admin Interface.

## Directory Structure

```
data/
└── selections/
    ├── week_YYYY-MM-DD.json    # Weekly selection files
    └── README.md               # This file
```

## Selection Files

Each selection file follows the naming convention `week_YYYY-MM-DD.json` where the date represents the Saturday for which the matches are being selected.

### File Format

```json
{
  "selectors": {
    "Glynny": {
      "id": "Premier League_Manchester United_Chelsea",
      "league": "Premier League",
      "home_team": "Manchester United",
      "away_team": "Chelsea",
      "kickoff": "15:00",
      "venue": "Old Trafford",
      "assigned_at": "2024-10-10T14:30:00.123456"
    },
    "Eamonn Bone": {
      "id": "Championship_Leeds_Leicester",
      "league": "Championship",
      "home_team": "Leeds",
      "away_team": "Leicester",
      "kickoff": "15:00",
      "venue": "Elland Road",
      "assigned_at": "2024-10-10T14:35:00.123456"
    }
  },
  "matches": [
    {
      "league": "Premier League",
      "home_team": "Manchester United",
      "away_team": "Chelsea",
      "kickoff": "15:00",
      "venue": "Old Trafford"
    }
  ],
  "last_updated": "2024-10-10T15:00:00.123456",
  "override_confirmed": false,
  "override_confirmed_at": null,
  "override_confirmed_by": null
}
```

### Fields Description

- **selectors**: Object containing all selector assignments
  - Key: Selector name
  - Value: Match assignment details
    - `id`: Unique match identifier (league_home_team_away_team)
    - `league`: League name
    - `home_team`: Home team name
    - `away_team`: Away team name
    - `kickoff`: Kickoff time (should be "15:00")
    - `venue`: Stadium name
    - `assigned_at`: ISO timestamp of assignment

- **matches**: Array of all available matches for the week (from BBC scraper)

- **last_updated**: ISO timestamp of last modification

- **override_confirmed**: Boolean indicating if override was used for <8 selections

- **override_confirmed_at**: ISO timestamp of override confirmation

- **override_confirmed_by**: User who confirmed the override

## Usage Notes

- Files are automatically created when selections are saved
- Each Saturday gets its own file based on the next Saturday's date
- Files are loaded automatically when accessing the admin interface
- The system ensures one match per selector validation
- Override confirmations are logged for audit purposes

## Backup Recommendation

Regularly backup the `data/selections/` directory to preserve historical selection data.