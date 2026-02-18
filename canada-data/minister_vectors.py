"""
Statistics Canada vector ID map for minister metrics.
All vectors verified via WDS API on 2026-02-11.

Computation types:
  rate_yoy_pp     - Value is a rate (%), detail = YoY change in percentage points
  level_yoy_pct   - Value is a level ($, count), detail = YoY % change
  count_yoy_pct   - Same as level_yoy_pct but for integer counts
  composite_avg   - Population-weighted average of multiple vectors, with YoY pp change
  share_pct       - Compute ratio (1 - vector_b / vector_a) as percentage
  wage_gap        - Compute (male - female) / male as percentage
"""

MINISTER_VECTOR_MAP = {
    # ==========================================
    # PRIME MINISTER — macro headline metrics
    # ==========================================
    "pm_unemployment": {
        "vectors": [{"id": "v2062815", "periods": 24}],
        "compute": "rate_yoy_pp",
        "direction": "negative",  # lower unemployment = better
        "format_value": "{:.1f}%",
        "description": "Unemployment rate, both sexes, 15+, Canada, SA",
    },
    "pm_gdp_percapita": {
        "vectors": [{"id": "v1645315579", "periods": 20}],
        "compute": "level_qoq_pct",
        "direction": "positive",
        "format_value": "${:,.0f}",
        "description": "Real GDP per capita, chained 2017 dollars, quarterly",
    },

    # ==========================================
    # LABOUR FORCE SURVEY (14-10-0287-02)
    # ==========================================
    "hajdu_employment": {
        "vectors": [{"id": "v2062952", "periods": 24}],
        "compute": "rate_yoy_pp",
        "direction": "positive",
        "format_value": "{:.1f}%",
        "description": "Employment rate, both sexes, 25-54, Canada, SA",
    },
    "hajdu_youth": {
        "vectors": [{"id": "v2062844", "periods": 24}],
        "compute": "rate_yoy_pp",
        "direction": "positive",
        "format_value": "{:.1f}%",
        "description": "Employment rate, both sexes, 15-24, Canada, SA",
    },
    "valdez_female_unemployment": {
        "vectors": [{"id": "v2062833", "periods": 24}],
        "compute": "rate_yoy_pp",
        "direction": "negative",  # lower unemployment = better
        "format_value": "{:.1f}%",
        "description": "Unemployment rate, women+, 15+, Canada, SA",
    },

    # ==========================================
    # TRADE (12-10-0011-01)
    # ==========================================
    "leblanc_exports_us": {
        "vectors": [{"id": "v87008956", "periods": 24}],
        "compute": "level_yoy_pct",
        "direction": "positive",
        "format_value": "${:.1f}B",
        "scalar": 1_000,  # millions to billions
        "description": "Merchandise exports to the United States, customs-based, SA",
    },

    # ==========================================
    # CULTURE & EDUCATION
    # ==========================================
    "miller_immersion": {
        "vectors": [{"id": "v65927163", "periods": 10}],
        "compute": "count_yoy_pct",
        "direction": "positive",
        "format_value": "{:,.0f}",
        "period_format": "school_year",  # reported by school year e.g. 2023/2024
        "description": "French immersion enrollment, total, Canada",
    },
    "miller_culture_gdp": {
        "vectors": [{"id": "v65201463", "periods": 24}],
        "compute": "level_yoy_pct",
        "direction": "positive",
        "format_value": "${:.1f}B",
        "scalar": 1_000,  # API returns millions, display in billions
        "description": "GDP arts, entertainment and recreation (NAICS 71), Canada, chained 2017$",
    },
    "miller_culture_employment": {
        "vectors": [{"id": "v2057618", "periods": 24}],
        "compute": "count_yoy_pct",
        "direction": "positive",
        "format_value": "{:,.0f}K",
        "description": "Employment in information, culture and recreation, Canada, SA",
    },

    # ==========================================
    # JUSTICE & PUBLIC SAFETY
    # ==========================================
    "fraser_disposition": {
        "vectors": [{"id": "v62472254", "periods": 10}],
        "compute": "level_yoy_pct",
        "direction": "negative",  # shorter = better
        "format_value": "{:.0f} days",
        "period_format": "fiscal_year",  # reported by fiscal year e.g. 2023/2024
        "description": "Median elapsed time, total criminal cases, Canada",
    },
    "anandasangaree_hatecrimes": {
        "vectors": [{"id": "v111901802", "periods": 10}],
        "compute": "count_yoy_pct",
        "direction": "negative",  # fewer = better
        "format_value": "{:,.0f}",
        "description": "Total police-reported hate crime incidents, Canada",
    },
    "anandasangaree_homicides": {
        "vectors": [{"id": "v1540422", "periods": 10}],
        "compute": "count_yoy_pct",
        "direction": "negative",
        "format_value": "{:,.0f}",
        "description": "Number of homicide victims, Canada",
    },
    "anandasangaree_autotheft": {
        "vectors": [{"id": "v44357265", "periods": 10}],
        "compute": "count_yoy_pct",
        "direction": "negative",
        "format_value": "{:,.0f}",
        "description": "Motor vehicle theft incidents, Canada",
    },

    # ==========================================
    # FOREIGN AFFAIRS & INVESTMENT
    # ==========================================
    "anand_cdia": {
        "vectors": [{"id": "v7117682", "periods": 10}],
        "compute": "level_yoy_pct",
        "direction": "positive",
        "format_value": "${:.2f}T",
        "scalar": 1_000_000,  # millions to trillions
        "description": "Canadian direct investment abroad, total, all countries",
    },
    "anand_fdi": {
        "vectors": [{"id": "v7117859", "periods": 10}],
        "compute": "level_yoy_pct",
        "direction": "positive",
        "format_value": "${:.2f}T",
        "scalar": 1_000_000,  # millions to trillions
        "description": "Foreign direct investment in Canada, total, all countries",
    },

    # ==========================================
    # TRADE DIVERSIFICATION (composite: 1 - US/Total)
    # ==========================================
    "leblanc_diversification": {
        "vectors": [
            {"id": "v87008955", "periods": 24, "label": "total_exports"},
            {"id": "v87008956", "periods": 24, "label": "us_exports"},
        ],
        "compute": "share_pct",
        "direction": "positive",  # more diversification = better
        "format_value": "{:.1f}%",
        "description": "Export diversification (% non-U.S.)",
    },
    "sidhu_diversification": {
        "vectors": [
            {"id": "v87008955", "periods": 24, "label": "total_exports"},
            {"id": "v87008956", "periods": 24, "label": "us_exports"},
        ],
        "compute": "share_pct",
        "direction": "positive",
        "format_value": "{:.1f}%",
        "description": "Export diversification (% non-U.S.)",
    },

    # ==========================================
    # BUSINESS INVESTMENT (36-10-0104-01, GDP expenditure-based)
    # ==========================================
    "joly_investment": {
        "vectors": [{"id": "v62305733", "periods": 20}],
        "compute": "level_yoy_pct",
        "direction": "positive",
        "format_value": "${:.1f}B",
        "scalar": 1_000,  # millions to billions
        "description": "Business gross fixed capital formation, chained 2017$, SAAR",
    },

    # ==========================================
    # TRADE & INVESTMENT
    # ==========================================
    "sidhu_fdi": {
        "vectors": [{"id": "v61913732", "periods": 20}],
        "compute": "level_yoy_pct",
        "direction": "positive",
        "format_value": "${:.1f}B",
        "scalar": 1_000,  # millions to billions
        "description": "FDI inflows (direct investment liabilities), all countries, quarterly",
    },
    "joly_productivity": {
        "vectors": [{"id": "v111384113", "periods": 10}],
        "compute": "level_yoy_pct",
        "direction": "positive",
        "format_value": "${:.1f}/hr",
        "description": "Labour productivity, business sector, Canada",
    },

    # ==========================================
    # TRANSPORT
    # ==========================================
    "mackinnon_rail": {
        "vectors": [{"id": "v74869", "periods": 24}],
        "compute": "level_yoy_pct",
        "direction": "positive",
        "format_value": "{:.1f}M t",
        "scalar": 1_000_000,  # tonnes to millions of tonnes
        "description": "Rail total traffic carried, tonnes, Canada",
    },
    "mackinnon_port": {
        "vectors": [{"id": "v11743", "periods": 24}],
        "compute": "level_yoy_pct",
        "direction": "positive",
        "format_value": "{:.1f}M",
        "scalar": 1_000,  # thousands to millions (StatCan reports in thousands)
        "description": "Air passenger traffic, Canada",
    },

    # ==========================================
    # GENDER WAGE GAP (composite: male - female / male)
    # ==========================================
    "valdez_wagegap": {
        "vectors": [
            {"id": "v1481409741", "periods": 10, "label": "male_wage"},
            {"id": "v1481409745", "periods": 10, "label": "female_wage"},
        ],
        "compute": "wage_gap",
        "direction": "negative",  # smaller gap = better
        "format_value": "{:.1f}%",
        "description": "Gender wage gap (median hourly, male vs female)",
    },

    # ==========================================
    # TERRITORIES (combined rate: sum employed / sum population 15+)
    # ==========================================
    "chartrand_employment": {
        "vectors": [
            {"id": "v46438735", "periods": 24, "label": "yukon_emp", "role": "numerator"},
            {"id": "v46438837", "periods": 24, "label": "nwt_emp", "role": "numerator"},
            {"id": "v99443822", "periods": 24, "label": "nunavut_emp", "role": "numerator"},
            {"id": "v46438711", "periods": 24, "label": "yukon_pop", "role": "denominator"},
            {"id": "v46438813", "periods": 24, "label": "nwt_pop", "role": "denominator"},
            {"id": "v99443810", "periods": 24, "label": "nunavut_pop", "role": "denominator"},
        ],
        "compute": "combined_rate",
        "direction": "positive",
        "format_value": "{:.1f}%",
        "description": "Northern employment rate, combined 3 territories (sum employed / sum pop 15+), 3-mo MA, SA",
    },
    "chartrand_population": {
        "vectors": [
            {"id": "v4", "periods": 20, "label": "yukon"},
            {"id": "v6", "periods": 20, "label": "nwt"},
            {"id": "v7", "periods": 20, "label": "nunavut"},
        ],
        "compute": "sum_yoy_pct",
        "direction": "positive",
        "format_value": "{:,.0f}",
        "description": "Combined population of three territories",
    },

    # ==========================================
    # AGRICULTURE
    # ==========================================
    "macdonald_income": {
        "vectors": [{"id": "v8620", "periods": 10}],
        "compute": "level_yoy_pct",
        "direction": "positive",
        "format_value": "${:.1f}B",
        "scalar": 1_000_000,  # thousands to billions (StatCan reports in thousands)
        "description": "Realized net farm income, Canada",
    },
    "macdonald_productivity": {
        "vectors": [{"id": "v170328", "periods": 20}],
        "compute": "level_yoy_pct",
        "direction": "positive",
        "format_value": "${:.1f}B",
        "scalar": 1_000_000,  # thousands to billions
        "description": "Total farm cash receipts, Canada, quarterly",
    },

    # ==========================================
    # TOURISM
    # ==========================================
    "valdez_tourism": {
        "vectors": [{"id": "v81364", "periods": 20}],
        "compute": "level_qoq_pct",
        "direction": "positive",
        "format_value": "${:.1f}B",
        "scalar": 1_000,  # millions to billions
        "description": "Tourism spending in Canada, chained 2017$, SA",
    },

}
