"""
Extract latest official Statistics Canada data from cached files
and create simple CSV files for the website.
"""
import csv
import pandas as pd
from pathlib import Path
from datetime import datetime

CODES_DIR = Path(__file__).parent.parent

# Mapping of indicator keys to their column names in statcan_raw.csv
INDICATOR_COLUMNS = {
    "gdp": {"col": "gdp_monthly", "name": "GDP", "quarterly": True},
    "inflation": {"col": "cpi", "name": "CPI"},
    "unemployment": {"col": "unemployment_rate", "name": "Unemployment"},
    "housing": {"col": "nhpi_house_only", "name": "Housing"},
    "trade": {"col": "trade_balance", "name": "Trade"},
    "retail": {"col": "retail_sales", "name": "Retail"},
    "manufacturing": {"col": "manufacturing_sales", "name": "Manufacturing"},
    "wages": {"col": "avg_weekly_earnings", "name": "Wages"},
    "ei": {"col": "ei_beneficiaries", "name": "EI"},
    "jobvacancy": {"col": "job_vacancy_rate", "name": "Job Vacancy", "quarterly": True},
    "population": {"col": "population", "name": "Population", "quarterly": True},
    "immigration": {"col": "immigrants", "name": "Immigration", "quarterly": True},
}

def get_latest_official_value(indicator_key, nowcast_folder):
    """Get the latest official Statistics Canada value for an indicator."""
    statcan_file = CODES_DIR / f"canadian-{indicator_key}-nowcast" / "cache" / "statcan_raw.csv"

    if not statcan_file.exists():
        print(f"Warning: {statcan_file} not found")
        return None

    # Read the CSV
    df = pd.read_csv(statcan_file)

    # Get the column name for this indicator
    col_info = INDICATOR_COLUMNS.get(indicator_key, {})
    col_name = col_info.get("col")

    if not col_name or col_name not in df.columns:
        print(f"Warning: Column {col_name} not found in {statcan_file}")
        return None

    # Remove rows where the target column is NaN
    df_clean = df[df[col_name].notna()].copy()

    if len(df_clean) == 0:
        print(f"Warning: No valid data for {indicator_key}")
        return None

    # Get the last row with valid data
    latest = df_clean.iloc[-1]
    latest_date = pd.to_datetime(latest['date'])
    latest_value = float(latest[col_name])

    # Calculate growth rates
    is_quarterly = col_info.get("quarterly", False)

    if is_quarterly:
        # For quarterly data
        if len(df_clean) >= 2:
            prev_value = df_clean.iloc[-2][col_name]
            qoq_growth = ((latest_value / prev_value) - 1) * 100 if prev_value != 0 else 0
        else:
            qoq_growth = 0

        if len(df_clean) >= 5:
            year_ago_value = df_clean.iloc[-5][col_name]
            yoy_growth = ((latest_value / year_ago_value) - 1) * 100 if year_ago_value != 0 else 0
        else:
            yoy_growth = 0

        period = f"{latest_date.year}-Q{(latest_date.month-1)//3 + 1}"
        return {
            'date': latest_date.strftime('%Y-%m-%d'),
            'period': period,
            'value': latest_value,
            'qoq': qoq_growth,
            'yoy': yoy_growth
        }
    else:
        # For monthly data
        if len(df_clean) >= 2:
            prev_value = df_clean.iloc[-2][col_name]
            mom_growth = ((latest_value / prev_value) - 1) * 100 if prev_value != 0 else 0
        else:
            mom_growth = 0

        if len(df_clean) >= 13:
            year_ago_value = df_clean.iloc[-13][col_name]
            yoy_growth = ((latest_value / year_ago_value) - 1) * 100 if year_ago_value != 0 else 0
        else:
            yoy_growth = 0

        period = latest_date.strftime('%Y-%m')
        return {
            'date': latest_date.strftime('%Y-%m-%d'),
            'period': period,
            'value': latest_value,
            'mom': mom_growth,
            'yoy': yoy_growth
        }

def main():
    """Extract latest official data for all indicators."""
    print("=" * 60)
    print("  EXTRACTING OFFICIAL STATISTICS CANADA DATA")
    print("=" * 60)

    data_dir = Path(__file__).parent

    for key, info in INDICATOR_COLUMNS.items():
        print(f"\n{info['name']}:")

        # Get latest official value
        latest = get_latest_official_value(key, info['name'])

        if latest:
            print(f"  Latest official date: {latest['period']}")
            print(f"  Value: {latest['value']:.2f}")

            # Write to latest.csv
            latest_file = data_dir / key / "latest.csv"
            with open(latest_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=latest.keys())
                writer.writeheader()
                writer.writerow(latest)
            print(f"  ✓ Wrote {latest_file}")
        else:
            print(f"  ✗ No data found")

    print("\n" + "=" * 60)
    print("  EXTRACTION COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()
