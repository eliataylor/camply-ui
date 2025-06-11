# Campsite Availability Tracker

This directory contains scripts for tracking and reporting campsite availability across multiple providers (Recreation.gov, ReserveCalifornia, etc.). The system generates interactive HTML reports that allow you to search, filter, and monitor available campsites.

## Scripts Overview

### 1. `californias-best.py`

The main script for searching campsite availability and generating detailed reports.

```bash
python californias-best.py --start-date YYYY-MM-DD --end-date YYYY-MM-DD
```

**Arguments:**
- `--start-date`: Start of the search window (format: YYYY-MM-DD)
- `--end-date`: End of the search window (format: YYYY-MM-DD)

**Features:**
- Searches multiple recreation areas and providers
- Generates detailed HTML reports with interactive filtering
- Includes maps and location data
- Shows amenity information for each campsite
- Supports filtering by amenities and provider
- Displays available dates for each campsite
- Provides direct booking links

### 2. `regenerate_reports.py`

Regenerates all HTML reports from existing data without performing new searches.

```bash
python regenerate_reports.py
```

**Use Cases:**
- Update report styling or layout
- Refresh reports after template changes
- Generate reports from cached data
- Quick report regeneration without new API calls

### 3. `generate_index.py`

Creates an index page that links to all generated availability reports.

```bash
python generate_index.py
```

**Features:**
- Lists all available reports
- Organizes reports by date
- Provides quick navigation to specific reports
- Shows report generation timestamps

## Report Features

The generated HTML reports include:

- **Provider Filtering**: Toggle between different booking providers
- **Location Jump**: Quick navigation to specific recreation areas or campgrounds
- **Amenity Filtering**: Filter campsites by available amenities
- **Interactive Maps**: View campground and campsite locations
- **Date Availability**: See available dates for each campsite
- **Direct Booking**: Links to book campsites directly
- **Responsive Design**: Works on desktop and mobile devices

## Directory Structure

```
favorites/
├── californias-best.py      # Main search and report generation script
├── regenerate_reports.py    # Report regeneration utility
├── generate_index.py        # Index page generator
└── templates/              # HTML templates for report generation
    └── availability_report.html  # Main report template
```

## Workflow Example

1. Search for available campsites:
```bash
python californias-best.py --start-date 2024-06-01 --end-date 2024-06-30
```

2. Regenerate reports with updated template:
```bash
python regenerate_reports.py
```

3. Create index page:
```bash
python generate_index.py
```

## Requirements

- Python 3.7+
- Required Python packages (install via pip):
  - requests
  - jinja2
  - pandas
  - beautifulsoup4

## Notes

- Reports are generated in the `output/` directory
- Maps require a valid Google Maps API key
- Some providers may have rate limits on their APIs
- Search windows are typically limited to 6 months
- Report regeneration uses cached search results 