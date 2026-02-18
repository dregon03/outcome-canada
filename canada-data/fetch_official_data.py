"""
Fetch official Statistics Canada data for Outcome Canada indicators.
Uses direct API calls to Statistics Canada's Web Data Service with proper headers.
All vector IDs have been verified as of February 2026.
"""
import csv
import requests
import time
from pathlib import Path
from datetime import datetime

# Map indicators to their Statistics Canada vector IDs
# All vectors verified via API on 2026-02-09
VECTOR_MAP = {
    # ===== ECONOMIC INDICATORS - MONTHLY =====

    "gdp": {
        "vector": "v65201210",
        "name": "Real GDP",
        "table": "36-10-0434-01",
        "periods": 60,
    },
    "gdp_percapita": {
        "vector": "v1645315579",
        "name": "GDP per Capita",
        "table": "36-10-0706-01",
        "periods": 20,  # Quarterly
    },
    "inflation": {
        "vector": "v41690973",
        "name": "CPI All-items",
        "table": "18-10-0004-01",
        "periods": 300,  # ~25 years to show from index=100 (2002=100)
    },
    "cpi_shelter": {
        "vector": "v41691050",
        "name": "CPI Shelter",
        "table": "18-10-0004-01",
        "periods": 300,
    },
    "cpi_food": {
        "vector": "v41690974",
        "name": "CPI Food",
        "table": "18-10-0004-01",
        "periods": 300,
    },
    "cpi_transport": {
        "vector": "v41691128",
        "name": "CPI Transportation",
        "table": "18-10-0004-01",
        "periods": 300,
    },

    # Labour Market
    "unemployment": {
        "vector": "v2062815",
        "name": "Unemployment Rate",
        "table": "14-10-0287-01",
        "periods": 60,
    },
    "employment_rate": {
        "vector": "v2062817",
        "name": "Employment Rate",
        "table": "14-10-0287-01",
        "periods": 60,
    },
    "participation_rate": {
        "vector": "v2062816",
        "name": "Participation Rate",
        "table": "14-10-0287-01",
        "periods": 60,
    },
    "wages": {
        "vector": "v54027306",
        "name": "Average Weekly Earnings",
        "table": "14-10-0222-01",
        "periods": 60,
    },
    "hours_worked": {
        "vector": "v54027310",
        "name": "Average Weekly Hours",
        "table": "14-10-0222-01",
        "periods": 60,
    },
    "ei": {
        "vector": "v64549350",
        "name": "EI Beneficiaries",
        "table": "14-10-0011-01",
        "periods": 60,
    },
    "jobvacancy": {
        "vector": "v1212389467",
        "name": "Job Vacancy Rate",
        "table": "14-10-0372-01",
        "periods": 60,
    },

    # Housing
    "housing": {
        "vector": "v111955442",
        "name": "New Housing Price Index",
        "table": "18-10-0205-01",
        "periods": 120,  # ~10 years to show from index=100 (2017=100)
    },
    "housing_starts": {
        "vector": "v52300157",
        "name": "Housing Starts",
        "table": "34-10-0158-01",
        "periods": 60,
    },

    # Trade
    "trade": {
        "vector": "v87008984",
        "name": "Trade Balance",
        "table": "12-10-0011-01",
        "periods": 60,
    },
    "exports": {
        "vector": "v87008955",
        "name": "Merchandise Exports",
        "table": "12-10-0011-01",
        "periods": 60,
    },
    "imports": {
        "vector": "v87008839",
        "name": "Merchandise Imports",
        "table": "12-10-0011-01",
        "periods": 60,
    },

    # Business Activity
    "retail": {
        "vector": "v1446859483",
        "name": "Retail Sales",
        "table": "20-10-0056-01",
        "periods": 60,
    },
    "manufacturing": {
        "vector": "v800450",
        "name": "Manufacturing Sales",
        "table": "16-10-0047-01",
        "periods": 60,
    },

    # ===== DEMOGRAPHIC INDICATORS - QUARTERLY =====

    "population": {
        "vector": "v1",
        "name": "Total Population",
        "table": "17-10-0009-01",
        "periods": 20,
    },
    "immigration": {
        "vector": "v29850342",
        "name": "Immigrants",
        "table": "17-10-0040-01",
        "periods": 20,
    },
    "emigration": {
        "vector": "v29850343",
        "name": "Emigrants",
        "table": "17-10-0040-01",
        "periods": 20,
    },
    "business_investment": {
        "vector": "v62143982",
        "name": "Business Investment (Non-res)",
        "table": "36-10-0108-01",
        "periods": 20,
    },

    # ===== FINANCIAL INDICATORS - DAILY (fetch recent) =====

    "policy_rate": {
        "vector": "v39079",
        "name": "BoC Policy Rate",
        "table": "10-10-0139-01",
        "periods": 400,  # ~16 months of daily (for Y/Y comparison)
    },
    "bond_5y": {
        "vector": "v39053",
        "name": "5-Year Bond Yield",
        "table": "10-10-0139-01",
        "periods": 400,  # ~16 months of daily (for Y/Y comparison)
    },
    "bond_10y": {
        "vector": "v39055",
        "name": "10-Year Bond Yield",
        "table": "10-10-0139-01",
        "periods": 400,  # ~16 months of daily (for Y/Y comparison)
    },
}


def fetch_indicator_data(indicator_key, info):
    """Fetch data for a single indicator from Statistics Canada."""
    try:
        print(f"  Fetching {info['name']}...")

        # API endpoint and headers
        url = "https://www150.statcan.gc.ca/t1/wds/rest/getDataFromVectorsAndLatestNPeriods"

        # CRITICAL: These headers prevent HTTP 406 errors
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        # Request payload
        vector_id = int(info['vector'].replace('v', ''))
        periods = info['periods']

        payload = [
            {"vectorId": vector_id, "latestN": periods}
        ]

        # Make request
        response = requests.post(url, headers=headers, json=payload, timeout=30)

        if response.status_code != 200:
            print(f"    [ERROR] HTTP {response.status_code}: {response.text[:200]}")
            return None

        # Parse response
        result = response.json()

        if not result or len(result) == 0:
            print(f"    [WARNING] No data in response")
            return None

        # Handle nested response structure: [{"status": "...", "object": {...}}]
        response_item = result[0]

        # Check for errors in response
        if response_item.get('status') == 'FAILED':
            print(f"    [ERROR] API returned FAILED status")
            return None

        # Get the actual vector data object (nested inside "object" key)
        vector_data = response_item.get('object', {})

        # Extract data points
        data_points = vector_data.get('vectorDataPoint', [])

        if not data_points:
            print(f"    [WARNING] No data points returned")
            return None

        # Convert to date/value format
        data = []
        for point in data_points:
            ref_per = point.get('refPer')
            value = point.get('value')

            if ref_per and value is not None:
                # Convert refPer (e.g., "2024-01-01") to date string
                data.append({
                    'date': ref_per,
                    'value': float(value)
                })

        if not data:
            print(f"    [WARNING] No valid data points")
            return None

        # Sort by date
        data.sort(key=lambda x: x['date'])

        print(f"    [OK] Got {len(data)} data points (latest: {data[-1]['date']})")
        return data

    except Exception as e:
        print(f"    [ERROR] Failed to fetch {info['name']}: {e}")
        return None


def save_indicator_data(indicator_key, data):
    """Save indicator data to CSV file."""
    if not data:
        return False

    try:
        data_dir = Path(__file__).parent / indicator_key
        data_dir.mkdir(exist_ok=True)

        csv_path = data_dir / "official_data.csv"

        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['date', 'value'])
            writer.writeheader()
            writer.writerows(data)

        print(f"    [SAVED] {csv_path}")
        return True

    except Exception as e:
        print(f"    [ERROR] Failed to save {indicator_key}: {e}")
        return False


def main():
    """Fetch all indicator data from Statistics Canada."""
    print("=" * 60)
    print("  FETCHING OFFICIAL STATISTICS CANADA DATA")
    print("  All vectors verified 2026-02-09")
    print("=" * 60)
    print()

    success_count = 0
    fail_count = 0

    for key, info in VECTOR_MAP.items():
        # Fetch data
        data = fetch_indicator_data(key, info)

        # Save to CSV
        if data and save_indicator_data(key, data):
            success_count += 1
        else:
            fail_count += 1

        print()

        # Rate limiting: wait 2 seconds between requests to avoid connection resets
        time.sleep(2)

    print("=" * 60)
    print(f"  FETCH COMPLETE")
    print(f"  Success: {success_count} indicators")
    print(f"  Failed: {fail_count} indicators")
    print("=" * 60)


if __name__ == "__main__":
    main()
