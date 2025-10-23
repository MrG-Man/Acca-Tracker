# Modern Acca Tracker Interface

## Overview
A modern, single-page interface for the Acca-Tracker application featuring a sleek 2025 design with glassmorphism effects, smooth animations, and mobile-first responsive design.

## Features

### 🎨 Modern Design System
- **Glassmorphism Effects**: Translucent cards with backdrop blur
- **Gradient Accents**: Beautiful color gradients throughout
- **Smooth Animations**: Polished transitions and micro-interactions
- **Modern Typography**: Inter font family with proper hierarchy
- **Color-Coded Status**: Visual indicators for success, pending, and failed states

### 📱 Single-Page Experience
The interface is organized into three main sections accessible via tabs:

#### 1. Dashboard
- **Hero Statistics**: Total selections, BTTS success, pending, and failed matches
- **Progress Indicators**: Circular progress ring showing completion percentage
- **Quick Actions**: Fast navigation to other sections
- **Accumulator Status**: Real-time status of the accumulator bet

#### 2. Selection (Admin)
- **Match Assignment**: Assign matches to selectors with a clean interface
- **Selector Cards**: Visual representation of all selectors and their assignments
- **Available Matches**: Grid of matches ready to be assigned
- **Progress Tracking**: Visual progress bar showing assignment completion

#### 3. Live Tracker
- **Real-time Updates**: Auto-refresh every 30 seconds (toggleable)
- **Live Match Cards**: Color-coded cards showing match status
- **BTTS Detection**: Instant visual feedback when both teams score
- **Score Display**: Large, easy-to-read scores with match time

### 📱 Mobile Optimization
- **Responsive Grid**: Adapts from 1-4 columns based on screen size
- **Bottom Navigation**: Mobile-friendly tab navigation at the bottom
- **Touch-Friendly**: All buttons and interactive elements are 44px minimum
- **Optimized Layout**: Single-column layout on mobile devices

## File Structure

```
templates/
└── modern-tracker.html          # Main HTML template

static/
├── css/
│   └── modern-tracker.css       # Modern styling with CSS variables
└── js/
    └── modern-tracker.js        # Single-page app logic
```

## Routes

- `/` - Redirects to `/modern`
- `/modern` - Main modern interface
- `/admin` - Legacy admin interface (still available)
- `/btts-tracker` - Legacy tracker interface (still available)

## API Endpoints Used

- `GET /api/tracker-data` - Complete tracker data with selections
- `GET /api/selections` - Current week's selections
- `GET /api/bbc-fixtures` - Available matches for selection
- `GET /api/btts-status` - Live BTTS status for all matches
- `POST /api/assign` - Assign a match to a selector
- `POST /api/unassign` - Unassign a match from a selector

## Design System

### Color Palette
- **Primary**: #2563eb (Modern Blue)
- **Success**: #10b981 (Emerald Green)
- **Warning**: #f59e0b (Amber)
- **Danger**: #ef4444 (Red)
- **Live**: #8b5cf6 (Purple)

### Typography
- **Font Family**: Inter (sans-serif)
- **Monospace**: JetBrains Mono (for scores)

### Spacing Scale
- XS: 0.25rem
- SM: 0.5rem
- MD: 1rem
- LG: 1.5rem
- XL: 2rem
- 2XL: 3rem

### Border Radius
- SM: 0.375rem
- MD: 0.5rem
- LG: 0.75rem
- XL: 1rem
- Full: 9999px

## Key Features

### Auto-Refresh
- Automatically refreshes data every 30 seconds
- Can be toggled on/off in the Live Tracker section
- Updates connection status indicator

### Toast Notifications
- Success, error, and info messages
- Auto-dismiss after 3 seconds
- Positioned in top-right corner

### Modal Dialogs
- Match assignment modal with selector dropdown
- Glassmorphism effect with backdrop blur
- Click outside to close

### Connection Status
- Visual indicator in header
- Shows connected, disconnected, or loading states
- Animated pulse effect when loading

## Browser Support
- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers (iOS Safari, Chrome Mobile)

## Accessibility
- Semantic HTML structure
- ARIA labels where appropriate
- Keyboard navigation support
- High contrast color combinations

## Performance
- Optimized CSS with CSS variables
- Efficient DOM updates
- Debounced auto-refresh
- Lazy loading of tab content

## Usage

1. **Navigate to the interface**: Visit `http://localhost:5001/modern`
2. **View Dashboard**: See overview statistics and quick actions
3. **Assign Matches**: Switch to Selection tab, click on available matches
4. **Track Live**: Switch to Live Tracker tab to see real-time BTTS status

## Customization

### Changing Colors
Edit CSS variables in `modern-tracker.css`:
```css
:root {
    --color-primary: #2563eb;
    --color-success: #10b981;
    /* ... more variables */
}
```

### Adjusting Refresh Interval
Edit `modern-tracker.js`:
```javascript
this.refreshInterval = 30000; // milliseconds
```

### Modifying Layout
The grid system is responsive and can be adjusted in CSS:
```css
.hero-stats {
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
}
```

## Future Enhancements
- [ ] WebSocket support for real-time updates
- [ ] Drag-and-drop match assignment
- [ ] Advanced filtering and sorting
- [ ] Export data functionality
- [ ] Dark mode toggle
- [ ] Celebration animations for BTTS success
- [ ] Sound notifications

## Troubleshooting

### Interface not loading
- Check that Flask server is running
- Verify all static files are in correct locations
- Check browser console for errors

### Data not updating
- Verify API endpoints are responding
- Check auto-refresh toggle is enabled
- Ensure backend services are running

### Mobile layout issues
- Clear browser cache
- Check viewport meta tag is present
- Verify CSS media queries are loading

## Credits
- Design: Kombai AI
- Framework: Vanilla JavaScript
- Styling: Modern CSS with Glassmorphism
- Icons: Unicode Emoji
- Fonts: Google Fonts (Inter, JetBrains Mono)