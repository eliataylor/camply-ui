"""
Generate an index.html file that lists all HTML reports in the logs directory.
Uses JSON files as the source of truth for report metadata.
"""

from pathlib import Path
from datetime import datetime, timedelta
import json
from jinja2 import Template
import logging

# Configure logging
logging.basicConfig(
    format="%(asctime)s [%(levelname)8s]: %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def generate_index_html():
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Find all JSON files in logs directory
    json_files = list(logs_dir.glob("*.json"))
    
    # Parse information from JSON files
    reports = []
    for json_file in json_files:
        html_file = json_file.with_suffix('.html')
        
        # Skip if corresponding HTML file doesn't exist
        if not html_file.exists():
            continue
            
        try:
            with open(json_file) as f:
                data = json.load(f)
                
            # Convert runtime to display format
            if 'runtime' in data:
                runtime = datetime.strptime(data['runtime'], "%Y-%m-%dT%H:%M:%S")
            else:
                runtime = datetime.now() - timedelta(days=1)
            
            # Get provider name if available, otherwise use a default
            provider_name = data.get('provider', {}).get('name', 'Unknown Provider')
            
            reports.append({
                "filename": html_file.name,
                "area_name": data['rec_area_name'],
                "provider": provider_name,
                "runtime": runtime.strftime("%B %d, %Y %I:%M:%S %p"),
                "modified": datetime.fromtimestamp(html_file.stat().st_mtime).strftime("%B %d, %Y %I:%M %p"),
                # Extract dates from the first and last available dates
                "start_date": min(data['date_counts'].keys()),
                "end_date": max(data['date_counts'].keys())
            })
        except Exception as e:
            logger.error(f"Error processing {json_file}: {e}")
            continue
    
    # Sort reports by runtime (newest first)
    reports.sort(key=lambda x: x["runtime"], reverse=True)
    
    # Load template
    template_path = Path("src/templates/index_template.html")
    with open(template_path) as f:
        template = Template(f.read())
    
    # Generate HTML content
    html_content = template.render(reports=reports)
    
    # Write index.html
    index_path = logs_dir / "index.html"
    with open(index_path, "w") as f:
        f.write(html_content)
    
    logger.info(f"Generated index.html with {len(reports)} reports")

if __name__ == "__main__":
    generate_index_html() 