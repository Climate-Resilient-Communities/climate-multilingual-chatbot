"""
Critical URLs for Canada and Toronto Climate Action Plans
Updated: January 2025

This file contains the most current and authoritative URLs for government climate action 
plans and strategies that the chatbot should reference or link to.
"""

# Canada Federal Climate Action URLs (2025)
CANADA_CLIMATE_URLS = {
    # Primary departmental plan for 2025-26
    "environment_canada_2025_plan": "https://www.canada.ca/en/environment-climate-change/corporate/transparency/priorities-management/departmental-plans/2025-2026.html",
    
    # At-a-glance summary
    "environment_canada_2025_summary": "https://www.canada.ca/en/environment-climate-change/corporate/transparency/priorities-management/departmental-plans/2025-2026/dp-at-glance.html",
    
    # Overall climate plans and targets
    "canada_climate_plan_overview": "https://www.canada.ca/en/services/environment/weather/climatechange/climate-plan/climate-plan-overview.html",
    
    # Main climate plan page
    "canada_climate_plan": "https://www.canada.ca/en/services/environment/weather/climatechange/climate-plan.html",
    
    # National adaptation strategy
    "national_adaptation_strategy": "https://www.canada.ca/en/services/environment/weather/climatechange/climate-plan/national-adaptation-strategy.html"
}

# Toronto Climate Action URLs (2025) 
TORONTO_CLIMATE_URLS = {
    # Main TransformTO Net Zero Strategy page
    "transformto_main": "https://www.toronto.ca/services-payments/water-environment/environmentally-friendly-city-initiatives/transformto/",
    
    # Current Action Plan (2026-2030)
    "transformto_action_plan_2026_2030": "https://www.toronto.ca/services-payments/water-environment/environmentally-friendly-city-initiatives/transformto/transformto-net-zero-action-plan/",
    
    # Implementation and progress updates
    "transformto_implementation": "https://www.toronto.ca/services-payments/water-environment/environmentally-friendly-city-initiatives/transformto/transformto-implementation/",
    
    # Climate resilience
    "toronto_climate_resilience": "https://www.toronto.ca/services-payments/water-environment/environmentally-friendly-city-initiatives/climate-change-resilience/"
}

# Ontario Provincial Climate Action URLs
ONTARIO_CLIMATE_URLS = {
    "ontario_climate_action": "https://www.ontario.ca/page/climate-change-action-plan",
    "ontario_environment": "https://www.ontario.ca/page/environment-and-energy"
}

# All critical URLs combined for easy access
ALL_CRITICAL_URLS = {
    **CANADA_CLIMATE_URLS,
    **TORONTO_CLIMATE_URLS, 
    **ONTARIO_CLIMATE_URLS
}

# Key facts for 2025
CLIMATE_ACTION_FACTS_2025 = {
    "canada_2035_target": "45-50% reduction in GHG emissions below 2005 levels by 2035",
    "canada_2050_target": "Net-zero emissions by 2050",
    "toronto_2040_target": "Net-zero community-wide emissions by 2040", 
    "toronto_2030_target": "65% reduction in GHG emissions by 2030 (from 1990 baseline)"
}