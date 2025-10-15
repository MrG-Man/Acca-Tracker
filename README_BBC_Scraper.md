# BBC Sport Football Fixtures Scraper

A comprehensive web scraper for extracting football fixtures from BBC Sport, specifically designed to retrieve next Saturday's 15:00 (3pm) matches from 8 English and Scottish leagues.

## Features

- **Zero API Calls**: Pure web scraping using requests + BeautifulSoup
- **8 League Coverage**: All major English and Scottish professional leagues
- **3pm Focus**: Extracts only Saturday 15:00 kickoff matches
- **Rate Limiting**: Respects BBC servers with configurable delays
- **Caching**: 24-hour cache to avoid redundant scraping
- **Error Handling**: Robust error handling for website changes
- **Comprehensive Tests**: Full test suite with mock data

## Supported Leagues

### English Leagues
- Premier League
- English Championship
- English League One
- English League Two

### Scottish Leagues
- Scottish Premiership
- Scottish Championship
- Scottish League One
- Scottish League Two

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Or install manually:
```bash
pip install requests beautifulsoup4 lxml
```

## Usage

### Basic Usage

```python
from bbc_scraper import BBCSportScraper

# Initialize scraper
scraper = BBCSportScraper()

# Get next Saturday's 15:00 fixtures
result = scraper.scrape_saturday_3pm_fixtures()

print(f"Found {len(result['matches_3pm'])} matches")
for match in result['matches_3pm']:
    print(f"{match['league']}: {match['home_team']} vs {match['away_team']} at {match['kickoff']}")
```

### Advanced Usage

```python
# Custom cache directory and rate limiting
scraper = BBCSportScraper(
    cache_dir="custom_cache",
    rate_limit=2.0  # 2 seconds between requests
)

# Clear cache if needed
scraper.clear_cache()

# Get results
result = scraper.scrape_saturday_3pm_fixtures()
```

## Output Format

```python
{
    "scraping_date": "2024-10-11",
    "next_saturday": "2024-10-12",
    "matches_3pm": [
        {
            "league": "Premier League",
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "kickoff": "15:00",
            "venue": "Emirates Stadium"
        }
        // ... more matches
    ]
}
```

## Key Features Explained

### Rate Limiting
- Configurable delay between requests (default: 1.0 seconds)
- Prevents overwhelming BBC servers
- Automatic enforcement before each request

### Caching
- 24-hour cache expiration
- Automatic cache key generation based on URL and date
- Reduces unnecessary requests and improves performance
- Manual cache clearing available

### Error Handling
- Graceful handling of network failures
- Robust HTML parsing with fallback options
- Comprehensive logging for debugging
- Continues processing even if individual leagues fail

### 3pm Validation
- Strict filtering for exactly "15:00" kickoff times
- Ignores other kickoff times (12:30, 17:30, etc.)
- Ensures only traditional Saturday 3pm matches are returned

## Testing

Run the comprehensive test suite:

```bash
python test_bbc_scraper.py
```

Tests include:
- Date calculation validation
- HTML parsing with various edge cases
- Cache functionality and expiry
- Rate limiting verification
- Error handling scenarios
- Mock data scenarios

## Configuration

### BBCSportScraper Parameters

- `cache_dir` (str): Directory for storing cached results (default: "cache")
- `rate_limit` (float): Minimum seconds between requests (default: 1.0)

### League URLs

All BBC Sport league URLs are pre-configured:
- English leagues use standard URLs
- Scottish leagues use their respective section URLs
- URLs are automatically joined with the BBC base URL

## Dependencies

- `requests`: HTTP library for making web requests
- `beautifulsoup4`: HTML parsing library
- `lxml`: Fast XML/HTML parser (recommended for performance)

## Limitations

- Dependent on BBC Sport website structure
- May break if BBC changes their HTML layout
- Rate limiting may slow down large-scale usage
- Cache files stored locally in specified directory

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed
2. **Network Timeouts**: Increase timeout in `_make_request()` method
3. **Cache Issues**: Clear cache manually with `scraper.clear_cache()`
4. **Rate Limiting Too Slow**: Reduce `rate_limit` parameter for faster scraping

### Logging

Enable debug logging to troubleshoot issues:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Performance Considerations

- Cache reduces redundant requests
- Rate limiting prevents IP blocking
- Session reuse for multiple requests
- Efficient HTML parsing with lxml

## Future Enhancements

- Configurable league selection
- Multiple date support
- Export to various formats (CSV, Excel)
- Web interface for easy usage
- Scheduled scraping with cron jobs

## License

This scraper is designed for educational and personal use. Please respect BBC's terms of service and robots.txt when using this tool.