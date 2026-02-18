"""
Fetch Statistics Canada data for minister metrics.
Produces pre-formatted 'latest' blocks as JSON for build_site.py.
All vector IDs verified via WDS API on 2026-02-11.
"""
import json
import requests
import time
from pathlib import Path
from datetime import datetime, timezone
from minister_vectors import MINISTER_VECTOR_MAP

OUTPUT_DIR = Path(__file__).parent / "minister-data"

API_URL = "https://www150.statcan.gc.ca/t1/wds/rest/getDataFromVectorsAndLatestNPeriods"
HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}


def fetch_vector(vector_id: str, periods: int) -> list | None:
    """Fetch data for a single vector. Returns sorted list of {date, value} or None."""
    vid = int(vector_id.replace("v", ""))
    payload = [{"vectorId": vid, "latestN": periods}]

    for attempt in range(3):
        try:
            resp = requests.post(API_URL, headers=HEADERS, json=payload, timeout=30)
            if resp.status_code != 200:
                print(f"      HTTP {resp.status_code}, attempt {attempt + 1}")
                time.sleep(5)
                continue

            result = resp.json()
            if not result or result[0].get("status") == "FAILED":
                return None

            points = result[0].get("object", {}).get("vectorDataPoint", [])
            data = []
            for p in points:
                ref = p.get("refPer")
                val = p.get("value")
                if ref and val is not None:
                    data.append({"date": ref, "value": float(val)})

            data.sort(key=lambda x: x["date"])
            return data if data else None

        except Exception as e:
            print(f"      Error: {e}, attempt {attempt + 1}")
            time.sleep(5)

    return None


def format_period(date_str: str, is_quarterly: bool = False) -> str:
    """Convert '2026-01-01' to '2026-01' (monthly) or '2025-Q3' (quarterly)."""
    if is_quarterly:
        year = date_str[:4]
        month = int(date_str[5:7])
        quarter = (month - 1) // 3 + 1
        return f"{year}-Q{quarter}"
    return date_str[:7]


def is_quarterly(data: list) -> bool:
    """Guess if data is quarterly by checking gap between last two points."""
    if len(data) < 2:
        return False
    d1 = datetime.strptime(data[-1]["date"][:10], "%Y-%m-%d")
    d2 = datetime.strptime(data[-2]["date"][:10], "%Y-%m-%d")
    return (d1 - d2).days > 60


def is_annual(data: list) -> bool:
    """Guess if data is annual by checking gap between last two points."""
    if len(data) < 2:
        return False
    d1 = datetime.strptime(data[-1]["date"][:10], "%Y-%m-%d")
    d2 = datetime.strptime(data[-2]["date"][:10], "%Y-%m-%d")
    return (d1 - d2).days > 300


def get_yoy_index(data: list) -> int | None:
    """Find the index of the data point ~12 months before the latest."""
    if is_annual(data):
        return -2 if len(data) >= 2 else None
    elif is_quarterly(data):
        return -5 if len(data) >= 5 else None
    else:  # monthly
        return -13 if len(data) >= 13 else None


def format_detail(change: float, unit: str, direction: str) -> tuple:
    """Format the detail line and color based on change direction."""
    if unit == "pp":
        arrow = "\u2191" if change >= 0 else "\u2193"
        detail = f"{arrow} {abs(change):.1f} pp year over year"
    else:
        arrow = "\u2191" if change >= 0 else "\u2193"
        detail = f"{arrow} {abs(change):.1f}% year over year"

    # Determine color: does the direction of change match the desired direction?
    if direction == "positive":
        color = "positive" if change >= 0 else "negative"
    elif direction == "negative":
        color = "positive" if change <= 0 else "negative"
    else:
        color = "neutral"

    return detail, color


def compute_rate_yoy_pp(config: dict, all_data: dict) -> dict | None:
    """Value is latest rate, detail is YoY change in percentage points."""
    vec = config["vectors"][0]
    data = all_data.get(vec["id"])
    if not data or len(data) < 2:
        return None

    latest_val = data[-1]["value"]
    yoy_idx = get_yoy_index(data)
    if yoy_idx is None:
        return None

    yoy_val = data[yoy_idx]["value"]
    pp_change = latest_val - yoy_val

    detail, color = format_detail(pp_change, "pp", config["direction"])
    period = data[-1]["date"][:4] if is_annual(data) else format_period(data[-1]["date"], is_quarterly(data))

    return {
        "value": config["format_value"].format(latest_val),
        "detail": detail,
        "detail_color": color,
        "period": period,
    }


def compute_level_yoy_pct(config: dict, all_data: dict) -> dict | None:
    """Value is latest level (formatted), detail is YoY % change."""
    vec = config["vectors"][0]
    data = all_data.get(vec["id"])
    if not data or len(data) < 2:
        return None

    latest_val = data[-1]["value"]
    scalar = config.get("scalar", 1)
    display_val = latest_val / scalar

    yoy_idx = get_yoy_index(data)
    if yoy_idx is None:
        return None

    yoy_val = data[yoy_idx]["value"]
    pct_change = ((latest_val / yoy_val) - 1) * 100 if yoy_val != 0 else 0

    detail, color = format_detail(pct_change, "%", config["direction"])
    period = data[-1]["date"][:4] if is_annual(data) else format_period(data[-1]["date"], is_quarterly(data))

    return {
        "value": config["format_value"].format(display_val),
        "detail": detail,
        "detail_color": color,
        "period": period,
    }


def compute_level_qoq_pct(config: dict, all_data: dict) -> dict | None:
    """Value is latest level (formatted), detail is quarter-over-quarter % change."""
    vec = config["vectors"][0]
    data = all_data.get(vec["id"])
    if not data or len(data) < 2:
        return None

    latest_val = data[-1]["value"]
    scalar = config.get("scalar", 1)
    display_val = latest_val / scalar

    prev_val = data[-2]["value"]
    pct_change = ((latest_val / prev_val) - 1) * 100 if prev_val != 0 else 0

    # Color based on direction
    if config["direction"] == "positive":
        color = "positive" if pct_change >= 0 else "negative"
    elif config["direction"] == "negative":
        color = "positive" if pct_change <= 0 else "negative"
    else:
        color = "neutral"

    arrow = "\u2191" if pct_change >= 0 else "\u2193"
    detail = f"{arrow} {abs(pct_change):.1f}% quarter over quarter"

    period = format_period(data[-1]["date"], is_quarterly=True)

    return {
        "value": config["format_value"].format(display_val),
        "detail": detail,
        "detail_color": color,
        "period": period,
    }


def compute_count_yoy_pct(config: dict, all_data: dict) -> dict | None:
    """Same as level_yoy_pct but for integer counts."""
    return compute_level_yoy_pct(config, all_data)


def compute_share_pct(config: dict, all_data: dict) -> dict | None:
    """Compute ratio: 1 - (vector_b / vector_a) as percentage (export diversification)."""
    total_vec = None
    us_vec = None
    for v in config["vectors"]:
        if v["label"] == "total_exports":
            total_vec = v["id"]
        elif v["label"] == "us_exports":
            us_vec = v["id"]

    total_data = all_data.get(total_vec)
    us_data = all_data.get(us_vec)
    if not total_data or not us_data:
        return None

    # Align by date
    latest_total = total_data[-1]["value"]
    latest_us = us_data[-1]["value"]
    if latest_total == 0:
        return None

    share = (1 - latest_us / latest_total) * 100

    # YoY
    yoy_idx = get_yoy_index(total_data)
    if yoy_idx is not None and len(us_data) >= abs(yoy_idx):
        prev_total = total_data[yoy_idx]["value"]
        prev_us = us_data[yoy_idx]["value"]
        prev_share = (1 - prev_us / prev_total) * 100 if prev_total != 0 else 0
        pp_change = share - prev_share
        detail, color = format_detail(pp_change, "pp", config["direction"])
    else:
        detail, color = "", "neutral"

    period = format_period(total_data[-1]["date"], is_quarterly(total_data))

    return {
        "value": config["format_value"].format(share),
        "detail": detail,
        "detail_color": color,
        "period": period,
    }


def compute_wage_gap(config: dict, all_data: dict) -> dict | None:
    """Compute gender wage gap: (male - female) / male."""
    male_vec = None
    female_vec = None
    for v in config["vectors"]:
        if v["label"] == "male_wage":
            male_vec = v["id"]
        elif v["label"] == "female_wage":
            female_vec = v["id"]

    male_data = all_data.get(male_vec)
    female_data = all_data.get(female_vec)
    if not male_data or not female_data:
        return None

    male_val = male_data[-1]["value"]
    female_val = female_data[-1]["value"]
    if male_val == 0:
        return None

    gap = ((male_val - female_val) / male_val) * 100

    # YoY
    yoy_idx = get_yoy_index(male_data)
    if yoy_idx is not None and len(female_data) >= abs(yoy_idx):
        prev_male = male_data[yoy_idx]["value"]
        prev_female = female_data[yoy_idx]["value"]
        prev_gap = ((prev_male - prev_female) / prev_male) * 100 if prev_male != 0 else 0
        pp_change = gap - prev_gap
        detail, color = format_detail(pp_change, "pp", config["direction"])
    else:
        detail, color = "", "neutral"

    period = male_data[-1]["date"][:4] if is_annual(male_data) else format_period(male_data[-1]["date"])

    return {
        "value": config["format_value"].format(gap),
        "detail": detail,
        "detail_color": color,
        "period": period,
    }


def compute_composite_avg(config: dict, all_data: dict) -> dict | None:
    """Population-weighted average of multiple vectors."""
    # Get latest values for each territory
    values = []
    weights = []

    for v in config["vectors"]:
        data = all_data.get(v["id"])
        if not data:
            return None
        values.append(data[-1]["value"])

    # Get population weights if available
    if "population_vectors" in config:
        for pv in config["population_vectors"]:
            pdata = all_data.get(pv["id"])
            if not pdata:
                return None
            weights.append(pdata[-1]["value"])
    else:
        weights = [1] * len(values)

    total_weight = sum(weights)
    if total_weight == 0:
        return None

    avg = sum(v * w for v, w in zip(values, weights)) / total_weight

    # YoY: compute weighted average for year-ago period
    ref_data = all_data.get(config["vectors"][0]["id"])
    yoy_idx = get_yoy_index(ref_data)
    if yoy_idx is not None:
        prev_values = []
        for v in config["vectors"]:
            data = all_data.get(v["id"])
            if data and len(data) >= abs(yoy_idx):
                prev_values.append(data[yoy_idx]["value"])
            else:
                prev_values = None
                break

        if prev_values:
            prev_avg = sum(v * w for v, w in zip(prev_values, weights)) / total_weight
            pp_change = avg - prev_avg
            detail, color = format_detail(pp_change, "pp", config["direction"])
        else:
            detail, color = "", "neutral"
    else:
        detail, color = "", "neutral"

    period = format_period(ref_data[-1]["date"], is_quarterly(ref_data))

    return {
        "value": config["format_value"].format(avg),
        "detail": detail,
        "detail_color": color,
        "period": period,
    }


def compute_sum_yoy_pct(config: dict, all_data: dict) -> dict | None:
    """Sum multiple vectors and compute YoY % change."""
    total = 0
    for v in config["vectors"]:
        data = all_data.get(v["id"])
        if not data:
            return None
        total += data[-1]["value"]

    ref_data = all_data.get(config["vectors"][0]["id"])
    yoy_idx = get_yoy_index(ref_data)
    if yoy_idx is not None:
        prev_total = 0
        for v in config["vectors"]:
            data = all_data.get(v["id"])
            if data and len(data) >= abs(yoy_idx):
                prev_total += data[yoy_idx]["value"]
            else:
                prev_total = None
                break

        if prev_total and prev_total != 0:
            pct_change = ((total / prev_total) - 1) * 100
            detail, color = format_detail(pct_change, "%", config["direction"])
        else:
            detail, color = "", "neutral"
    else:
        detail, color = "", "neutral"

    period = format_period(ref_data[-1]["date"], is_quarterly(ref_data))

    return {
        "value": config["format_value"].format(total),
        "detail": detail,
        "detail_color": color,
        "period": period,
    }


def compute_combined_rate(config: dict, all_data: dict) -> dict | None:
    """Compute combined rate as sum(numerator_vectors) / sum(denominator_vectors) * 100.

    Used for combined employment rate across territories where the correct
    calculation is sum(employed) / sum(population_15+), not a weighted avg of rates.
    """
    num_vecs = [v for v in config["vectors"] if v.get("role") == "numerator"]
    den_vecs = [v for v in config["vectors"] if v.get("role") == "denominator"]
    if not num_vecs or not den_vecs:
        return None

    # Latest values
    num_total = 0
    den_total = 0
    for v in num_vecs:
        data = all_data.get(v["id"])
        if not data:
            return None
        num_total += data[-1]["value"]
    for v in den_vecs:
        data = all_data.get(v["id"])
        if not data:
            return None
        den_total += data[-1]["value"]

    if den_total == 0:
        return None
    rate = (num_total / den_total) * 100

    # YoY change in pp
    ref_data = all_data.get(num_vecs[0]["id"])
    yoy_idx = get_yoy_index(ref_data)
    if yoy_idx is not None:
        prev_num = 0
        prev_den = 0
        ok = True
        for v in num_vecs:
            data = all_data.get(v["id"])
            if data and len(data) >= abs(yoy_idx):
                prev_num += data[yoy_idx]["value"]
            else:
                ok = False
                break
        for v in den_vecs:
            data = all_data.get(v["id"])
            if data and len(data) >= abs(yoy_idx):
                prev_den += data[yoy_idx]["value"]
            else:
                ok = False
                break

        if ok and prev_den != 0:
            prev_rate = (prev_num / prev_den) * 100
            pp_change = rate - prev_rate
            detail, color = format_detail(pp_change, "pp", config["direction"])
        else:
            detail, color = "", "neutral"
    else:
        detail, color = "", "neutral"

    period = format_period(ref_data[-1]["date"], is_quarterly(ref_data))

    return {
        "value": config["format_value"].format(rate),
        "detail": detail,
        "detail_color": color,
        "period": period,
    }


COMPUTE_FUNCTIONS = {
    "rate_yoy_pp": compute_rate_yoy_pp,
    "level_yoy_pct": compute_level_yoy_pct,
    "level_qoq_pct": compute_level_qoq_pct,
    "count_yoy_pct": compute_count_yoy_pct,
    "share_pct": compute_share_pct,
    "wage_gap": compute_wage_gap,
    "composite_avg": compute_composite_avg,
    "sum_yoy_pct": compute_sum_yoy_pct,
    "combined_rate": compute_combined_rate,
}


def main():
    print("=" * 60)
    print("  FETCHING MINISTER METRIC DATA FROM STATISTICS CANADA")
    print("=" * 60)
    print()

    OUTPUT_DIR.mkdir(exist_ok=True)

    # Collect all unique vector IDs to fetch
    all_vectors = {}
    for key, config in MINISTER_VECTOR_MAP.items():
        for v in config["vectors"]:
            all_vectors[v["id"]] = v["periods"]
        if "population_vectors" in config:
            for v in config["population_vectors"]:
                all_vectors[v["id"]] = v["periods"]

    print(f"  Fetching {len(all_vectors)} unique vectors...")
    print()

    # Fetch all vectors
    fetched_data = {}
    success = 0
    fail = 0

    for vid, periods in all_vectors.items():
        print(f"  Fetching {vid}...", end=" ")
        data = fetch_vector(vid, periods)
        if data:
            fetched_data[vid] = data
            print(f"OK ({len(data)} points, latest: {data[-1]['date'][:10]})")
            success += 1
        else:
            print("FAILED")
            fail += 1
        time.sleep(2)

    print()
    print(f"  Vectors fetched: {success} OK, {fail} failed")
    print()

    # Compute latest blocks for each minister metric
    results = {}
    for key, config in MINISTER_VECTOR_MAP.items():
        compute_fn = COMPUTE_FUNCTIONS.get(config["compute"])
        if not compute_fn:
            print(f"  {key}: unknown compute type '{config['compute']}'")
            continue

        latest = compute_fn(config, fetched_data)
        if latest:
            # Apply fiscal/school year period format if configured
            pf = config.get("period_format")
            if pf in ("fiscal_year", "school_year") and latest["period"].isdigit() and len(latest["period"]) == 4:
                year = int(latest["period"])
                latest["period"] = f"{year}/{year + 1}"
            results[key] = latest
            detail_safe = latest['detail'].replace('\u2191', '^').replace('\u2193', 'v')
            print(f"  {key}: {latest['value']} ({detail_safe})")
        else:
            print(f"  {key}: no data")

    # Save
    output_path = OUTPUT_DIR / "minister_latest.json"
    output = {
        "_fetched_at": datetime.now(tz=timezone.utc).isoformat(),
        "_count": len(results),
        "metrics": results,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print()
    print("=" * 60)
    print(f"  COMPLETE: {len(results)}/{len(MINISTER_VECTOR_MAP)} metrics computed")
    print(f"  Output: {output_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
