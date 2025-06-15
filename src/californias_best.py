"""
Search for available campsites across multiple recreation areas and send email notifications.
Following a 4-step process:
1. Get full list of bookable Campsites by recreation area
2. Search available dates within the search window
3. Build results with:
-  summary counts by recarea per date
-  list of available campsites ordered by rec area, campground, campsite with list of availale dates
4. If any 1 campsite is available, email HTML in notification
"""

from datetime import datetime, timedelta
import logging
from typing import List, Dict, Union
from collections import defaultdict
import pandas as pd
from jinja2 import Template
import argparse
import json
import os
from pathlib import Path
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

from camply.containers import AvailableCampsite, SearchWindow
from camply.config import EquipmentOptions
from camply.search import SearchRecreationDotGov, SearchReserveCalifornia
from generate_index import generate_index_html
from regenerate_reports import regenerate_reports

# Recreation areas we want to search, organized by provider
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

# Available providers
AVAILABLE_PROVIDERS = list(REC_AREAS.keys())
DEFAULT_PROVIDER = "ReserveCalifornia"

# Configure logging
logging.basicConfig(
    format="%(asctime)s [%(levelname)8s]: %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def parse_date(date_str: str) -> datetime:
    """Parse date string in YYYY-MM-DD format."""
    return datetime.strptime(date_str, "%Y-%m-%d")

def get_search_window(start_date: str, end_date: str) -> SearchWindow:
    """Create search window from command line arguments."""
    return SearchWindow(
        start_date=datetime.strptime(start_date, "%Y-%m-%d"),
        end_date=datetime.strptime(end_date, "%Y-%m-%d")
    )

def get_default_dates():
    """Get default start and end dates (today + 7 days)."""
    start_date = datetime.now()
    end_date = start_date + timedelta(days=7)
    return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")

def get_providers(provider_ids: List[str] = None) -> Dict:
    """
    Get provider configurations based on provider IDs.
    If no providers specified, returns ReserveCalifornia only.
    """
    if not provider_ids:
        return {DEFAULT_PROVIDER: REC_AREAS[DEFAULT_PROVIDER]}
    
    # Validate provider IDs
    invalid_providers = set(provider_ids) - set(AVAILABLE_PROVIDERS)
    if invalid_providers:
        raise ValueError(f"Invalid provider(s): {', '.join(invalid_providers)}. "
                        f"Available providers: {', '.join(AVAILABLE_PROVIDERS)}")
    
    return {pid: REC_AREAS[pid] for pid in provider_ids}

def build_results_summary(matches: List[AvailableCampsite], rec_area_name: str, provider_name: str, rec_area_id: str) -> Dict:
    """
    Build summary of available campsites grouped by date.
    Structure:
    {
        "runtime": "2024-03-21T15:30:45",
        "provider": {
            "name": "Recreation.gov",
            "id": "RecreationDotGov"
        },
        "rec_area_name": "Yosemite National Park",
        "rec_area_id": "1234567890",
        "total_sites": 42,
        "available_sites": {
            "campground_name": {
                "campground_id": "1234567890",
                "campground_name": "the name",
                "location": {
                    "latitude": 37.8651,
                    "longitude": -119.5383
                },
                "campsites": {
                    "campsite_name": {
                        "campsite_id": "1234567890",
                        "campsite_name": "the name",
                        "dates": ["2025-06-13", "2025-06-14"],
                        "booking_url": "https://...",
                        "location": {
                            "latitude": 37.8651,
                            "longitude": -119.5383
                        },
                        "amenities": {
                            "Campfire Allowed": "Yes",
                            "Picnic Table": "Yes",
                            ...
                        }
                    }
                }
            }
        },
        "all_amenities": {
            "Campfire Allowed": ["Yes", "No"],
            "Picnic Table": ["Yes", "No"],
            ...
        }
    }
    """
    available_sites = {}
    date_counts = defaultdict(int)
    all_amenities = defaultdict(set)
    
    for match in matches:
        date = match.booking_date.strftime("%Y-%m-%d")
        date_counts[date] += 1
        
        # Initialize nested structure if needed
        if match.facility_name not in available_sites:
            available_sites[match.facility_name] = {
                "campground_id": str(match.facility_id),
                "campground_name": match.facility_name,
                "location": None,  # Will be set when we find a campsite with location
                "campsites": {}
            }
        
        if match.campsite_site_name not in available_sites[match.facility_name]["campsites"]:
            available_sites[match.facility_name]["campsites"][match.campsite_site_name] = {
                "campsite_id": str(match.campsite_id),
                "campsite_name": match.campsite_site_name,
                "dates": [],
                "booking_url": match.booking_url,
                "location": None,  # Will be set if campsite has location
                "amenities": {}
            }
        
        # Add date to the campsite's list of available dates
        available_sites[match.facility_name]["campsites"][match.campsite_site_name]["dates"].append(date)
        
        # Update location information if available
        if match.location:
            # Update facility location if not set
            if not available_sites[match.facility_name]["location"]:
                available_sites[match.facility_name]["location"] = {
                    "latitude": match.location.latitude,
                    "longitude": match.location.longitude
                }
            
            # Update campsite location
            available_sites[match.facility_name]["campsites"][match.campsite_site_name]["location"] = {
                "latitude": match.location.latitude,
                "longitude": match.location.longitude
            }

        # Process amenities if available
        if match.campsite_attributes:
            amenities = available_sites[match.facility_name]["campsites"][match.campsite_site_name]["amenities"]
            for attr in match.campsite_attributes:
                if attr.attribute_name and attr.attribute_value:
                    amenities[attr.attribute_name] = attr.attribute_value
                    all_amenities[attr.attribute_name].add(attr.attribute_value)
    
    return {
        "runtime": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "provider": {
            "name": provider_name,
            "id": next(k for k, v in REC_AREAS.items() if v["provider_name"] == provider_name)
        },
        "rec_area_name": rec_area_name,
        "rec_area_id": str(rec_area_id),
        "total_sites": len(matches),
        "date_counts": dict(date_counts),
        "available_sites": available_sites,
        "all_amenities": {k: sorted(list(v)) for k, v in all_amenities.items()}
    }

def create_html_email(summaries: List[Dict], start_date: str, end_date: str) -> str:
    """
    Create HTML email from availability summaries using the template.
    """
    # Create templates directory if it doesn't exist
    template_dir = Path("src/templates")
    template_dir.mkdir(exist_ok=True)
    
    # Load template from file
    template_path = template_dir / "availability_report.html"
    with open(template_path) as f:
        template = Template(f.read())
    
    # Get Google Maps API key from environment
    load_dotenv()
    maps_api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    
    return template.render(
        summaries=summaries,
        start_date=start_date,
        end_date=end_date,
        maps_api_key=maps_api_key
    )

def save_rec_area_json(summary: Dict, start_date: str, end_date: str, html_content: str = None):
    """
    Save recreation area results to JSON and HTML files in the logs directory.
    """
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Create a filename safe version of the rec area name
    rec_area_name = summary["rec_area_name"].lower().replace(" ", "-").replace(",", "")
    base_filename = f"{rec_area_name}_{start_date}_to_{end_date}"
    
    # Save JSON
    json_filepath = log_dir / f"{base_filename}.json"
    with open(json_filepath, "w") as f:
        json.dump(summary, f, indent=2)
    logger.info(f"Saved JSON results for {summary['rec_area_name']} to {json_filepath}")
    
    # Save HTML if provided
    if html_content:
        # Add runtime comment to HTML
        runtime_comment = f"<!-- Report generated at: {summary['runtime']} -->"
        html_content = runtime_comment + "\n" + html_content
        
        html_filepath = log_dir / f"{base_filename}.html"
        with open(html_filepath, "w") as f:
            f.write(html_content)
        logger.info(f"Saved HTML report for {summary['rec_area_name']} to {html_filepath}")

def send_email(html_content: str, subject: str) -> None:
    """Send email using configuration from .env file."""
    # Load email configuration from .env
    load_dotenv()
    
    # Get email configuration
    smtp_server = os.getenv("EMAIL_SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("EMAIL_SMTP_PORT", "587"))
    username = os.getenv("EMAIL_USERNAME")
    password = os.getenv("EMAIL_PASSWORD")
    from_addr = os.getenv("EMAIL_FROM_ADDRESS", "eliabrahamtaylor@gmail.com")
    to_addr = os.getenv("EMAIL_TO_ADDRESS", "eliabrahamtaylor@gmail.com")
    
    # Validate required fields
    if not all([username, password]):
        raise ValueError(
            "Missing required email configuration. Please set EMAIL_USERNAME and "
            "EMAIL_PASSWORD in your .env file"
        )
    
    # Create email message
    msg = EmailMessage()
    msg.set_content(html_content, subtype='html')
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr
    
    # Send email using TLS
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(username, password)
        server.send_message(msg)
    logger.info(f"Sent email notification to {to_addr}")

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Search for available campsites in multiple recreation areas")
    parser.add_argument("--start-date", help="Start date in YYYY-MM-DD format")
    parser.add_argument("--end-date", help="End date in YYYY-MM-DD format")
    parser.add_argument("--providers", nargs="+", choices=AVAILABLE_PROVIDERS,
                      help=f"Providers to search. Available: {', '.join(AVAILABLE_PROVIDERS)}. "
                           f"Default: {DEFAULT_PROVIDER}")
    args = parser.parse_args()

    # Use provided dates or defaults
    if not args.start_date or not args.end_date:
        args.start_date, args.end_date = get_default_dates()
        logger.info(f"Using default date range: {args.start_date} to {args.end_date}")

    search_window = get_search_window(args.start_date, args.end_date)
    all_summaries = []
    
    # Get selected providers
    providers = get_providers(args.providers)
    logger.info(f"Searching providers: {', '.join(p['provider_name'] for p in providers.values())}")
    
    # Search each provider
    for provider_id, provider_config in providers.items():
        provider_name = provider_config["provider_name"]
        search_class = provider_config["search_class"]
        
        for rec_area_id, rec_area_name in provider_config["areas"].items():
            logger.info(f"Searching {rec_area_name} via {provider_name}...")
            
            try:
                # Initialize provider-specific search class with required parameters
                try:
                    searcher = search_class(
                        search_window=search_window,
                        recreation_area=rec_area_id,
                        equipment=[EquipmentOptions.tent],  # Use enum value directly
                        weekends_only=True,  # Search all days
                        nights=1  # Minimum stay
                    )
                except SystemExit:
                    logger.error(f"Failed to initialize searcher for {rec_area_name} (ID: {rec_area_id})")
                    continue

                if not searcher or not searcher.get_matching_campsites:
                    logger.error(f"Recreation area not found: {rec_area_name} (ID: {rec_area_id})")
                    continue
                
                # Get matching campsites
                try:
                    matches = searcher.get_matching_campsites(
                        continuous=False,  # Don't require continuous stays
                        verbose=True,
                        log=True
                    )
                except SystemExit:
                    logger.error(f"No campsites found for {rec_area_name} (ID: {rec_area_id})")
                    continue
                
                if not matches:
                    logger.info(f"No matches found for {rec_area_name}")
                    continue
                    
                logger.info(f"Found {len(matches)} matches for {rec_area_name}")
                
                # Build summary for this recreation area
                summary = build_results_summary(
                    matches=matches,
                    rec_area_name=rec_area_name,
                    provider_name=provider_name,
                    rec_area_id=rec_area_id
                )
                all_summaries.append(summary)
                
                # Save individual recreation area results
                save_rec_area_json(
                    summary=summary,
                    start_date=args.start_date,
                    end_date=args.end_date
                )
            except Exception as e:
                logger.error(f"Error searching {rec_area_name}: {str(e)}")
                continue
    
    if not all_summaries:
        logger.info("No matches found for any recreation areas")
        return
    
    # Create HTML report
    html_content = create_html_email(
        summaries=all_summaries,
        start_date=args.start_date,
        end_date=args.end_date
    )
    
    combined_filename = f"combined_{args.start_date}_to_{args.end_date}"
    
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    html_path = output_dir / f"{combined_filename}.html"
    with open(html_path, "w") as f:
        f.write(html_content)
    logger.info(f"Saved combined HTML report to {html_path}")
    
    # Generate index
    regenerate_reports()
    generate_index_html()

if __name__ == "__main__":
    main()
