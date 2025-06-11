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
from camply.search import SearchRecreationDotGov, SearchReserveCalifornia
from favorites.generate_index import generate_index_html

# Recreation areas we want to search, organized by provider
REC_AREAS = {
    "RecreationDotGov": {
        "provider_name": "Recreation.gov",
        "areas": {
            2991: "Yosemite National Park",
            1073: "Shasta-Trinity National Forest, CA",
            1077: "Tahoe National Forest, CA",
            2025: "Lake Tahoe Basin Management Unit, CA"
        }
    },
    "ReserveCalifornia": {
        "provider_name": "ReserveCalifornia",
        "areas": {
            728: "Tahoe SRA, Tahoe City, CA",
            640: "Donner Memorial SP",
            641: "Emerald Bay SP",
            1097: "Burton Creek SP"
        }
    }
}

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
    template_dir = Path("favorites/templates")
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
    runtime = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_filename = f"{rec_area_name}_{start_date}_to_{end_date}_{runtime}"
    
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
    args = parser.parse_args()

    # Use provided dates or defaults
    if not args.start_date or not args.end_date:
        args.start_date, args.end_date = get_default_dates()
        logger.info(f"Using default date range: {args.start_date} to {args.end_date}")

    search_window = get_search_window(args.start_date, args.end_date)
    all_summaries = []
    
    for provider_id, provider_data in REC_AREAS.items():
        logger.info(f"Searching provider: {provider_data['provider_name']}")
        
        # Select the appropriate search class based on provider
        if provider_id == "RecreationDotGov":
            SearchClass = SearchRecreationDotGov
        elif provider_id == "ReserveCalifornia":
            SearchClass = SearchReserveCalifornia
        else:
            logger.warning(f"Unknown provider {provider_id}, skipping...")
            continue
            
        for rec_area_id, rec_area_name in provider_data["areas"].items():
            logger.info(f"Searching {rec_area_name} (ID: {rec_area_id})")
            
            try:
                # Step 1: Get bookable campsites
                camping_finder = SearchClass(
                    search_window=search_window,
                    recreation_area=rec_area_id,            
                    equipment=[("Tent", None)],
                    weekends_only=True,
                    nights=1  # 1-night minimum stay
                )
                
                # Step 2: Search available dates
                matches = camping_finder.get_matching_campsites(
                    log=True,
                    verbose=True,
                    continuous=False
                )
                
                # Step 3: Build results summary
                if matches:
                    summary = build_results_summary(
                        matches, 
                        rec_area_name,
                        provider_data["provider_name"],
                        rec_area_id
                    )
                    all_summaries.append(summary)
                    
                    # Create HTML content for this recreation area
                    html_content = create_html_email([summary], args.start_date, args.end_date)
                    
                    # Save both JSON and HTML reports
                    save_rec_area_json(summary, args.start_date, args.end_date, html_content)
                    
                    # Send email for this recreation area
                    try:
                        subject = f"Campsite Alert: {len(matches)} sites available at {rec_area_name} ({args.start_date} to {args.end_date})"
                        send_email(html_content, subject)
                        logger.info(f"Sent email notification for {rec_area_name}")
                    except Exception as e:
                        logger.error(f"Failed to send email for {rec_area_name}: {e}")
                    
                    logger.info(f"Found {len(matches)} available sites in {rec_area_name}")
                else:
                    logger.info(f"No available sites found in {rec_area_name}")
                    
            except Exception as e:
                logger.error(f"Error searching {rec_area_name}: {e}")
                continue
    
    # If we have results from multiple areas, create a combined report
    if len(all_summaries) > 1:
        combined_html = create_html_email(all_summaries, args.start_date, args.end_date)
        try:
            subject = f"Campsite Alert: Multiple Areas ({args.start_date} to {args.end_date})"
            send_email(combined_html, subject)
            logger.info("Sent combined email notification")
        except Exception as e:
            logger.error(f"Failed to send combined email: {e}")
    
    # Generate index.html after all reports are created
    generate_index_html()

if __name__ == "__main__":
    main()
