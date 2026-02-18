"""
Static Site Generator for outcomecanada.ca

Displays latest available data from Statistics Canada across 27 key Canadian indicators
and generates a static website with:
  - Home page: overview dashboard with all indicators
  - Category pages: indicators organized by theme
  - Individual indicator pages: summary, chart, data sources
"""
import csv
import json
import shutil
from pathlib import Path
from datetime import datetime
from indicators_config import INDICATORS, CATEGORIES
from ministers_config import MINISTERS

CODES_DIR = Path(__file__).parent
SITE_DIR = Path(__file__).parent / "site"

# Load fresh minister data from daily fetch (if available)
_MINISTER_JSON_PATH = CODES_DIR / "canada-data" / "minister-data" / "minister_latest.json"
MINISTER_FRESH_DATA = {}
if _MINISTER_JSON_PATH.exists():
    try:
        with open(_MINISTER_JSON_PATH, "r", encoding="utf-8") as _f:
            _minister_json = json.load(_f)
            MINISTER_FRESH_DATA = _minister_json.get("metrics", {})
            print(f"  Loaded {len(MINISTER_FRESH_DATA)} fresh minister metrics from minister_latest.json")
    except Exception as _e:
        print(f"  Warning: Could not load minister_latest.json: {_e}")

# Preserve original INDICATORS for backwards compatibility (will be overridden by import)
_ORIGINAL_INDICATORS = {
    "gdp": {
        "name": "GDP Growth",
        "category": "Economic",
        "unit": "% annualized",
        "frequency": "Quarterly",
        "source": "Statistics Canada",
        "table": "36-10-0434-01",
        "project": "canadian-gdp-nowcast",
        "csv_file": "nowcast_history.csv",
        "value_col": "growth_annualized",
        "secondary_col": "growth_monthly",
        "secondary_label": "Monthly",
        "secondary_unit": "%",
        "period_col": "target_quarter",
        "description": "Real Gross Domestic Product growth measures the pace of economic expansion. "
                       "A positive rate signals economic expansion; negative indicates contraction.",
        "methodology": (
            "GDP data is sourced from Statistics Canada Table 36-10-0434-01, which provides monthly "
            "estimates of real GDP by industry. The data represents the actual output of the Canadian "
            "economy across all sectors. Growth rates are calculated as annualized percentage changes "
            "from the previous period, providing insight into the pace of economic expansion or contraction. "
            "This indicator is fundamental for understanding Canada's overall economic health and is "
            "released monthly, typically 60 days after the reference period."
        ),
    },
    "inflation": {
        "name": "Inflation (CPI)",
        "category": "Economic",
        "unit": "% y/y",
        "frequency": "Monthly",
        "source": "Statistics Canada",
        "table": "18-10-0004-01",
        "project": "canadian-inflation-nowcast",
        "csv_file": "nowcast_history.csv",
        "value_col": "inflation_yoy",
        "secondary_col": "inflation_annualized",
        "secondary_label": "Annualized",
        "secondary_unit": "%",
        "period_col": "target_month",
        "description": "Consumer Price Index inflation tracks the rate of change in the cost of a "
                       "basket of goods and services. The Bank of Canada targets 2% inflation.",
        "methodology": (
            "CPI data comes from Statistics Canada Table 18-10-0004-01, which measures price changes "
            "for a fixed basket of consumer goods and services. This includes food, shelter, transportation, "
            "clothing, and other household expenses. The year-over-year inflation rate shows how consumer "
            "prices have changed compared to the same month last year. CPI is Canada's most closely watched "
            "inflation indicator and is released monthly, typically 3 weeks after the reference period."
        ),
    },
    "unemployment": {
        "name": "Unemployment Rate",
        "category": "Economic",
        "unit": "%",
        "frequency": "Monthly",
        "source": "Statistics Canada",
        "table": "14-10-0287-01",
        "project": "canadian-unemployment-nowcast",
        "csv_file": "nowcast_history.csv",
        "value_col": "rate",
        "secondary_col": "monthly_change",
        "secondary_label": "Monthly Change",
        "secondary_unit": "pp",
        "period_col": "target_month",
        "description": "The unemployment rate measures the share of the labour force that is jobless "
                       "and actively seeking employment. It is a key indicator of labour market health.",
        "methodology": (
            "Unemployment data is sourced from Statistics Canada's Labour Force Survey (Table 14-10-0287-01), "
            "which surveys approximately 56,000 households monthly. The unemployment rate represents the "
            "percentage of the labour force that is actively seeking work but currently without employment. "
            "This indicator provides crucial insight into labour market conditions and economic health. "
            "The data is released monthly, typically on the first Friday after the reference period ends."
        ),
    },
    "housing": {
        "name": "Housing Prices (NHPI)",
        "category": "Economic",
        "unit": "% y/y",
        "frequency": "Monthly",
        "source": "Statistics Canada",
        "table": "18-10-0205-01",
        "project": "canadian-housing-nowcast",
        "csv_file": "nowcast_history.csv",
        "value_col": "hpi_yoy",
        "secondary_col": "hpi_annualized",
        "secondary_label": "Annualized",
        "secondary_unit": "%",
        "period_col": "target_month",
        "description": "The New Housing Price Index tracks changes in the selling prices of new "
                       "residential houses. It reflects builder pricing and housing market conditions.",
        "methodology": (
            "The New Housing Price Index is sourced from Statistics Canada Table 18-10-0205-01 and "
            "measures price changes for new residential houses where detailed specifications are "
            "available. The index reflects contractors' selling prices, capturing market conditions "
            "for newly built homes across Canadian markets. Year-over-year changes indicate housing "
            "price trends and market strength. Data is released monthly, approximately 10 days after "
            "the reference period."
        ),
    },
    "trade": {
        "name": "Trade Balance",
        "category": "Economic",
        "unit": "C$ millions",
        "frequency": "Monthly",
        "source": "Statistics Canada",
        "table": "12-10-0011-01",
        "project": "canadian-trade-nowcast",
        "csv_file": "nowcast_history.csv",
        "value_col": "balance_millions",
        "secondary_col": "monthly_change",
        "secondary_label": "Monthly Change",
        "secondary_unit": "C$ millions",
        "period_col": "target_month",
        "description": "The merchandise trade balance is the difference between exports and imports. "
                       "A positive balance (surplus) means Canada exports more than it imports.",
        "methodology": (
            "Trade balance data comes from Statistics Canada Table 12-10-0011-01, which tracks "
            "international merchandise trade. The balance is calculated as the difference between "
            "the value of goods exported from Canada and goods imported into Canada. A positive "
            "balance indicates a trade surplus, while negative indicates a deficit. This measure "
            "reflects Canada's international competitiveness and is released monthly, typically "
            "5 weeks after the reference period."
        ),
    },
    "retail": {
        "name": "Retail Sales",
        "category": "Economic",
        "unit": "% y/y",
        "frequency": "Monthly",
        "source": "Statistics Canada",
        "table": "20-10-0056-02",
        "project": "canadian-retail-nowcast",
        "csv_file": "nowcast_history.csv",
        "value_col": "retail_yoy",
        "secondary_col": "retail_annualized",
        "secondary_label": "Annualized",
        "secondary_unit": "%",
        "period_col": "target_month",
        "description": "Retail trade measures consumer spending at retail establishments. "
                       "It is a key indicator of consumer demand and economic activity.",
        "methodology": (
            "Retail sales data is sourced from Statistics Canada Table 20-10-0056-02, based on the "
            "Monthly Retail Trade Survey. This measures the total sales of retail stores across Canada, "
            "covering sectors like food, clothing, gasoline, and general merchandise. Year-over-year "
            "growth rates indicate consumer spending trends and economic strength. The data is released "
            "monthly, approximately 50 days after the reference period."
        ),
    },
    "manufacturing": {
        "name": "Manufacturing Sales",
        "category": "Economic",
        "unit": "% y/y",
        "frequency": "Monthly",
        "source": "Statistics Canada",
        "table": "16-10-0047-01",
        "project": "canadian-manufacturing-nowcast",
        "csv_file": "nowcast_history.csv",
        "value_col": "mfg_yoy",
        "secondary_col": "mfg_annualized",
        "secondary_label": "Annualized",
        "secondary_unit": "%",
        "period_col": "target_month",
        "description": "Manufacturing sales (shipments) measure the value of goods sold by "
                       "manufacturing establishments. It reflects industrial production and goods demand.",
        "methodology": (
            "Manufacturing sales data comes from Statistics Canada Table 16-10-0047-01, derived from "
            "the Monthly Survey of Manufacturing. This tracks the value of shipments from Canadian "
            "manufacturing plants across industries like food, chemicals, machinery, and vehicles. "
            "Year-over-year changes reflect industrial production trends and manufacturing sector health. "
            "Data is released monthly, typically 50 days after the reference period."
        ),
    },
    "wages": {
        "name": "Wage Growth",
        "category": "Economic",
        "unit": "% y/y",
        "frequency": "Monthly",
        "source": "Statistics Canada",
        "table": "14-10-0223-01",
        "project": "canadian-wage-nowcast",
        "csv_file": "nowcast_history.csv",
        "value_col": "wage_yoy",
        "secondary_col": "wage_annualized",
        "secondary_label": "Annualized",
        "secondary_unit": "%",
        "period_col": "target_month",
        "description": "Average weekly earnings measure wage growth across all industries. "
                       "Rising wages signal a tight labour market and can feed into inflation.",
        "methodology": (
            "Wage data is sourced from Statistics Canada Table 14-10-0223-01, based on the Survey of "
            "Employment, Payrolls and Hours (SEPH). This measures average weekly earnings including "
            "overtime for all employees across Canadian industries. Year-over-year wage growth indicates "
            "labour market tightness and income trends. The data is released monthly, approximately "
            "60 days after the reference period."
        ),
    },
    "ei": {
        "name": "EI Beneficiaries",
        "category": "Social",
        "unit": "% y/y",
        "frequency": "Monthly",
        "source": "Statistics Canada",
        "table": "14-10-0011-01",
        "project": "canadian-ei-nowcast",
        "csv_file": "nowcast_history.csv",
        "value_col": "ei_yoy",
        "secondary_col": "ei_annualized",
        "secondary_label": "Annualized",
        "secondary_unit": "%",
        "period_col": "target_month",
        "description": "Employment Insurance beneficiaries count Canadians receiving regular EI benefits. "
                       "Rising claims signal labour market deterioration and economic stress.",
        "methodology": (
            "EI beneficiaries data comes from Statistics Canada Table 14-10-0011-01, which counts "
            "the number of Canadians receiving regular Employment Insurance benefits. This indicator "
            "reflects labour market stress and economic conditions - rising beneficiary counts suggest "
            "increased job losses or difficulty finding work. Year-over-year changes show trends in "
            "labour market health. Data is released monthly, approximately 45 days after the reference period."
        ),
    },
    "jobvacancy": {
        "name": "Job Vacancy Rate",
        "category": "Social",
        "unit": "%",
        "frequency": "Monthly",
        "source": "Statistics Canada",
        "table": "14-10-0432-01",
        "project": "canadian-jobvacancy-nowcast",
        "csv_file": "nowcast_history.csv",
        "value_col": "vacancy_rate",
        "secondary_col": "vacancy_change",
        "secondary_label": "Monthly Change",
        "secondary_unit": "pp",
        "period_col": "target_month",
        "description": "The job vacancy rate measures unfilled positions as a share of total labour demand. "
                       "It reflects employer hiring intentions and labour market tightness.",
        "methodology": (
            "Job vacancy data is sourced from Statistics Canada Table 14-10-0432-01, based on the Job "
            "Vacancy and Wage Survey (JVWS). This measures the number of vacant positions as a percentage "
            "of total labour demand (employed + vacant positions). A higher rate indicates tight labour "
            "markets with many unfilled jobs, while lower rates suggest slack. The survey began in 2015 "
            "and data is released quarterly, approximately 60 days after the reference period."
        ),
    },
    "population": {
        "name": "Population Growth",
        "category": "Demographic",
        "unit": "% y/y",
        "frequency": "Quarterly",
        "source": "Statistics Canada",
        "table": "17-10-0009-01",
        "project": "canadian-population-nowcast",
        "csv_file": "nowcast_history.csv",
        "value_col": "pop_yoy",
        "secondary_col": "pop_qoq",
        "secondary_label": "Q/Q",
        "secondary_unit": "%",
        "period_col": "target_quarter",
        "description": "Population growth tracks changes in Canada's total population from births, deaths, "
                       "and net migration. It is a fundamental demographic indicator.",
        "methodology": (
            "Population data comes from Statistics Canada Table 17-10-0009-01, providing quarterly "
            "estimates of Canada's total population. This includes all Canadian residents and is "
            "updated based on births, deaths, immigration, and emigration. The population estimates "
            "are fundamental for understanding demographic trends, labour force growth, and economic "
            "planning. Data is released quarterly, approximately 90 days after the reference period."
        ),
    },
    "immigration": {
        "name": "Immigration Flows",
        "category": "Demographic",
        "unit": "% y/y",
        "frequency": "Quarterly",
        "source": "Statistics Canada",
        "table": "17-10-0040-01",
        "project": "canadian-immigration-nowcast",
        "csv_file": "nowcast_history.csv",
        "value_col": "imm_yoy",
        "secondary_col": "imm_qoq",
        "secondary_label": "Q/Q",
        "secondary_unit": "%",
        "period_col": "target_quarter",
        "description": "Immigration flows count the number of immigrants arriving in Canada each quarter. "
                       "Immigration is the primary driver of Canadian population growth.",
        "methodology": (
            "Immigration data is sourced from Statistics Canada Table 17-10-0040-01, which tracks "
            "the quarterly flow of immigrants landing in Canada. This includes economic immigrants, "
            "family class, refugees, and other categories. Immigration is the largest component of "
            "Canada's population growth and reflects both policy decisions and global migration trends. "
            "Data is released quarterly, approximately 120 days after the reference period."
        ),
    },
}

# INDICATORS and CATEGORIES are now imported from indicators_config.py
# This provides all 27 indicators across 7 categories


def read_official_data(indicator_key: str, indicator: dict) -> dict | None:
    """Read the latest official Statistics Canada values."""
    data_dir = CODES_DIR / "canada-data" / indicator_key
    csv_path = data_dir / "official_data.csv"

    if not csv_path.exists():
        print(f"  WARNING: {csv_path} not found")
        return None

    rows = []
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('value') and row['value'].strip():
                rows.append(row)

    if not rows:
        return None

    latest = rows[-1]

    try:
        latest_value = float(latest['value'])
        latest_date = latest["date"]

        # Calculate growth rates
        is_quarterly = indicator["frequency"] == "Quarterly"

        if is_quarterly:
            # Quarterly data
            period = latest_date[:4] + "-Q" + str((int(latest_date[5:7])-1)//3 + 1)

            # Q/Q growth
            if len(rows) >= 2:
                prev_value = float(rows[-2]['value'])
                qoq_growth = ((latest_value / prev_value) - 1) * 100 if prev_value != 0 else 0
            else:
                qoq_growth = None

            # Y/Y growth
            if len(rows) >= 5:
                year_ago_value = float(rows[-5]['value'])
                yoy_growth = ((latest_value / year_ago_value) - 1) * 100 if year_ago_value != 0 else 0
            else:
                yoy_growth = None

            # For level indicators like GDP per capita (C$ (2017)), show value and Y/Y growth
            if "C$" in indicator["unit"] or "dollars" in indicator["unit"].lower():
                return {
                    "date": latest_date,
                    "period": period,
                    "value": latest_value,
                    "secondary": yoy_growth,
                    "absolute": latest_value,
                    "yoy_growth": yoy_growth,
                }
            # For growth indicators, return Y/Y growth as main value
            else:
                return {
                    "date": latest_date,
                    "period": period,
                    "value": yoy_growth if yoy_growth is not None else qoq_growth,
                    "secondary": qoq_growth,
                    "absolute": latest_value,
                }
        else:
            # Monthly or Daily data
            is_daily = indicator["frequency"] == "Daily"
            period = latest_date if is_daily else latest_date[:7]

            # Determine lookback period for Y/Y calculation
            # Daily: look back ~252 trading days (approximate as 260 for safety)
            # Monthly: look back 13 months
            yoy_lookback = 260 if is_daily else 13

            # M/M or D/D growth (annualized for some indicators)
            if len(rows) >= 2:
                prev_value = float(rows[-2]['value'])
                mom_growth = ((latest_value / prev_value) - 1) * 100 if prev_value != 0 else 0
                mom_annualized = ((1 + mom_growth/100)**12 - 1) * 100 if not is_daily else None
            else:
                mom_growth = None
                mom_annualized = None

            # Y/Y growth or Y/Y percentage point change
            if len(rows) >= yoy_lookback:
                year_ago_value = float(rows[-yoy_lookback]['value'])
                yoy_growth = ((latest_value / year_ago_value) - 1) * 100 if year_ago_value != 0 else 0
                yoy_pp_change = latest_value - year_ago_value
            else:
                yoy_growth = None
                yoy_pp_change = None

            # For rate indicators (unemployment, job vacancy, policy rate, bonds), show level and Y/Y pp change
            if indicator["unit"] == "%":
                return {
                    "date": latest_date,
                    "period": period,
                    "value": latest_value,
                    "secondary": yoy_pp_change,
                    "absolute": latest_value,
                    "yoy_pp_change": yoy_pp_change,
                }
            # For trade balance, show the level in millions
            elif indicator["unit"] == "C$ millions":
                monthly_change = latest_value - float(rows[-2]['value']) if len(rows) >= 2 else None
                yoy_change = latest_value - float(rows[-13]['value']) if len(rows) >= 13 else None
                return {
                    "date": latest_date,
                    "period": period,
                    "value": latest_value,
                    "secondary": monthly_change,
                    "absolute": latest_value,
                    "yoy_change_millions": yoy_change,
                }
            # For level indicators like GDP per capita (C$ (2017)), show value and Y/Y growth
            elif "C$" in indicator["unit"] or "dollars" in indicator["unit"].lower():
                return {
                    "date": latest_date,
                    "period": period,
                    "value": latest_value,
                    "secondary": yoy_growth,
                    "absolute": latest_value,
                    "yoy_growth": yoy_growth,
                }
            # For growth indicators, show Y/Y growth
            else:
                return {
                    "date": latest_date,
                    "period": period,
                    "value": yoy_growth,
                    "secondary": mom_annualized,
                    "absolute": latest_value,
                }
    except (KeyError, ValueError, TypeError) as e:
        print(f"  ERROR processing {indicator_key}: {e}")
        return None


def read_chart_history(indicator_key: str, indicator: dict) -> list[dict]:
    """Read official data for chart generation."""
    data_dir = CODES_DIR / "canada-data" / indicator_key
    csv_path = data_dir / "official_data.csv"

    if not csv_path.exists():
        return []

    rows = []
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            date_str = row.get("date", "")
            val_str = row.get("value", "")
            if date_str and val_str and val_str.strip():
                try:
                    rows.append({"date": date_str, "value": float(val_str)})
                except ValueError:
                    pass

    return rows


def format_value(val, unit: str, use_arrow: bool = False) -> str:
    """Format a numeric value with its unit for display."""
    if val is None:
        return "N/A"
    if unit == "C$ millions":
        # Trade balance - display in billions
        val_b = val / 1_000  # millions -> billions
        return f"C${val_b:,.1f}B"
    elif unit == "C$ (2017)" or "C$" in unit:
        # GDP per capita - display in dollars
        return f"${val:,.0f}"
    elif unit == "%":
        # Level rates (unemployment, vacancy) — no +/- sign
        return f"{val:.1f}{unit}"
    elif unit in ("% y/y", "% annualized", "pp"):
        if use_arrow:
            arrow = "↑" if val >= 0 else "↓"
            # Remove unit suffix when using arrows (will be added separately)
            if unit == "pp":
                return f"{arrow} {abs(val):.1f} pp"
            else:
                return f"{arrow} {abs(val):.2f}%"
        else:
            # Convert abbreviated units to full text
            if unit == "% y/y":
                return f"{val:+.2f}% year over year"
            elif unit == "% annualized":
                return f"{val:+.2f}% annualized"
            elif unit == "pp":
                return f"{val:+.1f} percentage points"
    else:
        return f"{val:.2f}"


def format_absolute_value(val, indicator_key: str) -> str:
    """Format absolute values for display on cards."""
    if val is None:
        return "N/A"

    # GDP values - in millions, display as trillions
    if indicator_key == "gdp":
        return f"${val/1_000_000:,.2f}T"
    # GDP per capita - display as is
    elif indicator_key == "gdp_percapita":
        return f"${val:,.0f}"
    # Trade balance - in millions, display in billions
    elif indicator_key in ("trade", "exports", "imports"):
        return f"C${val/1_000:,.1f}B"
    # Retail and manufacturing - in thousands, display in billions
    elif indicator_key in ("retail", "manufacturing"):
        return f"C${val/1_000_000:,.1f}B"
    # Business investment - in millions, display in billions
    elif indicator_key == "business_investment":
        return f"C${val/1_000:,.1f}B"
    # Population - display in millions
    elif indicator_key == "population":
        return f"{val/1_000_000:,.2f}M"
    # Immigration/emigration - display as thousands
    elif indicator_key in ("immigration", "emigration"):
        return f"{val/1_000:,.1f}K"
    # EI beneficiaries - display as thousands
    elif indicator_key == "ei":
        return f"{val/1_000:,.0f}K"
    # Wages - display in dollars
    elif indicator_key == "wages":
        return f"${val:,.0f}"
    # Hours worked
    elif indicator_key == "hours_worked":
        return f"{val:.1f} hrs"
    # Housing starts - in thousands
    elif indicator_key == "housing_starts":
        return f"{val:,.0f}K"
    # CPI indices - display as index value
    elif indicator_key in ("inflation", "cpi_shelter", "cpi_food", "cpi_transport", "housing"):
        return f"{val:.1f}"
    # Rates (unemployment, employment, participation, job vacancy, policy rate, bonds)
    elif indicator_key in ("unemployment", "employment_rate", "participation_rate", "jobvacancy", "policy_rate", "bond_5y", "bond_10y"):
        return f"{val:.1f}%"
    else:
        return f"{val:,.0f}"


def generate_css() -> str:
    """Generate the main stylesheet."""
    return """\
:root {
    --primary: #d52b1e;
    --primary-light: #ff3333;
    --accent: #d52b1e;
    --positive: #27ae60;
    --negative: #c0392b;
    --bg: #f8f9fa;
    --card-bg: #ffffff;
    --text: #2c3e50;
    --text-light: #7f8c8d;
    --border: #dee2e6;
    --shadow: 0 2px 8px rgba(0,0,0,0.08);
    --canadian-red: #d52b1e;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
}

/* ── Header ── */
header {
    background: var(--primary);
    color: white;
    padding: 0;
    position: sticky;
    top: 0;
    z-index: 100;
    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
}

.header-inner {
    max-width: 1200px;
    margin: 0 auto;
    padding: 16px 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.logo {
    display: flex;
    align-items: center;
    gap: 16px;
    text-decoration: none;
}

.logo-img {
    height: 65px;
    width: auto;
}

.logo-text {
    color: white;
    font-size: 28px;
    font-weight: 700;
    letter-spacing: -0.5px;
}

nav {
    display: flex;
    align-items: center;
    gap: 24px;
}

nav a {
    color: rgba(255,255,255,0.85);
    text-decoration: none;
    font-size: 14px;
    font-weight: 500;
    transition: color 0.2s;
    padding: 8px 12px;
    border-radius: 4px;
}

nav a:hover {
    color: white;
    background: rgba(255,255,255,0.1);
}

nav a.active {
    color: white;
    background: rgba(255,255,255,0.15);
}

/* ── Main Container ── */
.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 24px;
}

/* ── Hero / Summary Banner ── */
.hero {
    background: linear-gradient(135deg, var(--primary) 0%, #2471a3 100%);
    color: white;
    padding: 40px 0;
    margin-bottom: 32px;
}

.hero-inner {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 24px;
}

.hero h1 {
    font-size: 28px;
    font-weight: 700;
    margin-bottom: 8px;
}

.hero p {
    font-size: 16px;
    opacity: 0.9;
    max-width: 700px;
}

.hero .update-date {
    font-size: 13px;
    opacity: 0.7;
    margin-top: 12px;
}

/* ── Summary Cards ── */
.summary-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 20px;
    margin-bottom: 32px;
}

.summary-card {
    background: var(--card-bg);
    border-radius: 8px;
    padding: 20px;
    box-shadow: var(--shadow);
    border-left: 4px solid var(--primary);
    text-decoration: none;
    color: var(--text);
    transition: transform 0.15s, box-shadow 0.15s;
}

.summary-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 16px rgba(0,0,0,0.12);
}

.summary-card.social { border-left-color: #7d3c98; }
.summary-card.demographic { border-left-color: #1e8449; }

.summary-card .label {
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    color: var(--text-light);
    margin-bottom: 8px;
    letter-spacing: 0.5px;
    text-align: center;
}

.summary-card .value {
    font-size: 26px;
    font-weight: 700;
    margin-bottom: 4px;
    color: #1a5276;
    text-align: center;
}

.summary-card .detail {
    font-size: 14px;
    font-weight: 600;
    color: var(--text);
    margin-bottom: 6px;
    text-align: center;
}

.summary-card .detail.positive { color: var(--positive); }
.summary-card .detail.negative { color: var(--negative); }
.summary-card .detail.neutral { color: var(--text-light); }

.summary-card .period {
    font-size: 11px;
    color: var(--text-light);
    margin-top: 4px;
    text-align: center;
}

/* ── Category Section ── */
.category-section {
    margin-bottom: 32px;
}

.category-header {
    font-size: 18px;
    font-weight: 700;
    padding-bottom: 8px;
    margin-bottom: 16px;
    border-bottom: 2px solid var(--primary);
    display: flex;
    align-items: center;
    gap: 8px;
}

.category-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    display: inline-block;
}

/* ── Indicator Table ── */
.indicator-table {
    width: 100%;
    border-collapse: collapse;
    background: var(--card-bg);
    border-radius: 8px;
    overflow: hidden;
    box-shadow: var(--shadow);
}

.indicator-table th {
    background: #f1f3f5;
    padding: 10px 16px;
    text-align: left;
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    color: var(--text-light);
    letter-spacing: 0.5px;
}

.indicator-table td {
    padding: 12px 16px;
    border-top: 1px solid var(--border);
    font-size: 14px;
}

.indicator-table tr {
    cursor: pointer;
    transition: background 0.15s;
}

.indicator-table tbody tr:hover {
    background: #f8f9fa;
}

.indicator-table .name-cell {
    font-weight: 600;
    color: #8b4513;
}

.indicator-table .name-cell a {
    color: inherit;
    text-decoration: none;
}

.indicator-table .name-cell a:hover {
    text-decoration: underline;
}

.indicator-table .value-cell {
    font-weight: 600;
    font-variant-numeric: tabular-nums;
}

.indicator-table .positive { color: var(--positive); }
.indicator-table .negative { color: var(--negative); }

.indicator-table .period-cell {
    color: var(--text-light);
    font-size: 13px;
}

.indicator-table .freq-cell {
    color: var(--text-light);
    font-size: 13px;
}

.sparkline-cell {
    width: 100px;
    padding: 8px 16px;
}

/* ── Indicator Detail Page ── */
.breadcrumb {
    font-size: 13px;
    color: var(--text-light);
    margin-bottom: 16px;
}

.breadcrumb a {
    color: var(--primary-light);
    text-decoration: none;
}

.breadcrumb a:hover { text-decoration: underline; }

.indicator-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 16px;
    margin-bottom: 24px;
}

.indicator-title h1 {
    font-size: 24px;
    font-weight: 700;
    margin-bottom: 4px;
}

.indicator-title .subtitle {
    font-size: 14px;
    color: var(--text-light);
}

.indicator-stats {
    display: flex;
    gap: 24px;
    flex-wrap: wrap;
}

.stat-box {
    text-align: center;
    padding: 12px 20px;
    background: var(--card-bg);
    border-radius: 8px;
    box-shadow: var(--shadow);
    min-width: 120px;
}

.stat-box .stat-label {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    color: var(--text-light);
    letter-spacing: 0.5px;
    margin-bottom: 4px;
}

.stat-box .stat-value {
    font-size: 24px;
    font-weight: 700;
}

.stat-box .stat-value.positive { color: var(--positive); }
.stat-box .stat-value.negative { color: var(--negative); }

/* ── Chart Container ── */
.chart-container {
    background: var(--card-bg);
    border-radius: 8px;
    padding: 24px;
    margin-bottom: 24px;
    box-shadow: var(--shadow);
}

.chart-container h2 {
    font-size: 16px;
    margin-bottom: 16px;
}

.chart-wrapper {
    position: relative;
    height: 350px;
}

/* ── Methodology Section ── */
.methodology {
    background: var(--card-bg);
    border-radius: 8px;
    padding: 24px;
    margin-bottom: 24px;
    box-shadow: var(--shadow);
}

.methodology h2 {
    font-size: 18px;
    margin-bottom: 12px;
    color: var(--primary);
}

.methodology p {
    font-size: 14px;
    line-height: 1.7;
    margin-bottom: 12px;
}

.methodology .meta-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 12px;
    margin-top: 16px;
    padding-top: 16px;
    border-top: 1px solid var(--border);
}

.methodology .meta-item {
    font-size: 13px;
}

.methodology .meta-item strong {
    display: block;
    font-size: 11px;
    text-transform: uppercase;
    color: var(--text-light);
    letter-spacing: 0.5px;
    margin-bottom: 2px;
}

/* ── Footer ── */
footer {
    background: var(--text);
    color: rgba(255,255,255,0.7);
    padding: 24px;
    text-align: center;
    font-size: 13px;
    margin-top: 48px;
}

footer a {
    color: rgba(255,255,255,0.9);
    text-decoration: none;
}

/* ── About Page ── */
.about-content {
    background: var(--card-bg);
    border-radius: 8px;
    padding: 32px;
    box-shadow: var(--shadow);
    max-width: 800px;
}

.about-content h2 {
    font-size: 20px;
    color: var(--primary);
    margin-bottom: 12px;
    margin-top: 24px;
}

.about-content h2:first-child { margin-top: 0; }

.about-content p {
    font-size: 14px;
    line-height: 1.7;
    margin-bottom: 12px;
}

.about-content ul {
    margin: 8px 0 16px 24px;
    font-size: 14px;
    line-height: 1.7;
}

/* ── Responsive ── */
@media (max-width: 768px) {
    .header-inner { flex-direction: column; gap: 8px; }
    nav a { margin-left: 12px; }
    .hero h1 { font-size: 22px; }
    .summary-grid { grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); }
    .indicator-header { flex-direction: column; }
    .indicator-stats { width: 100%; }
    .stat-box { flex: 1; }
    .indicator-table { font-size: 13px; }
    .indicator-table th, .indicator-table td { padding: 8px 10px; }
}

@media (max-width: 480px) {
    .summary-grid { grid-template-columns: 1fr; }
    .minister-metrics { grid-template-columns: 1fr; }
}

/* ── Ministers Page ── */
.minister-row {
    background: var(--card-bg);
    border-radius: 8px;
    padding: 24px;
    margin-bottom: 20px;
    box-shadow: var(--shadow);
}

.minister-header {
    display: flex;
    align-items: center;
    gap: 20px;
    margin-bottom: 16px;
}

.minister-photo {
    width: 80px;
    height: 80px;
    border-radius: 50%;
    object-fit: cover;
    border: 3px solid var(--primary);
    flex-shrink: 0;
}

.minister-info h2 {
    font-size: 20px;
    font-weight: 700;
    margin-bottom: 2px;
    color: var(--text);
}

.minister-info .minister-title {
    font-size: 14px;
    color: var(--text-light);
    font-weight: 500;
}

.minister-metrics {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
}

.metric-card {
    background: var(--card-bg);
    border-radius: 8px;
    padding: 20px;
    box-shadow: var(--shadow);
    text-decoration: none;
    color: var(--text);
    transition: transform 0.15s, box-shadow 0.15s;
    border-left: 4px solid var(--primary);
    display: block;
}

.metric-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 16px rgba(0,0,0,0.12);
}

.metric-card .metric-name {
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    color: var(--text-light);
    margin-bottom: 8px;
    letter-spacing: 0.5px;
    text-align: center;
}

.metric-card .metric-value {
    font-size: 26px;
    font-weight: 700;
    color: #1a5276;
    margin-bottom: 4px;
    text-align: center;
}

.metric-card .metric-detail {
    font-size: 14px;
    font-weight: 600;
    margin-bottom: 6px;
    text-align: center;
}

.metric-card .metric-detail.positive { color: var(--positive); }
.metric-card .metric-detail.negative { color: var(--negative); }
.metric-card .metric-detail.neutral { color: var(--text-light); }

.metric-card .metric-meta {
    font-size: 11px;
    color: var(--text-light);
    margin-top: 4px;
    text-align: center;
}

.rating-badge {
    display: inline-block;
    font-size: 10px;
    font-weight: 700;
    padding: 1px 6px;
    border-radius: 3px;
    text-transform: uppercase;
    letter-spacing: 0.3px;
}

.rating-badge.high { background: #d4edda; color: #155724; }
.rating-badge.moderate-high { background: #d1ecf1; color: #0c5460; }
.rating-badge.moderate { background: #fff3cd; color: #856404; }

@media (max-width: 768px) {
    .minister-metrics { grid-template-columns: 1fr; }
    .minister-header { flex-direction: column; text-align: center; }
    .minister-photo { width: 64px; height: 64px; }
}
"""


def generate_header(active: str = "home") -> str:
    """Generate the site header/nav."""
    is_sub = active in ("indicator", "minister_indicator")
    logo_path = "../img/Full Logo.png" if is_sub else "img/Full Logo.png"
    prefix = "../" if is_sub else ""
    return f"""\
<header>
    <div class="header-inner">
        <a href="{prefix}index.html" class="logo">
            <img src="{logo_path}" alt="Outcome Canada" class="logo-img">
            <span class="logo-text">Outcome Canada</span>
        </a>
        <nav>
            <a href="{prefix}index.html" {"class='active'" if active == "home" else ""}>Dashboard</a>
            <a href="{prefix}ministers.html" {"class='active'" if active == "ministers" else ""}>Ministers</a>
            <a href="{prefix}about.html" {"class='active'" if active == "about" else ""}>About</a>
            <a href="{prefix}contact.html" {"class='active'" if active == "contact" else ""}>Contact</a>
        </nav>
    </div>
</header>"""


def generate_footer() -> str:
    """Generate the site footer."""
    now = datetime.now().strftime("%Y-%m-%d")
    return f"""\
<footer>
    <p>Outcome Canada &mdash; Canadian Economic, Social & Demographic Data</p>
    <p style="margin-top:4px">
        Official data from Statistics Canada.
    </p>
    <p style="margin-top:4px; font-size:11px; opacity:0.7">
        Last updated: {now}. Data shown represents the latest available official statistics.
    </p>
</footer>"""


def value_class(val, unit: str = "% y/y") -> str:
    """Return CSS class for positive/negative values. Level rates get no color."""
    if val is None:
        return ""
    # Level rates (unemployment %, vacancy %, trade balance) — neutral color
    if unit in ("%", "C$ millions"):
        return ""
    return "positive" if val >= 0 else "negative"


def get_change_sentiment(indicator_key: str, change_value: float) -> str:
    """
    Determine if a change is positive, negative, or neutral for Canada.
    Returns: 'positive' (green), 'negative' (red), or 'neutral' (grey)
    """
    if change_value is None:
        return 'neutral'

    is_increase = change_value > 0

    # Indicators where increase is GOOD (green up, red down)
    positive_growth_indicators = [
        'gdp', 'gdp_percapita', 'employment_rate', 'participation_rate',
        'wages', 'housing_starts', 'trade', 'exports', 'retail',
        'manufacturing', 'business_investment'
    ]

    # Indicators where increase is BAD (red up, green down)
    negative_growth_indicators = [
        'unemployment', 'ei', 'inflation', 'cpi_shelter', 'cpi_food', 'cpi_transport'
    ]

    # Indicators that are NEUTRAL (grey regardless of direction)
    neutral_indicators = [
        'population', 'immigration', 'emigration', 'policy_rate', 'bond_5y', 'bond_10y',
        'hours_worked', 'jobvacancy', 'housing', 'imports'
    ]

    if indicator_key in positive_growth_indicators:
        return 'positive' if is_increase else 'negative'
    elif indicator_key in negative_growth_indicators:
        return 'negative' if is_increase else 'positive'
    elif indicator_key in neutral_indicators:
        return 'neutral'
    else:
        # Default: increase = positive
        return 'positive' if is_increase else 'negative'


def generate_home_page(all_data: dict) -> str:
    """Generate the main index.html."""
    now = datetime.now().strftime("%B %d, %Y")

    # Summary cards
    cards_html = ""
    for key in INDICATORS:
        ind = INDICATORS[key]
        data = all_data.get(key)
        if not data or data["value"] is None:
            continue

        cat_class = ind["category"].lower()
        val = data["value"]
        abs_val = data.get("absolute")

        # Format absolute value
        abs_str = format_absolute_value(abs_val, key)

        # Determine growth display based on indicator type
        if ind["unit"] == "%":
            # Rate indicators - show Y/Y percentage point change
            yoy_pp = data.get("yoy_pp_change")
            if yoy_pp is not None:
                arrow = "↑" if yoy_pp >= 0 else "↓"
                growth_str = f"{arrow} {abs(yoy_pp):.1f} pp"
                growth_color = get_change_sentiment(key, yoy_pp)
                detail_line = f"{growth_str} year over year"
            else:
                detail_line = ""
                growth_color = ""
        elif ind["unit"] == "C$ millions":
            # Trade balance - show Y/Y change
            yoy_chg = data.get("yoy_change_millions")
            if yoy_chg is not None:
                arrow = "↑" if yoy_chg >= 0 else "↓"
                yoy_b = abs(yoy_chg) / 1_000
                growth_str = f"{arrow} C${yoy_b:.1f}B"
                growth_color = get_change_sentiment(key, yoy_chg)
                detail_line = f"{growth_str} year over year"
            else:
                detail_line = ""
                growth_color = ""
        elif "C$" in ind["unit"] or "dollars" in ind["unit"].lower():
            # Level indicators like GDP per capita - show Y/Y growth percentage
            yoy_pct = data.get("yoy_growth")
            if yoy_pct is not None:
                arrow = "↑" if yoy_pct >= 0 else "↓"
                growth_str = f"{arrow} {abs(yoy_pct):.2f}%"
                growth_color = get_change_sentiment(key, yoy_pct)
                detail_line = f"{growth_str} year over year"
            else:
                detail_line = ""
                growth_color = ""
        else:
            # Growth indicators - show Y/Y growth with arrow
            if val is not None:
                growth_str = format_value(val, "% y/y", use_arrow=True)
                growth_color = get_change_sentiment(key, val)
                detail_line = f"{growth_str} year over year"
            else:
                detail_line = ""
                growth_color = ""

        cards_html += f"""\
        <a href="indicators/{key}.html" class="summary-card {cat_class}">
            <div class="label">{ind['name']}</div>
            <div class="value">{abs_str}</div>
            <div class="detail {growth_color}">{detail_line}</div>
            <div class="period">{data['period']} &middot; {ind['frequency']}</div>
        </a>\n"""

    # Category tables
    tables_html = ""
    for cat, cat_color in CATEGORIES.items():
        cat_indicators = {k: v for k, v in INDICATORS.items() if v["category"] == cat}
        if not cat_indicators:
            continue

        rows = ""
        for key, ind in cat_indicators.items():
            data = all_data.get(key)
            if not data:
                continue

            val = data["value"]
            abs_val = data.get("absolute")

            # Format absolute value (same as card big number)
            abs_str = format_absolute_value(abs_val, key)

            # Format Y/Y change (same as card detail line)
            if ind["unit"] == "%":
                yoy_pp = data.get("yoy_pp_change")
                if yoy_pp is not None:
                    arrow = "↑" if yoy_pp >= 0 else "↓"
                    yoy_str = f"{arrow} {abs(yoy_pp):.1f} pp"
                    yoy_color = get_change_sentiment(key, yoy_pp)
                else:
                    yoy_str = "N/A"
                    yoy_color = ""
            elif ind["unit"] == "C$ millions":
                yoy_chg = data.get("yoy_change_millions")
                if yoy_chg is not None:
                    arrow = "↑" if yoy_chg >= 0 else "↓"
                    yoy_b = abs(yoy_chg) / 1_000
                    yoy_str = f"{arrow} C${yoy_b:.1f}B"
                    yoy_color = get_change_sentiment(key, yoy_chg)
                else:
                    yoy_str = "N/A"
                    yoy_color = ""
            elif "C$" in ind["unit"] or "dollars" in ind["unit"].lower():
                yoy_pct = data.get("yoy_growth")
                if yoy_pct is not None:
                    arrow = "↑" if yoy_pct >= 0 else "↓"
                    yoy_str = f"{arrow} {abs(yoy_pct):.2f}%"
                    yoy_color = get_change_sentiment(key, yoy_pct)
                else:
                    yoy_str = "N/A"
                    yoy_color = ""
            else:
                if val is not None:
                    yoy_str = format_value(val, "% y/y", use_arrow=True)
                    yoy_color = get_change_sentiment(key, val)
                else:
                    yoy_str = "N/A"
                    yoy_color = ""

            rows += f"""\
            <tr onclick="window.location='indicators/{key}.html'">
                <td class="name-cell"><a href="indicators/{key}.html">{ind['name']}</a></td>
                <td class="value-cell">{abs_str}</td>
                <td class="{yoy_color}">{yoy_str}</td>
                <td class="period-cell">{data.get('period', '')}</td>
                <td class="freq-cell">{ind['frequency']}</td>
                <td class="period-cell">{ind['source']}</td>
            </tr>\n"""

        tables_html += f"""\
    <div class="category-section">
        <div class="category-header">
            <span class="category-dot" style="background:{cat_color}"></span>
            {cat} Indicators
        </div>
        <table class="indicator-table">
            <thead>
                <tr>
                    <th>Indicator</th>
                    <th>Value</th>
                    <th>Y/Y Change</th>
                    <th>Period</th>
                    <th>Freq</th>
                    <th>Source</th>
                </tr>
            </thead>
            <tbody>
{rows}
            </tbody>
        </table>
    </div>\n"""

    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Outcome Canada — Canadian Economic & Demographic Indicators</title>
    <meta name="description" content="Latest available data on Canadian economic, social, and demographic indicators from Statistics Canada.">
    <link rel="icon" type="image/png" sizes="32x32" href="img/Icon.png">
    <link rel="icon" type="image/png" sizes="16x16" href="img/Icon2.png">
    <link rel="apple-touch-icon" href="img/Icon.png">
    <link rel="stylesheet" href="css/style.css">
</head>
<body>
{generate_header("home")}

<div class="hero">
    <div class="hero-inner">
        <h1>Canada &mdash; Economic & Demographic Dashboard</h1>
        <p>Latest available data on key Canadian economic, social, and demographic indicators
           from Statistics Canada.</p>
        <div class="update-date">Last updated: {now}</div>
    </div>
</div>

<div class="container">
    <div class="summary-grid">
{cards_html}
    </div>

{tables_html}
</div>

{generate_footer()}
</body>
</html>"""


def generate_indicator_page(key: str, indicator: dict, data: dict, history: list) -> str:
    """Generate an individual indicator page."""
    val = data["value"] if data else None
    sec = data["secondary"] if data else None
    period = data["period"] if data else "N/A"

    # Determine display unit: growth indicators show Y/Y % even if native unit differs
    display_unit = indicator["unit"]
    if indicator["unit"] not in ("%", "C$ millions") and "C$" not in indicator["unit"]:
        display_unit = "% y/y"

    val_str = format_value(val, display_unit) if val is not None else "N/A"

    # Stats boxes
    stats_html = f"""\
    <div class="stat-box">
        <div class="stat-label">{display_unit}</div>
        <div class="stat-value {value_class(val, display_unit)}">{val_str}</div>
    </div>"""

    if sec is not None and indicator.get("secondary_label"):
        sec_unit = indicator.get("secondary_unit", "%")
        sec_str = format_value(sec, sec_unit)
        stats_html += f"""\
    <div class="stat-box">
        <div class="stat-label">{indicator['secondary_label']}</div>
        <div class="stat-value {value_class(sec, sec_unit)}">{sec_str}</div>
    </div>"""

    stats_html += f"""\
    <div class="stat-box">
        <div class="stat-label">Period</div>
        <div class="stat-value" style="font-size:18px; color:var(--text)">{period}</div>
    </div>"""

    # Chart data - adjust based on indicator type
    is_daily = indicator.get("frequency") == "Daily"
    is_index = key in ("inflation", "cpi_shelter", "cpi_food", "cpi_transport", "housing")
    is_scaled = key in ("retail", "manufacturing")

    if is_daily:
        chart_data = history[-400:] if len(history) > 400 else history
        chart_labels = json.dumps([d["date"] for d in chart_data])
    elif is_index:
        # Show full history for index indicators (back to index ~100)
        chart_data = history
        chart_labels = json.dumps([d["date"][:7] for d in chart_data])
    else:
        chart_data = history[-60:] if len(history) > 60 else history
        chart_labels = json.dumps([d["date"][:7] for d in chart_data])

    # Scale values for readability
    if is_scaled:
        chart_values = json.dumps([round(d["value"] / 1_000_000, 2) for d in chart_data])
    else:
        chart_values = json.dumps([d["value"] for d in chart_data])

    # Chart heading and y-axis config
    if is_index:
        chart_heading = "Historical Index"
        y_axis_config = "min: 100, grid: { color: 'rgba(0,0,0,0.06)' }"
        max_ticks = 15
        auto_skip_padding = 40
    elif is_scaled:
        chart_heading = f"Historical Series (C$ Billions)"
        y_axis_config = "title: { display: true, text: 'C$ Billions' }, grid: { color: 'rgba(0,0,0,0.06)' }"
        max_ticks = 10
        auto_skip_padding = 40
    elif is_daily:
        chart_heading = "Historical Series"
        y_axis_config = "grid: { color: 'rgba(0,0,0,0.06)' }"
        max_ticks = 12
        auto_skip_padding = 50
    else:
        chart_heading = "Historical Series"
        y_axis_config = "grid: { color: 'rgba(0,0,0,0.06)' }"
        max_ticks = 10
        auto_skip_padding = 40

    chart_section = ""
    if chart_data:
        chart_section = f"""\
    <div class="chart-container">
        <h2>{chart_heading}</h2>
        <div class="chart-wrapper">
            <canvas id="indicatorChart"></canvas>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <script>
    const ctx = document.getElementById('indicatorChart').getContext('2d');
    new Chart(ctx, {{
        type: 'line',
        data: {{
            labels: {chart_labels},
            datasets: [{{
                label: '{indicator["name"]}',
                data: {chart_values},
                borderColor: '#1a5276',
                backgroundColor: 'rgba(26, 82, 118, 0.1)',
                fill: true,
                tension: 0.3,
                pointRadius: 0,
                borderWidth: 2,
            }}]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{
                legend: {{ display: false }},
                tooltip: {{
                    mode: 'index',
                    intersect: false,
                }}
            }},
            scales: {{
                x: {{
                    ticks: {{
                        maxTicksLimit: {max_ticks},
                        maxRotation: 0,
                        autoSkip: true,
                        autoSkipPadding: {auto_skip_padding},
                    }},
                    grid: {{ display: false }}
                }},
                y: {{
                    {y_axis_config}
                }}
            }},
            interaction: {{
                mode: 'nearest',
                axis: 'x',
                intersect: false
            }}
        }}
    }});
    </script>"""

    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{indicator['name']} — Canada | Outcome Canada</title>
    <meta name="description" content="{indicator['description'][:160]}">
    <link rel="icon" type="image/png" sizes="32x32" href="../img/Icon.png">
    <link rel="icon" type="image/png" sizes="16x16" href="../img/Icon2.png">
    <link rel="apple-touch-icon" href="../img/Icon.png">
    <link rel="stylesheet" href="../css/style.css">
</head>
<body>
{generate_header("indicator")}

<div class="container">
    <div class="breadcrumb">
        <a href="../index.html">Dashboard</a> &rsaquo; {indicator['name']}
    </div>

    <div class="indicator-header">
        <div class="indicator-title">
            <h1>{indicator['name']}</h1>
            <div class="subtitle">{indicator['description']}</div>
        </div>
        <div class="indicator-stats">
{stats_html}
        </div>
    </div>

{chart_section}

    <div class="methodology">
        <h2>Data Source</h2>
        <p>{indicator['methodology']}</p>
        <div class="meta-grid">
            <div class="meta-item">
                <strong>Source</strong>
                {_statcan_table_link(indicator['source'], indicator['table'])}
            </div>
            <div class="meta-item">
                <strong>Frequency</strong>
                {indicator['frequency']}
            </div>
            <div class="meta-item">
                <strong>Category</strong>
                {indicator['category']}
            </div>
            <div class="meta-item">
                <strong>Unit</strong>
                {indicator['unit']}
            </div>
        </div>
    </div>
</div>

{generate_footer()}
</body>
</html>"""


def generate_about_page() -> str:
    """Generate the about page."""
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>About — Outcome Canada</title>
    <link rel="icon" type="image/png" sizes="32x32" href="img/Icon.png">
    <link rel="icon" type="image/png" sizes="16x16" href="img/Icon2.png">
    <link rel="apple-touch-icon" href="img/Icon.png">
    <link rel="stylesheet" href="css/style.css">
</head>
<body>
{generate_header("about")}

<div class="container">
    <div class="about-content">
        <h2>About Outcome Canada</h2>
        <p>
            Outcome Canada provides a comprehensive view of Canadian economic, social, and demographic
            indicators. The mission is to make official government statistics more accessible for
            Canadians who want to monitor the country's economic and social outcomes.
        </p>

        <h2>What We Track</h2>
        <p>We currently track 27 Canadian indicators across seven categories:</p>
        <ul>
            <li><strong>Economic Growth (2):</strong> Real GDP, GDP per Capita</li>
            <li><strong>Labour Market (7):</strong> Unemployment Rate, Employment Rate,
                Participation Rate, Average Weekly Earnings, Average Weekly Hours,
                EI Beneficiaries, Job Vacancy Rate</li>
            <li><strong>Prices & Inflation (4):</strong> CPI All-items, CPI Shelter,
                CPI Food, CPI Transportation</li>
            <li><strong>Housing (2):</strong> New Housing Price Index, Housing Starts</li>
            <li><strong>Trade & Business (6):</strong> Trade Balance, Merchandise Exports,
                Merchandise Imports, Retail Sales, Manufacturing Sales, Business Investment</li>
            <li><strong>Financial (3):</strong> Bank of Canada Policy Rate, 5-Year Bond Yield,
                10-Year Bond Yield</li>
            <li><strong>Demographics (3):</strong> Total Population, Immigrants, Emigrants</li>
        </ul>
        <p>
            All indicators are sourced directly from official Statistics Canada data,
            accessed through their Web Data Service API.
        </p>

        <h2>Data Sources</h2>
        <p>
            <strong>Statistics Canada</strong> — All data is sourced exclusively from Statistics
            Canada, Canada's national statistical office. Data is accessed through their Web Data
            Service API and covers economic indicators (GDP, employment, inflation, trade,
            manufacturing, retail sales, housing, business investment), labour market statistics
            (Labour Force Survey), price indices (Consumer Price Index), financial data (interest
            rates, bond yields), and demographic data (population, immigration, emigration).
        </p>

        <h2>Data Updates</h2>
        <p>
            Statistics Canada releases data on different schedules depending on the indicator.
            Most monthly indicators are released 30-60 days after the reference period, while
            quarterly indicators may take 60-120 days. This dashboard is updated as new official
            data becomes available.
        </p>

        <h2>Understanding the Data</h2>
        <p>
            Each indicator page provides context on what the indicator measures, why it matters,
            and when the data is typically released. Historical charts show trends over time,
            helping you understand current values in context.
        </p>
        <p>
            All data shown represents official statistics from government sources. We do not
            make projections, forecasts, or predictions — we simply present the latest available
            official data in an accessible format.
        </p>

        <h2>Author</h2>
        <div style="display: flex; align-items: center; gap: 20px; margin-top: 16px;">
            <img src="img/Author Photo.png" alt="Tom Hwang" style="width: 100px; height: 100px; border-radius: 50%; object-fit: cover;">
            <div>
                <p>
                    Outcome Canada is a personal project by <a href="https://www.linkedin.com/in/tom-hwang/" target="_blank" rel="noopener noreferrer" style="color: var(--primary); text-decoration: none; font-weight: 600;">Tom Hwang</a>.
                </p>
                <p style="margin-top: 8px; font-size: 14px; color: var(--text-light);">
                    This project has no affiliation with the author's institution and is purely a personal initiative.
                </p>
            </div>
        </div>
    </div>
</div>

{generate_footer()}
</body>
</html>"""


def generate_contact_page() -> str:
    """Generate the contact page with feedback form."""
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Contact — Outcome Canada</title>
    <link rel="icon" type="image/png" sizes="32x32" href="img/Icon.png">
    <link rel="icon" type="image/png" sizes="16x16" href="img/Icon2.png">
    <link rel="apple-touch-icon" href="img/Icon.png">
    <link rel="stylesheet" href="css/style.css">
</head>
<body>
{generate_header("contact")}

<div class="container">
    <div class="about-content">
        <h2>Contact Outcome Canada</h2>
        <p style="font-size: 16px; margin-bottom: 32px;">
            Do you have any comments or feedback to Outcome Canada?
        </p>

        <form id="contactForm" action="https://formspree.io/f/xnnqjgrd" method="POST" style="max-width: 600px;">
            <div style="margin-bottom: 20px;">
                <label for="name" style="display: block; font-weight: 600; margin-bottom: 8px; color: var(--text);">Name</label>
                <input type="text" id="name" name="name" required
                       style="width: 100%; padding: 12px; border: 1px solid var(--border); border-radius: 4px; font-size: 14px; font-family: inherit;">
            </div>

            <div style="margin-bottom: 20px;">
                <label for="email" style="display: block; font-weight: 600; margin-bottom: 8px; color: var(--text);">Email</label>
                <input type="email" id="email" name="_replyto" required
                       style="width: 100%; padding: 12px; border: 1px solid var(--border); border-radius: 4px; font-size: 14px; font-family: inherit;">
            </div>

            <div style="margin-bottom: 20px;">
                <label for="message" style="display: block; font-weight: 600; margin-bottom: 8px; color: var(--text);">Message</label>
                <textarea id="message" name="message" rows="6" required
                          style="width: 100%; padding: 12px; border: 1px solid var(--border); border-radius: 4px; font-size: 14px; font-family: inherit; resize: vertical;"></textarea>
            </div>

            <button type="submit"
                    style="background: var(--primary); color: white; padding: 12px 32px; border: none; border-radius: 4px; font-size: 16px; font-weight: 600; cursor: pointer; transition: background 0.2s;">
                Send Message
            </button>

            <div id="formStatus" style="margin-top: 16px; padding: 12px; border-radius: 4px; display: none;"></div>
        </form>

        <script>
            const form = document.getElementById('contactForm');
            const status = document.getElementById('formStatus');

            form.addEventListener('submit', async (e) => {{
                e.preventDefault();

                const formData = new FormData(form);

                try {{
                    const response = await fetch(form.action, {{
                        method: 'POST',
                        body: formData,
                        headers: {{
                            'Accept': 'application/json'
                        }}
                    }});

                    if (response.ok) {{
                        status.style.display = 'block';
                        status.style.background = '#d4edda';
                        status.style.color = '#155724';
                        status.style.border = '1px solid #c3e6cb';
                        status.textContent = 'Thank you for your feedback! We will get back to you soon.';
                        form.reset();
                    }} else {{
                        throw new Error('Form submission failed');
                    }}
                }} catch (error) {{
                    status.style.display = 'block';
                    status.style.background = '#f8d7da';
                    status.style.color = '#721c24';
                    status.style.border = '1px solid #f5c6cb';
                    status.textContent = 'Oops! There was a problem submitting your form. Please try again.';
                }}
            }});
        </script>
    </div>
</div>

{generate_footer()}
</body>
</html>"""


METRIC_TO_INDICATOR = {
    "pm_gdp_growth": "gdp",
    "pm_gdp_percapita": "gdp_percapita",
    "pm_unemployment": "unemployment",
    "pm_wages": "wages",
    "pm_cpi": "inflation",
    "pm_retail": "retail",
    "pm_employment": "employment_rate",
    "pm_trade": "trade",
    "joly_manufacturing": "manufacturing",
    "chartrand_food": "cpi_food",
    "robertson_starts": "housing_starts",
    "robertson_affordability": "housing",
    "sidhu_exports": "exports",
    "macdonald_exports": "exports",
    "diab_admissions": "immigration",
}


def _statcan_table_link(source: str, table: str) -> str:
    """Return HTML for the source citation, with a clickable link for StatCan tables or embedded URLs."""
    import re
    # Handle sources with embedded URLs (e.g. "Government of Canada https://...")
    urls = list(re.finditer(r'(https?://\S+)', source))
    if urls:
        # Build HTML with all URLs as clickable links
        parts = []
        last_end = 0
        for i, m in enumerate(urls):
            text_before = source[last_end:m.start()].strip()
            url = m.group(1)
            # Strip trailing punctuation that's not part of the URL
            while url and url[-1] in '),;':
                url = url[:-1]
            link_label = text_before if text_before else f"Source {i + 1}"
            if text_before:
                parts.append(f'{text_before} <a href="{url}" target="_blank" rel="noopener">[link]</a>')
            else:
                parts.append(f'<a href="{url}" target="_blank" rel="noopener">[link]</a>')
            last_end = m.end()
        # Append any trailing text after the last URL
        trailing = source[last_end:].strip()
        if trailing:
            parts.append(trailing)
        return " ".join(parts)
    if source == "Statistics Canada" and table and table != "N/A":
        pid = table.replace("-", "")
        url = f"https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid={pid}"
        return f'{source} — <a href="{url}" target="_blank" rel="noopener">Table {table}</a>'
    if table and table != "N/A":
        return f"{source} — Table {table}"
    return source


def _minister_card_display(metric: dict, all_data: dict) -> tuple:
    """Return (value_str, detail_line, growth_color, period_str) for a minister metric card."""
    # Priority 1: Fresh data from daily StatCan fetch (minister_latest.json)
    fresh = MINISTER_FRESH_DATA.get(metric["key"])
    if fresh:
        return (fresh["value"], fresh.get("detail", ""), fresh.get("detail_color", "neutral"), fresh.get("period", ""))

    # Priority 2: Hardcoded latest data in ministers_config.py (fallback for non-StatCan sources)
    latest = metric.get("latest")
    if latest:
        return (latest["value"], latest.get("detail", ""), latest.get("detail_color", "neutral"), latest.get("period", ""))

    ind_key = METRIC_TO_INDICATOR.get(metric["key"])
    if not ind_key:
        return ("—", "", "neutral", "")

    data = all_data.get(ind_key)
    ind = INDICATORS.get(ind_key)
    if not data or not ind or data.get("value") is None:
        return ("—", "", "neutral", "")

    val = data["value"]
    abs_str = format_absolute_value(data.get("absolute"), ind_key)
    period = data.get("period", "")

    # Growth / detail line — same logic as home page
    if ind["unit"] == "%":
        yoy_pp = data.get("yoy_pp_change")
        if yoy_pp is not None:
            arrow = "↑" if yoy_pp >= 0 else "↓"
            detail_line = f"{arrow} {abs(yoy_pp):.1f} pp year over year"
            growth_color = get_change_sentiment(ind_key, yoy_pp)
        else:
            detail_line, growth_color = "", ""
    elif ind["unit"] == "C$ millions":
        yoy_chg = data.get("yoy_change_millions")
        if yoy_chg is not None:
            arrow = "↑" if yoy_chg >= 0 else "↓"
            yoy_b = abs(yoy_chg) / 1_000
            detail_line = f"{arrow} C${yoy_b:.1f}B year over year"
            growth_color = get_change_sentiment(ind_key, yoy_chg)
        else:
            detail_line, growth_color = "", ""
    elif "C$" in ind["unit"] or "dollars" in ind["unit"].lower():
        yoy_pct = data.get("yoy_growth")
        if yoy_pct is not None:
            arrow = "↑" if yoy_pct >= 0 else "↓"
            detail_line = f"{arrow} {abs(yoy_pct):.2f}% year over year"
            growth_color = get_change_sentiment(ind_key, yoy_pct)
        else:
            detail_line, growth_color = "", ""
    else:
        if val is not None:
            growth_str = format_value(val, "% y/y", use_arrow=True)
            detail_line = f"{growth_str} year over year"
            growth_color = get_change_sentiment(ind_key, val)
        else:
            detail_line, growth_color = "", ""

    return (abs_str, detail_line, growth_color, period)


def generate_ministers_page(all_data: dict) -> str:
    """Generate the ministers.html page with all 26 ministers and their metric cards."""
    now = datetime.now().strftime("%B %d, %Y")

    ministers_html = ""
    for minister_key, minister in MINISTERS.items():
        # Build metric cards for this minister
        cards_html = ""
        for metric in minister["metrics"]:
            abs_str, detail_line, growth_color, period = _minister_card_display(metric, all_data)
            period_line = f"{period} &middot; " if period else ""
            cards_html += f"""\
                <a href="ministers/{metric['key']}.html" class="metric-card">
                    <div class="metric-name">{metric['name']}</div>
                    <div class="metric-value">{abs_str}</div>
                    <div class="metric-detail {growth_color}">{detail_line}</div>
                    <div class="metric-meta">{period_line}{metric['frequency']}</div>
                </a>\n"""

        ministers_html += f"""\
    <div class="minister-row">
        <div class="minister-header">
            <img src="{minister['photo']}" alt="{minister['name']}" class="minister-photo">
            <div class="minister-info">
                <h2>{minister['name']}</h2>
                <p>{minister['title']}</p>
            </div>
        </div>
        <div class="minister-metrics">
{cards_html}
        </div>
    </div>\n"""

    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cabinet Ministers — Outcome Canada</title>
    <meta name="description" content="Track the performance of Canada's 26 cabinet ministers across 78 key metrics.">
    <link rel="icon" type="image/png" sizes="32x32" href="img/Icon.png">
    <link rel="icon" type="image/png" sizes="16x16" href="img/Icon2.png">
    <link rel="apple-touch-icon" href="img/Icon.png">
    <link rel="stylesheet" href="css/style.css">
</head>
<body>
{generate_header("ministers")}

<div class="hero">
    <div class="hero-inner">
        <h1>Cabinet Ministers &mdash; Performance Scorecard</h1>
        <p>Tracking 78 outcome metrics across Canada's 26 cabinet ministers.
           Each metric is linked to official data sources.</p>
        <div class="update-date">Last updated: {now}</div>
    </div>
</div>

<div class="container">
{ministers_html}
</div>

{generate_footer()}
</body>
</html>"""


def generate_minister_indicator_page(minister_key: str, minister: dict, metric: dict) -> str:
    """Generate an individual minister metric detail page."""
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{metric['name']} — {minister['name']} | Outcome Canada</title>
    <meta name="description" content="{metric['description'][:160]}">
    <link rel="icon" type="image/png" sizes="32x32" href="../img/Icon.png">
    <link rel="icon" type="image/png" sizes="16x16" href="../img/Icon2.png">
    <link rel="apple-touch-icon" href="../img/Icon.png">
    <link rel="stylesheet" href="../css/style.css">
</head>
<body>
{generate_header("minister_indicator")}

<div class="container">
    <div class="breadcrumb">
        <a href="../ministers.html">Ministers</a> &rsaquo; {minister['name']} &rsaquo; {metric['name']}
    </div>

    <div class="indicator-header">
        <div class="indicator-title" style="display:flex; align-items:center; gap:20px;">
            <img src="{minister['photo']}" alt="{minister['name']}" class="minister-photo" style="width:60px; height:60px;">
            <div>
                <h1>{metric['name']}</h1>
                <div class="subtitle">{minister['name']} &mdash; {minister['title']}</div>
            </div>
        </div>
        <div class="indicator-stats">
            <div class="stat-box">
                <div class="stat-label">Rating</div>
                <div class="stat-value"><span class="rating-badge {metric['rating'].lower().replace('-', '')}">{metric['rating']}</span></div>
            </div>
            <div class="stat-box">
                <div class="stat-label">Frequency</div>
                <div class="stat-value" style="font-size:18px; color:var(--text)">{metric['frequency']}</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">Unit</div>
                <div class="stat-value" style="font-size:18px; color:var(--text)">{metric['unit']}</div>
            </div>
        </div>
    </div>

    <div class="methodology">
        <h2>About This Metric</h2>
        <p>{metric['description']}</p>
        <div class="meta-grid">
            <div class="meta-item">
                <strong>Source</strong>
                {_statcan_table_link(metric['source'], metric['table'])}
            </div>
            <div class="meta-item">
                <strong>Frequency</strong>
                {metric['frequency']}
            </div>
            <div class="meta-item">
                <strong>Unit</strong>
                {metric['unit']}
            </div>
            <div class="meta-item">
                <strong>Trackability</strong>
                <span class="rating-badge {metric['rating'].lower().replace('-', '')}">{metric['rating']}</span>
            </div>
        </div>
    </div>
</div>

{generate_footer()}
</body>
</html>"""


def build():
    """Build the complete static site."""
    print("=" * 56)
    print("  BUILDING OUTCOMECANADA.CA")
    print("=" * 56)

    # Clean and create output directory
    if SITE_DIR.exists():
        shutil.rmtree(SITE_DIR)
    SITE_DIR.mkdir(parents=True)
    (SITE_DIR / "css").mkdir()
    (SITE_DIR / "indicators").mkdir()
    (SITE_DIR / "ministers").mkdir()

    # Write CSS
    print("\n[1/5] Writing CSS...")
    with open(SITE_DIR / "css" / "style.css", "w", encoding="utf-8") as f:
        f.write(generate_css())

    # Read all official Statistics Canada data
    print("\n[2/5] Reading official data...")
    all_data = {}
    all_history = {}
    for key, ind in INDICATORS.items():
        data = read_official_data(key, ind)
        history = read_chart_history(key, ind)
        all_data[key] = data
        all_history[key] = history
        if data and data["value"] is not None:
            print(f"  {ind['name']}: {format_value(data['value'], ind['unit'])} ({data['period']})")
        else:
            print(f"  {ind['name']}: NO DATA")

    # Generate pages
    print("\n[3/5] Generating HTML pages...")

    # Home page
    with open(SITE_DIR / "index.html", "w", encoding="utf-8") as f:
        f.write(generate_home_page(all_data))
    print("  index.html")

    # About page
    with open(SITE_DIR / "about.html", "w", encoding="utf-8") as f:
        f.write(generate_about_page())
    print("  about.html")

    # Contact page
    with open(SITE_DIR / "contact.html", "w", encoding="utf-8") as f:
        f.write(generate_contact_page())
    print("  contact.html")

    # Indicator pages
    for key, ind in INDICATORS.items():
        data = all_data.get(key, {})
        history = all_history.get(key, [])
        html = generate_indicator_page(key, ind, data, history)
        with open(SITE_DIR / "indicators" / f"{key}.html", "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  indicators/{key}.html")

    # Ministers page and individual minister metric pages
    print("\n[4/5] Generating ministers pages...")
    with open(SITE_DIR / "ministers.html", "w", encoding="utf-8") as f:
        f.write(generate_ministers_page(all_data))
    print("  ministers.html")

    for minister_key, minister in MINISTERS.items():
        for metric in minister["metrics"]:
            html = generate_minister_indicator_page(minister_key, minister, metric)
            with open(SITE_DIR / "ministers" / f"{metric['key']}.html", "w", encoding="utf-8") as f:
                f.write(html)
            print(f"  ministers/{metric['key']}.html")

    # Dashboard charts (optional - not required for static data display)
    print("\n[5/5] Finalizing site...")
    # Note: Dashboard charts from nowcast projects are no longer used
    # Charts are generated inline using Chart.js on each indicator page
    img_dir = SITE_DIR / "img"
    img_dir.mkdir(exist_ok=True)

    # Copy logo and icon files
    source_dir = Path(__file__).parent
    logo_file = source_dir / "Full Logo.png"
    icon_file = source_dir / "Icon.png"
    icon2_file = source_dir / "Icon2.png"
    author_photo = source_dir / "Author Photo.png"

    if logo_file.exists():
        shutil.copy2(logo_file, img_dir / "Full Logo.png")
        print("  Copied Full Logo.png")

    if icon_file.exists():
        shutil.copy2(icon_file, img_dir / "Icon.png")
        print("  Copied Icon.png")

    if icon2_file.exists():
        shutil.copy2(icon2_file, img_dir / "Icon2.png")
        print("  Copied Icon2.png")

    if author_photo.exists():
        shutil.copy2(author_photo, img_dir / "Author Photo.png")
        print("  Copied Author Photo.png")

    # Legacy chart copying code (disabled - no longer applicable)
    # for key, ind in INDICATORS.items():
    #     project_dir = CODES_DIR / ind.get("project", "")
    #     output_dir = project_dir / "output"
    #     if output_dir.exists():
    #         for png in output_dir.glob("*.png"):
    #             dest = img_dir / f"{key}_dashboard.png"
    #             shutil.copy2(png, dest)
    #             print(f"  {key}_dashboard.png")
    #             break

    print(f"\n{'=' * 56}")
    print(f"  BUILD COMPLETE")
    print(f"  Output: {SITE_DIR}")
    print(f"  Files: {sum(1 for _ in SITE_DIR.rglob('*') if _.is_file())}")
    print(f"{'=' * 56}")


if __name__ == "__main__":
    build()
