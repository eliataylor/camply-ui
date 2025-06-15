## Install:
- chmod +x setup_env.sh
- ./setup_env.sh


## Configure Search Targets / Providers

The recreation areas to search are defined in `src/californias_best.py` in the `REC_AREAS` dictionary. This dictionary organizes search targets by provider:

```python
REC_AREAS = {
    "RecreationDotGov": {
        "provider_name": "Recreation.gov",
        "search_class": SearchRecreationDotGov,
        "areas": {
            2991: "Yosemite National Park",
            1073: "Shasta-Trinity National Forest, CA",
            1077: "Tahoe National Forest, CA",
            2025: "Lake Tahoe Basin Management Unit, CA"
        }
    },
    "ReserveCalifornia": {
        "provider_name": "ReserveCalifornia",
        "search_class": SearchReserveCalifornia,
        "areas": {
            713: "Hearst San Simeon SP",
            728: "Tahoe SRA, Tahoe City, CA",
            640: "Donner Memorial SP",
            641: "Emerald Bay SP",
            690: "Pfeiffer Big Sur SP",
            661: "Julia Pfeiffer Burns SP",
            718: "Bodega Dunes SP",
            17: "Lake Berryessa SP",
            628: "Clear Lake SP"
        }
    }
}
```

To modify the search targets, edit the `REC_AREAS` dictionary in `src/californias_best.py`
To find recreation area IDs:
- For Recreation.gov: Visit recreation.gov and note the ID from the URL when viewing a recreation area
- For ReserveCalifornia: Visit reservecalifornia.com and note the ID from the URL when viewing a park

Note: The script will search all recreation areas defined in `REC_AREAS` unless you specify providers using the `--providers` option.

## Usage

Run the script with default settings (searches for tent sites on weekends over next 7 days):

```bash
python src/californias_best.py 
```

### Command Line Options

The script supports several command line options to customize the search:

#### Date Range
- `--start-date YYYY-MM-DD`: Start date for search window (default: today)
- `--end-date YYYY-MM-DD`: End date for search window (default: today + 7 days)

#### Search Parameters
- `--equipment {tent,rv,trailer,car,van}`: Type of equipment to search for (default: tent)
- `--weekends-only`: Only search for weekend availability (default: True)
- `--no-weekends-only`: Search all days of the week
- `--nights N`: Minimum number of consecutive nights to search (default: 1)

#### Provider Selection
- `--providers {RecreationDotGov,ReserveCalifornia}`: Providers to search (default: ReserveCalifornia)

### Examples

Search for RV sites on weekends with 2-night minimum:
```bash
python src/californias_best.py --equipment tent --nights 2
```

Search for tent sites on all days:
```bash
python src/californias_best.py --no-weekends-only
```

Search specific date range with multiple providers:
```bash
python src/californias_best.py --start-date 2025-06-20 --end-date 2025-09-08 --providers RecreationDotGov ReserveCalifornia
```

Combine multiple options:
```bash
python src/californias_best.py --equipment rv --nights 2 --no-weekends-only --start-date 2025-06-20 --end-date 2025-09-08
```

## Output

The script generates two types of output files in the `logs` directory:

1. Individual recreation area reports:
   - JSON file: `{rec_area_name}_{start_date}_to_{end_date}.json`
   - HTML file: `{rec_area_name}_{start_date}_to_{end_date}.html`

2. Combined report:
   - HTML file: `combined_{start_date}_to_{end_date}.html`

The HTML reports include:
- Interactive maps showing campground locations
- Detailed availability information
- Links to booking pages
- Amenity information