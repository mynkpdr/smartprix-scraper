# Smartprix Product Scraper

A daily scraper that collects product specifications from Smartprix.com and saves them to CSV format. Supports multiple product categories including mobiles and laptops.

## Features

- Scrapes product data from Smartprix sitemaps (mobiles, laptops, etc.)
- Configurable product type via `PRODUCT_TYPE` environment variable
- Processes products in batches with progress tracking
- Organized file structure with category-specific folders
- Automatic daily runs via GitHub Actions for multiple product types
- Automatic dataset uploads to Kaggle
- Cloudflare bypass using cloudscraper

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the scraper:
   ```bash
   # Default (mobiles)
   python main.py
   
   # Specific product type
   set PRODUCT_TYPE=laptops
   python main.py
   ```

## Configuration

The scraper can be configured through environment variables:

- `PRODUCT_TYPE` - Product category to scrape (default: "mobiles")
  - Available: `mobiles`, `laptops`, and other Smartprix categories

## Output

- `data/{product_type}/{product_type}.csv` - Product specifications and details
- `data/{product_type}/{product_type}_progress.json` - Progress tracking to resume from last run

Examples:
- `data/mobiles/mobiles.csv` - Mobile phone specifications
- `data/laptops/laptops.csv` - Laptop specifications

## Data Structure

Each CSV contains the following key information:
- **Basic Info**: Name, Brand, Price, Price Drop details
- **Specifications**: Detailed specs organized by categories (Display, Performance, Camera, etc.)
- **Metadata**: Last modified date, related products
- **Flattened Format**: All specifications are flattened with dot notation (e.g., `Display.Screen Size`)

## Automation

The scraper runs automatically every day at 5 AM UTC via GitHub Actions workflow, processing both mobiles and laptops in separate jobs. After scraping, the datasets are automatically uploaded to Kaggle for public access.

### GitHub Actions Workflow
- **Mobiles job**: Scrapes mobile data and uploads to Kaggle
- **Laptops job**: Scrapes laptop data and uploads to Kaggle  
- **Sequential execution**: Laptops job runs after mobiles job completes

### Kaggle Integration
Requires `KAGGLE_USERNAME` and `KAGGLE_KEY` secrets configured in the repository settings.

## Troubleshooting

### Common Issues
- **Cloudflare blocks**: The scraper uses cloudscraper to bypass protection
- **Rate limiting**: Built-in 1-second delay between requests
- **Network errors**: Automatic retry logic handles temporary failures
- **Progress tracking**: Resumes from last successful scrape

### Manual Run
```bash
# Check progress
ls data/mobiles/

# Reset progress (will re-scrape all products)
rm data/mobiles/mobiles_progress.json
```