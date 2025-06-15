"""
Regenerate HTML reports from existing JSON files in the logs directory.
This is useful when making changes to the template without needing to recrawl the APIs.
"""

from pathlib import Path
import json
import os
from jinja2 import Template
from dotenv import load_dotenv
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    format="%(asctime)s [%(levelname)8s]: %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def create_html_report(summary: dict, start_date: str, end_date: str) -> str:
    """
    Create HTML report from a summary dictionary using the template.
    """
    # Load template
    template_dir = Path("src/templates")
    template_path = template_dir / "availability_report.html"
    
    with open(template_path) as f:
        template = Template(f.read())
    
    # Get Google Maps API key from environment
    load_dotenv()
    maps_api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    
    return template.render(
        summaries=[summary],  # Wrap in list to match original template structure
        start_date=start_date,
        end_date=end_date,
        maps_api_key=maps_api_key
    )

def regenerate_reports():
    """
    Find all JSON files in logs directory and regenerate their HTML counterparts.
    """
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Find all JSON files
    json_files = list(logs_dir.glob("*.json"))
    logger.info(f"Found {len(json_files)} JSON files to process")
    
    for json_file in json_files:
        try:
            # Read JSON data
            with open(json_file) as f:
                summary = json.load(f)
            
            # Extract dates from the first and last available dates
            start_date = min(summary['date_counts'].keys())
            end_date = max(summary['date_counts'].keys())
            
            # Generate HTML content
            html_content = create_html_report(summary, start_date, end_date)
            
            # Add runtime comment
            runtime_comment = f"<!-- Report regenerated at: {datetime.now().strftime('%Y-%m-%dT%H:%M:%S')} -->"
            html_content = runtime_comment + "\n" + html_content
            
            # Save HTML file
            html_file = json_file.with_suffix('.html')
            with open(html_file, "w") as f:
                f.write(html_content)
            
            logger.info(f"Regenerated HTML report for {summary['rec_area_name']}: {html_file}")
            
        except Exception as e:
            logger.error(f"Error processing {json_file}: {e}")
            continue
    
    # Regenerate index.html
    from generate_index import generate_index_html
    generate_index_html()
    logger.info("Regenerated index.html")

if __name__ == "__main__":
    regenerate_reports() 