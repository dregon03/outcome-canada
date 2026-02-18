"""
Create sample data files for Outcome Canada website testing.
In production, this would fetch real data from Statistics Canada API.
"""
import csv
from pathlib import Path
from datetime import datetime, timedelta
import random

INDICATORS = {
    "gdp": {"sample_value": 2300000, "variance": 0.01},
    "inflation": {"sample_value": 165, "variance": 0.005},
    "unemployment": {"sample_value": 6.5, "variance": 0.02},
    "housing": {"sample_value": 122, "variance": 0.01},
    "trade": {"sample_value": 1800, "variance": 0.15},
    "retail": {"sample_value": 65000, "variance": 0.02},
    "manufacturing": {"sample_value": 70000, "variance": 0.02},
    "wages": {"sample_value": 1150, "variance": 0.005},
    "ei": {"sample_value": 420000, "variance": 0.03},
    "jobvacancy": {"sample_value": 2.6, "variance": 0.05},
    "population": {"sample_value": 40000000, "variance": 0.001},
    "immigration": {"sample_value": 120000, "variance": 0.05},
}

def create_sample_data(indicator_key, info, n_periods=60):
    """Create sample time series data."""
    random.seed(hash(indicator_key))
    base_value = info['sample_value']
    variance = info['variance']
    points = []

    # Start from 5 years ago
    start_date = datetime.now() - timedelta(days=365 * 5)

    for i in range(n_periods):
        date = start_date + timedelta(days=30 * i)
        date_str = date.strftime('%Y-%m-01')

        # Add trend and random variation
        trend = 1 + (i / n_periods) * 0.1  # 10% growth over period
        variation = random.uniform(-variance, variance)
        value = base_value * trend * (1 + variation)

        points.append({
            'date': date_str,
            'value': round(value, 2)
        })

    return points

def main():
    print("=" * 60)
    print("  CREATING SAMPLE DATA FOR OUTCOME CANADA")
    print("=" * 60)
    print()

    data_dir = Path(__file__).parent

    for key, info in INDICATORS.items():
        print(f"{key}: Creating sample data...")

        # Create subdirectory
        indicator_dir = data_dir / key
        indicator_dir.mkdir(exist_ok=True)

        # Generate data
        data = create_sample_data(key, info, n_periods=60)

        # Save to CSV
        csv_path = indicator_dir / "official_data.csv"
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['date', 'value'])
            writer.writeheader()
            writer.writerows(data)

        print(f"  [OK] Saved {len(data)} points. Latest: {data[-1]['date']} = {data[-1]['value']}")

    print()
    print("=" * 60)
    print("  SAMPLE DATA CREATION COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()
