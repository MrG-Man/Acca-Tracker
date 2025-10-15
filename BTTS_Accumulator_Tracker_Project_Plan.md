# BTTS Accumulator Tracker - Project Plan

## Project Overview

**8-Person BTTS Accumulator Betting Tracker**
- Track live scores for 8 simultaneously matches (3pm Saturday kickoffs)
- Monitor BTTS (Both Teams To Score) status for each match
- Assign each match to one of 8 fixed panel members
- Simple web interface for admin setup and public tracking

## Business Requirements

### Core Functionality
- **Admin Interface**: Select 8 matches from England/Scotland leagues for Saturday 3pm kickoffs
- **Selector Assignment**: Assign each match to one of 8 fixed panel members
- **Live Scoreboard**: Real-time BTTS tracking for all 8 matches
- **BTTS Detection**: Highlight matches when both teams score (PRIMARY FEATURE)
- **BTTS Status Display**: Clear visual indication of fulfilled selections

### Panel Members (Fixed Selectors)
1. **Glynny** - Panel Member 1
2. **Eamonn Bone** - Panel Member 2
3. **Mickey D** - Panel Member 3
4. **Rob Carney** - Panel Member 4
5. **Steve H** - Panel Member 5
6. **Danny** - Panel Member 6
7. **Eddie Lee** - Panel Member 7
8. **Fran Radar** - Panel Member 8

### Admin Interface Rules
- **Match Scope**: ONLY next Saturday 3pm matches (no future/past)
- **Time Filter**: EXACTLY 15:00 kickoff time only
- **Selector Assignment**: One match per selector maximum
- **Available Selectors**: Dropdown shows remaining unassigned selectors
- **Override Function**: Allow <8 selections (rare cases) with confirmation

### Technical Constraints
- **8 simultaneous matches** at 3pm Saturday only
- **4 Saturdays per month** accumulator schedule
- **500 free API calls/month** budget
- **Fixed panel** (selectors don't change)

## Technical Architecture

### System Architecture
```
/admin                    # Admin-only match selection interface
/tracker                  # Public BTTS scoreboard
/api                      # Backend API endpoints
/static                   # CSS, JavaScript, images
/data                     # JSON storage for selections and cache
```

### Technology Stack
- **Backend**: Python Flask (lightweight web framework)
- **Frontend**: HTML/CSS/JavaScript (no frameworks)
- **Data Storage**: JSON files for selections, cache
- **Web Scraping**: BBC Sport for match fixtures (Saturday 3pm only)
- **API Integration**: Sofascore API (live scores only, 12-16 calls/month)
- **Deployment**: Single server (local or cloud)

## Hybrid Data Strategy & Budget Management

### Monthly API Budget: 500 Calls (75% Reduction Achieved)
- **Optimized Usage**: 12-16 calls per month (3% utilization)
- **Budget Breakdown**:
  - Live tracking: 3-4 calls per Saturday × 4 Saturdays = 12-16 calls
  - Match details: 0 calls (web scraping)
  - Setup/Admin: 0 calls (web scraping)
  - Buffer: 484 calls for testing and errors

### Data Source Separation Strategy
- **Web Scraping (BBC Sport)**: All match fixtures and details (Saturday 3pm only)
- **Sofascore API**: Live scores only (every 15-20 minutes)
- **Smart Caching**: Different TTL for different data types
- **Batch Processing**: Single API call for all 8 matches

### Event-Driven Call Pattern
```
Saturday Schedule:
3:00pm - 5:00pm (2-hour window)
- Updates triggered by KO/HT/FT events (not time-based)
- Goal events trigger immediate updates
- 3-4 API calls per Saturday (event-driven)
- 4 Saturdays = 12-16 calls per month
- 75% reduction from original 48 calls/month

Critical Events Monitored:
- Kick-Off (KO) detection
- Half-Time (HT) confirmation
- Full-Time (FT) verification
- Goal scoring events (both teams)
```

### Scraping Schedule
```
Friday Schedule:
- Weekly scraping: 8 league pages (England + Scotland)
- Update frequency: Friday evenings for Saturday matches
- Data scope: Saturday 3pm kickoffs only
```

## Development Phases

### Phase 1: Core Infrastructure (Week 1-2)
- [ ] Set up Flask web application
- [ ] Create basic routing structure (/admin, /tracker)
- [ ] Implement JSON data storage for selections
- [ ] Basic HTML templates for both interfaces

### Phase 2: Web Scraping & Admin Interface (Week 3)
- [ ] BBC Sport scraper for all 8 England/Scotland leagues
- [ ] Saturday 3pm ONLY filtering (next Saturday, 15:00 kickoffs)
- [ ] Admin interface with filtered match selection
- [ ] Dynamic selector assignment (dropdown of available selectors)
- [ ] One-match-per-selector validation
- [ ] Override function for <8 selections (with confirmation)
- [ ] Data validation and storage

### Phase 3: Live Scoreboard (Week 4)
- [ ] Real-time score display for 8 matches
- [ ] BTTS status detection and highlighting
- [ ] Auto-refresh functionality (5-minute intervals)
- [ ] Mobile-responsive design

### Phase 4: API Integration & Optimization (Week 5)
- [ ] Integrate Sofascore API for live scores
- [ ] Implement single-call batch updates
- [ ] Add intelligent caching system
- [ ] API usage monitoring and alerts

### Phase 5: Testing & Refinement (Week 6)
- [ ] End-to-end testing of accumulator workflow
- [ ] Performance optimization
- [ ] User experience refinements
- [ ] Documentation and deployment guide

## Hybrid Data Flow Architecture

### Weekly Setup Workflow (Friday Evenings)
1. **Web Scraping**: Scrape BBC Sport for all 8 England/Scotland leagues
2. **Time Filtering**: Extract ONLY next Saturday 15:00 matches
3. **Match Selection**: Admin selects from available 3pm matches only
4. **Selector Assignment**: Dropdown of remaining available selectors
5. **One-per-Selector**: Each selector can only have one match
6. **Override Option**: Allow <8 selections with double confirmation
7. **Data Storage**: Selections saved to weekly JSON file

### Live Tracking Workflow (Saturday 3pm)
1. **Load Selections**: Load 8 matches from JSON storage
2. **Match Status Monitoring**: Detect KO/HT/FT events reliably
3. **Live Score Updates**: Update on status changes (not time-based)
4. **BTTS Detection**: Monitor for both teams scoring (event-driven)
5. **Critical Event Display**: Show KO/HT/FT status clearly
6. **Real-time Display**: Update on official match events

### Caching Strategy
- **Fixture Data**: 6-12 hour cache (weekly updates)
- **Live Scores**: 3-5 minute cache (real-time updates)
- **Match Details**: 24-72 hour cache (team/league info)

## BTTS Detection & Display System

### Primary Feature: BTTS Status Highlighting
**Core Requirement**: Instantly identify fulfilled BTTS selections at a glance

### BTTS Detection Logic
- **Valid Period**: From KO to FT only (official match time)
- **Detection**: When both teams have scored (score > 0 for both)
- **Real-time**: Updates immediately when second goal scored
- **Event-Driven**: Triggered by goal events, not time intervals

### Visual Display Requirements
- **Clear Highlighting**: Obvious visual distinction for BTTS matches
- **8-Match Overview**: All selections visible simultaneously
- **Selector Names**: Show which panel member chose each match
- **Score Display**: Current scoreline for context
- **Status Indicators**: BTTS ✅ vs No BTTS ❌
- **Live Updates**: Real-time refresh during match window

### BTTS Tally System
- **Count Display**: "X/8 BTTS" achieved
- **Quick Reference**: Immediate overview of accumulator status
- **Progress Tracking**: See which selections are still pending

## File Structure

```
BTTS_Accumulator_Tracker/
├── app.py                    # Main Flask application
├── requirements.txt          # Python dependencies
├── bbc_scraper.py           # BBC Sport web scraper (8 leagues)
├── sofascore_optimized.py    # Live scores API client (optimized)
├── data_manager.py          # Coordinates scraping + API data
├── templates/
│   ├── admin.html           # Admin interface (match selection)
│   ├── tracker.html         # Public scoreboard
│   └── base.html            # Common template
├── static/
│   ├── css/
│   │   ├── admin.css
│   │   └── tracker.css
│   └── js/
│       ├── admin.js
│       └── tracker.js
├── data/
│   ├── selections/          # Weekly match selections
│   ├── fixtures/           # Scraped fixture data cache
│   └── cache/              # API response cache
└── BTTS_Accumulator_Tracker_Project_Plan.md
```

## Risk Management

### Web Scraping Reliability
- **Mitigation**: Single source (BBC Sport) for simplicity
- **Monitoring**: Weekly scraping success tracking
- **Fallback**: Manual fixture entry if scraping fails
- **Maintenance**: Monitor BBC website structure changes

### API Limitations (Minimized)
- **Mitigation**: Live scores only (12-16 calls/month vs 48)
- **Monitoring**: Real-time usage tracking
- **Fallback**: Cached scores if API fails temporarily

### Match Availability
- **Challenge**: Getting reliable Saturday 3pm fixtures data
- **Solution**: BBC Sport scraping with validation
- **Coverage**: All 8 England/Scotland leagues
- **Schedule**: Weekly scraping (Friday evenings)

## Success Metrics

### Technical Metrics
- [ ] API calls: <20 per month (target: 12-16) - 75% reduction achieved
- [ ] Scraping success rate: >95% for weekly fixture updates
- [ ] Event detection: 100% reliable KO/HT/FT recognition
- [ ] BTTS detection: Real-time goal event monitoring
- [ ] Cache hit rate: >90% (different TTL for different data types)
- [ ] Page load time: <2 seconds

### User Experience Metrics
- [ ] Admin setup time: <3 minutes per week (automated scraping)
- [ ] Match selection: One-click selection from scraped fixtures
- [ ] Scoreboard clarity: Easy to read BTTS status
- [ ] Mobile responsiveness: Works on all devices
- [ ] Reliability: 99% uptime during match days

## Future Enhancements (Post-MVP)

### Phase 2 Features
- [ ] Historical results tracking
- [ ] Performance analytics per selector
- [ ] Notification system for BTTS success
- [ ] Export functionality for betting records

### Scaling Considerations
- [ ] API upgrade path ($5-10/month for higher limits)
- [ ] Multi-league support beyond England/Scotland
- [ ] Additional accumulator types (not just BTTS)

## Development Guidelines

### Code Standards
- **Simplicity First**: Clean, readable code over complex features
- **Mobile Responsive**: Works on phones and tablets
- **Error Handling**: Graceful degradation when API fails
- **Performance**: Fast loading and responsive updates

### API Management
- **Call Minimization**: Every call must be necessary
- **Caching Strategy**: Cache aggressively to reduce API usage
- **Error Recovery**: Retry failed calls with exponential backoff
- **Usage Monitoring**: Track calls in real-time

## Deployment Strategy

### Initial Deployment
- **Local Development**: Run on development machine
- **Simple Hosting**: PythonAnywhere or Heroku free tier
- **Domain**: Subdomain or free hosting service

### Production Considerations
- **SSL Certificate**: For secure admin access
- **Backup Strategy**: Regular JSON file backups
- **Monitoring**: Basic uptime and error tracking

## Key Optimizations Implemented

### Hybrid Architecture Benefits
- **75% API Reduction**: From 48 to 12-16 calls per month
- **Zero-Cost Fixtures**: Web scraping eliminates fixture API costs
- **Simplified Maintenance**: Single BBC source for all leagues
- **Enhanced Reliability**: Multiple data sources with fallbacks
- **Better Performance**: Optimized caching with different TTL strategies

### Architecture Evolution
- **Before**: Sofascore API for everything (48 calls/month)
- **After**: BBC scraping + Sofascore live scores only (12-16 calls/month)

---

**Project Status**: Planning Complete | Ready for Implementation
**Last Updated**: October 2025 (Hybrid Architecture Update)
**Maintainer**: Development Team