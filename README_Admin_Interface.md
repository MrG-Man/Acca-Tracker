# Football Predictions Admin Interface

A Flask web interface for selecting and assigning Saturday 3pm football matches to panel members using BBC Sport data.

## Features

- **Match Display**: Shows next Saturday's 15:00 matches from BBC Sport scraper
- **Dynamic Selector Assignment**: Dropdown shows only unassigned panel members
- **One-Match-Per-Selector**: Validation ensures each selector gets only one match
- **Progress Tracking**: Visual progress bar showing assignment completion
- **Override Function**: Allows proceeding with <8 selections with confirmation
- **Mobile Responsive**: Works on desktop and mobile devices
- **JSON Storage**: Saves selections to `data/selections/week_YYYY-MM-DD.json`

## Panel Members (Assignment Order)

1. Glynny
2. Eamonn Bone
3. Mickey D
4. Rob Carney
5. Steve H
6. Danny
7. Eddie Lee
8. Fran Radar

## Installation & Setup

### 1. Virtual Environment (Recommended)

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\\Scripts\\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Dependencies

The following packages are required:

- Flask>=3.0.0 (web framework)
- requests>=2.31.0 (HTTP requests)
- beautifulsoup4>=4.12.0 (HTML parsing)
- lxml>=4.9.0 (XML parser)

### 3. Directory Structure

```
football-predictions/
├── app.py                    # Main Flask application
├── bbc_scraper.py           # BBC Sport scraper
├── requirements.txt         # Python dependencies
├── templates/
│   └── admin.html          # Admin interface template
├── static/
│   ├── css/
│   │   └── admin.css       # Styling
│   └── js/
│       └── admin.js        # Frontend logic
├── data/
│   ├── selections/         # JSON storage for selections
│   │   ├── week_YYYY-MM-DD.json
│   │   └── README.md
│   └── README.md           # Data structure documentation
└── cache/                  # BBC scraper cache
```

## Usage

### Running the Admin Interface

```bash
# Activate virtual environment
source venv/bin/activate

# Start the Flask application
python app.py
```

The application will start on `http://localhost:5000`

### Accessing the Admin Interface

1. Open your browser and go to `http://localhost:5000/admin`
2. The interface will display:
   - Next Saturday's date
   - Available 15:00 matches from BBC Sport
   - Current assignment progress
   - Unassigned panel members

### Making Assignments

1. **Select Match**: Browse the displayed matches
2. **Choose Selector**: Use dropdown to select available panel member
3. **Assign**: Click "Assign" button to make the assignment
4. **Track Progress**: Monitor completion in the progress section

### Override Process (for <8 selections)

If you need to proceed with fewer than 8 selections:

1. Click "Override Confirmation" button
2. Type the exact confirmation text
3. Select reason for override
4. Confirm the override

## API Endpoints

- `GET /admin` - Main admin interface
- `POST /api/assign` - Assign match to selector
- `POST /api/unassign` - Unassign match from selector
- `GET /api/selections` - Get current selections
- `POST /api/override` - Confirm override for <8 selections

## Data Storage

Selections are automatically saved to:
```
data/selections/week_YYYY-MM-DD.json
```

Each file contains:
- Selector assignments with match details
- Assignment timestamps
- Override confirmations (if used)

## Technical Details

### Match Filtering

- Only displays matches with exactly "15:00" kickoff time
- Shows next Saturday's matches only
- Uses BBC Sport scraper with caching (24-hour expiry)

### Validation Rules

- Each selector can only have one match
- Dropdown only shows unassigned selectors
- Must have 8 selections or confirmed override
- Match IDs are generated as: `{league}_{home_team}_{away_team}`

### Error Handling

- Network errors are handled gracefully
- Invalid assignments are rejected with clear messages
- Cache failures fall back to fresh scraping
- Override process requires explicit confirmation

## Troubleshooting

### Common Issues

1. **No matches displayed**
   - Check BBC Sport website availability
   - Verify date calculation for next Saturday
   - Check scraper cache files

2. **Assignment not working**
   - Ensure selector isn't already assigned
   - Check browser JavaScript console for errors
   - Verify Flask application is running

3. **Styling issues**
   - Check static file paths
   - Verify CSS/JS files are being served
   - Clear browser cache

### Debug Mode

Run with debug logging:
```bash
python -c "
from bbc_scraper import BBCSportScraper
scraper = BBCSportScraper()
result = scraper.scrape_saturday_3pm_fixtures()
print('Found matches:', len(result.get('matches_3pm', [])))
"
```

## Security Notes

- Application runs on localhost only (not exposed to internet)
- No authentication implemented (single-user admin interface)
- Data stored in plain JSON files (not encrypted)
- Consider implementing authentication for production use

## Future Enhancements

- User authentication and authorization
- Historical selection viewing
- Export functionality (CSV/PDF)
- Email notifications for assignments
- Bulk assignment features
- Selection deadline management