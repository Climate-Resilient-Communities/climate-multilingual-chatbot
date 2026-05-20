"""
Ingest Thorncliffe Park climate-resilience documents into Pinecone.

Usage:
    python -m scripts.ingest_thorncliffe_docs [--dry-run]

Requires: PINECONE_API_KEY, HF_TOKEN in environment.
Uses the same HFEmbedder and index as the main pipeline.
"""

import os
import sys
import hashlib
import logging
import argparse

import numpy as np
from pinecone import Pinecone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.utils.env_loader import load_environment
from src.models.cohere_flow import HFEmbedder

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

THORNCLIFFE_DOCUMENTS = [
    {
        "title": "Thorncliffe Park Flood Vulnerability — Don River Watershed",
        "url": "https://www.toronto.ca/services-payments/water-environment/managing-rain-melted-snow/basement-flooding/basement-flooding-protection-program/",
        "chunk_text": (
            "Thorncliffe Park is located within the Don River watershed, one of the most "
            "urbanized watersheds in Canada. The watershed's natural absorption capacity has "
            "been largely replaced by impervious surfaces (asphalt, concrete), causing rapid "
            "stormwater runoff and pollutant transport during heavy rain events. The Don River "
            "corridor, particularly along the Don Valley Parkway and Bayview Avenue, is prone "
            "to overbank flooding during intense spring rain and snowmelt. "
            "Thorncliffe Park has among the highest social vulnerability to flooding in Toronto, "
            "second only to the Black Creek neighbourhood. Contributing factors include high "
            "population density (54% above the Toronto average), predominantly low-income "
            "renter households, and aging high-rise building infrastructure from the 1960s-70s. "
            "The City of Toronto's Basement Flooding Protection Program provides sewer and "
            "drainage improvements citywide. A subsidy of up to 80% of costs (maximum $500) "
            "is available for home plumbing assessments, though this primarily targets owners "
            "of single-family to fourplex homes. For Thorncliffe Park's high-rise renter "
            "population, flood resilience depends on building-level infrastructure upgrades "
            "and municipal drainage improvements. Residents should sign up for Toronto weather "
            "alerts and know their building's emergency plan."
        ),
        "doc_keywords": ["flooding", "don river", "thorncliffe park", "stormwater", "watershed", "toronto"],
        "segment_keywords": ["flood vulnerability", "basement flooding", "don valley", "renter housing"],
    },
    {
        "title": "Thorncliffe Park Urban Heat Island and Extreme Heat Resources",
        "url": "https://www.toronto.ca/community-people/health-wellness-care/health-programs-advice/hot-weather/cool-spaces-near-you/",
        "chunk_text": (
            "Thorncliffe Park experiences significant urban heat island effects due to its "
            "built environment: approximately 30 mid-rise to high-rise concrete apartment "
            "towers built in the 1960s-1970s, with limited surrounding green space. The "
            "neighbourhood's population density is 54% higher than the Toronto average, "
            "concentrating heat exposure among residents. Many units in the older rental "
            "buildings lack air conditioning, and the City of Toronto has been working toward "
            "a health-based maximum indoor temperature standard of 26°C for rental units. "
            "During Heat Warnings, the City of Toronto activates its Heat Relief Network, "
            "opening 500+ cool spaces across the city including libraries, community centres, "
            "pools, splash pads, and civic buildings. Some locations operate 24 hours during "
            "Heat Warnings. Residents of Thorncliffe Park can find the nearest cool spaces "
            "using the City's online map at toronto.ca. "
            "Practical tips for high-rise residents during extreme heat: close blinds on "
            "sun-facing windows during the day, use fans with a damp towel for evaporative "
            "cooling, drink water regularly, check on elderly neighbours, and visit cool "
            "spaces during the hottest hours (noon to 5 PM). The East York Civic Centre "
            "and local library branches near Thorncliffe serve as cooling centres."
        ),
        "doc_keywords": ["extreme heat", "urban heat island", "cooling", "thorncliffe park", "toronto", "heat wave"],
        "segment_keywords": ["cool spaces", "heat relief", "high-rise", "air conditioning", "heat warning"],
    },
    {
        "title": "Thorncliffe Park Air Quality and Don Valley Parkway Emissions",
        "url": "https://www.airqualityontario.com/aqhi/today.php",
        "chunk_text": (
            "Thorncliffe Park's apartment towers are situated directly adjacent to the Don "
            "Valley Parkway (DVP), a major urban highway carrying over 100,000 vehicles per "
            "day. Communities within 200-500 metres of major highways face elevated levels of "
            "nitrogen dioxide (NO2), fine particulate matter (PM2.5), and other traffic-related "
            "air pollutants. Health research consistently shows that highway-adjacent residents "
            "experience higher rates of asthma, respiratory illness, cardiovascular disease, "
            "and reduced lung function, particularly among children and elderly residents. "
            "Lower-income and marginalized communities disproportionately bear these health "
            "impacts. Climate change is expected to worsen air quality through increased "
            "ground-level ozone formation during hotter summers and more frequent wildfire "
            "smoke events. "
            "Residents can monitor daily air quality using Ontario's Air Quality Health Index "
            "(AQHI) at airqualityontario.com. When the AQHI is high (7+), residents should "
            "reduce outdoor physical activity, keep windows closed, and use recirculated air "
            "settings on any ventilation systems. Vulnerable individuals (children, elderly, "
            "those with respiratory conditions) should take precautions at moderate AQHI "
            "levels (4-6). The City of Toronto's TransformTO strategy includes targets for "
            "reducing vehicle emissions through transit expansion and active transportation."
        ),
        "doc_keywords": ["air quality", "pollution", "DVP", "thorncliffe park", "toronto", "emissions"],
        "segment_keywords": ["highway pollution", "PM2.5", "NO2", "respiratory health", "AQHI"],
    },
    {
        "title": "Thorncliffe Park Tree Canopy and Green Infrastructure Programs",
        "url": "https://www.toronto.ca/services-payments/water-environment/environmental-grants-incentives/urban-forestry-grants-and-incentives/",
        "chunk_text": (
            "Thorncliffe Park is designated as a Neighbourhood Improvement Area (NIA) by the "
            "City of Toronto, and 23 of 33 NIAs across the city have below-average tree canopy "
            "cover (under 26.9%). Limited green space and tree canopy in the neighbourhood "
            "exacerbates urban heat island effects and reduces natural stormwater absorption. "
            "The City of Toronto's Urban Forestry Grants and Incentives program supports tree "
            "planting on private land. From 2017 to 2025, the program invested over $25.4 "
            "million, funded 247 projects, and planted more than 128,000 trees and shrubs. "
            "The program uses a tree equity approach to prioritize canopy growth in "
            "underserved neighbourhoods like Thorncliffe Park. "
            "The City also offers a Free Tree Program through which Toronto residents can "
            "request trees to be planted in front of their properties. Building managers and "
            "tenant associations in Thorncliffe Park can apply for urban forestry grants to "
            "improve green space around apartment buildings. Trees provide shade that can "
            "reduce indoor temperatures by 2-4°C, absorb stormwater runoff, filter air "
            "pollutants, and create community gathering spaces. The LEAF (Local Enhancement "
            "and Appreciation of Forests) program also operates a Low-Canopy Neighbourhood "
            "Greening Initiative targeting NIAs."
        ),
        "doc_keywords": ["tree canopy", "urban forestry", "green space", "thorncliffe park", "toronto"],
        "segment_keywords": ["tree planting", "NIA", "canopy cover", "LEAF program", "green infrastructure"],
    },
    {
        "title": "Thorncliffe Park Community Demographics and Climate Communication",
        "url": "https://www.toronto.ca/city-government/data-research-maps/neighbourhoods-communities/neighbourhood-profiles/",
        "chunk_text": (
            "Thorncliffe Park is home to approximately 21,000-30,000 residents across roughly "
            "1.4 square kilometres, making it one of Toronto's most densely populated "
            "neighbourhoods. Over 90% of residents identify as visible minorities, with a "
            "strong South Asian community (Pakistani, Indian, Bangladeshi, Afghan). The "
            "neighbourhood was designated a Neighbourhood Improvement Area (NIA) in 2014. "
            "Top non-English mother tongues include Urdu (24.4%), Pashto (5.1%), Tagalog "
            "(4.7%), Farsi/Persian (4.6%), Gujarati (4.1%), Arabic (3.5%), Bengali (2.0%), "
            "Greek (1.5%), Punjabi (1.4%), and Spanish (1.4%). English is spoken by 88.7% "
            "of the population. "
            "TNO — The Neighbourhood Organization (formerly Thorncliffe Neighbourhood Office) "
            "has served the community since 1985, providing multilingual services in 50+ "
            "languages at no cost. The new 67,000 square foot Thorncliffe Park Community Hub "
            "at East York Town Centre provides health, settlement, legal, family, and "
            "community services. Climate communication in Thorncliffe Park should be "
            "multilingual, culturally sensitive, and delivered through trusted community "
            "channels. Many residents are newcomers who may not be familiar with Canadian "
            "weather extremes or emergency preparedness systems."
        ),
        "doc_keywords": ["demographics", "thorncliffe park", "toronto", "multilingual", "newcomers"],
        "segment_keywords": ["population", "languages", "south asian", "community hub", "NIA"],
    },
    {
        "title": "Toronto Climate Strategy — TransformTO and ResilientTO",
        "url": "https://www.toronto.ca/services-payments/water-environment/environmentally-friendly-city-initiatives/transformto/",
        "chunk_text": (
            "TransformTO is the City of Toronto's climate action strategy targeting net-zero "
            "greenhouse gas emissions by 2040. The strategy was adopted in December 2021, "
            "and the second action plan (2026-2030) was adopted in December 2025, emphasizing "
            "equitable climate action with attention to vulnerable communities. Key actions "
            "include building retrofits, transit expansion, renewable energy deployment, and "
            "urban forestry expansion. "
            "ResilientTO is Toronto's resilience strategy, launched in 2019 after engagement "
            "with 8,000 residents and 75 partner organizations. It sets 10 goals and 27 "
            "actions across three pillars: people and neighbourhoods, infrastructure, and "
            "leadership. The strategy specifically acknowledges that climate impacts are "
            "shaped by systemic inequities including racism, poverty, precarious work, and "
            "insecure housing — factors present in Neighbourhood Improvement Areas like "
            "Thorncliffe Park. "
            "Toronto's Climate Risks report identifies key hazards for the city: extreme "
            "heat events (increasing in frequency and intensity), riverine and urban flooding "
            "(worsened by climate change and urbanization), ice storms, and deteriorating "
            "air quality from wildfire smoke and ground-level ozone. The report emphasizes "
            "that vulnerability is not evenly distributed — neighbourhoods with older housing "
            "stock, higher population density, lower incomes, and less green space face "
            "disproportionate risk. Community-level engagement and multilingual communication "
            "are identified as essential components of effective climate adaptation."
        ),
        "doc_keywords": ["TransformTO", "ResilientTO", "climate strategy", "toronto", "net zero"],
        "segment_keywords": ["climate action", "resilience", "equity", "adaptation", "2040 target"],
    },
    {
        "title": "Emergency Preparedness for Thorncliffe Park Residents",
        "url": "https://www.toronto.ca/community-people/public-safety-alerts/emergency-preparedness/",
        "chunk_text": (
            "Toronto residents, especially those in high-density neighbourhoods like "
            "Thorncliffe Park, should prepare for weather emergencies that are becoming more "
            "frequent due to climate change. Key emergencies include extreme heat events, "
            "severe thunderstorms, flooding, ice storms, and poor air quality from wildfire "
            "smoke. "
            "Every household should have an emergency kit with: 3 days of water (4 litres "
            "per person per day), non-perishable food, a battery-powered or hand-crank radio, "
            "a flashlight and batteries, a first aid kit, copies of important documents, cash "
            "in small bills, and any essential medications. High-rise residents should also "
            "know their building's evacuation routes and have a plan for sheltering in place "
            "during power outages. "
            "Sign up for Toronto Alerts (toronto.ca/alerts) to receive emergency notifications "
            "by email or text. Environment Canada weather alerts are available at "
            "weather.gc.ca. During extended power outages, check on elderly or isolated "
            "neighbours and go to the nearest emergency warming or cooling centre. "
            "For newcomers: Canada uses a public alerting system called Alert Ready that "
            "sends warnings to all compatible cell phones during life-threatening emergencies. "
            "No sign-up is required — alerts are automatic. The City of Toronto provides "
            "emergency information in multiple languages through 311 (call, text, or online)."
        ),
        "doc_keywords": ["emergency preparedness", "thorncliffe park", "toronto", "weather emergency"],
        "segment_keywords": ["emergency kit", "evacuation", "power outage", "Alert Ready", "high-rise"],
    },
    {
        "title": "Thorncliffe Park Urban Farmers — Community Gardens and Food Security",
        "url": "https://thorncliffeparkurbanfarmers.ca/",
        "chunk_text": (
            "Thorncliffe Park Urban Farmers is a grassroots organization working to improve "
            "food security, restore urban biodiversity, and foster environmental stewardship "
            "in one of Toronto's most densely populated neighbourhoods. Local residents "
            "volunteer their time maintaining two communal vegetable gardens located on "
            "residential apartment properties as well as fruit trees throughout the "
            "neighbourhood. All harvest is shared at no cost. "
            "The community gardens transform underused grass and pavement around high-rise "
            "towers into productive growing spaces, strengthening food security and community "
            "connections. In a neighbourhood characterized by high-rise buildings and limited "
            "green space, the gardens provide a rare outdoor gathering place while addressing "
            "climate resilience on multiple fronts: local food production reduces transport "
            "emissions, gardens absorb stormwater, plants improve local air quality, and "
            "green space reduces urban heat island effects. "
            "The program also teaches children about nature and tackles food insecurity, "
            "connecting newcomer families — many from agricultural backgrounds — with the "
            "land. Thorncliffe Park Urban Farmers is featured on Drawdown Toronto as a "
            "local climate solution. For residents interested in joining, volunteer "
            "opportunities are available throughout the growing season (May through October)."
        ),
        "doc_keywords": ["community garden", "food security", "urban farming", "thorncliffe park", "toronto"],
        "segment_keywords": ["urban farmers", "vegetable garden", "biodiversity", "food access", "volunteer"],
    },
    {
        "title": "Tower Renewal and High-Rise Retrofit Programs for Thorncliffe Park",
        "url": "https://www.toronto.ca/community-people/community-partners/apartment-building-operators/tower-renewal/hi-ris/",
        "chunk_text": (
            "Thorncliffe Park's approximately 30 apartment towers, built in the 1960s-1970s, "
            "are prime candidates for the City of Toronto's Tower Renewal programs. In 2013, "
            "Park Property Management completed a two-year rehabilitation of a 279-unit "
            "building at 53 Thorncliffe Park Drive (built circa 1968). The $5-million project "
            "included repointing bricks, installing high R-value windows, adding insulation, "
            "and recladding the entire structure to stop energy loss. The building's energy "
            "costs dropped by 20% following the retrofit. "
            "The City offers two main programs for similar buildings. The High-Rise Retrofit "
            "Improvement Support Program (Hi-RIS) provides financing for residential rental "
            "apartment buildings built before 1990, of three or more storeys, to increase "
            "energy efficiency and reduce greenhouse gas emissions while improving tenant "
            "comfort. As of November 2025, equity housing co-ops are also eligible. "
            "The Taking Action on Tower Renewal (TATR) program, launched May 2023, supports "
            "apartment building owners and operators in making energy efficiency improvements "
            "and revitalizing surrounding communities. These programs are critical for "
            "Thorncliffe Park because building energy use is a major source of greenhouse "
            "gas emissions, and retrofits directly benefit tenants through lower energy costs, "
            "better indoor air quality, and more comfortable temperatures during extreme heat "
            "and cold events. Building managers and landlords can apply through the City of "
            "Toronto's Tower Renewal portal."
        ),
        "doc_keywords": ["tower renewal", "retrofit", "energy efficiency", "thorncliffe park", "toronto", "high-rise"],
        "segment_keywords": ["Hi-RIS", "TATR", "insulation", "building envelope", "greenhouse gas"],
    },
    {
        "title": "Don River Stormwater Management and Flood Protection Infrastructure",
        "url": "https://www.toronto.ca/services-payments/water-environment/managing-rain-melted-snow/what-the-city-is-doing-stormwater-management-projects/lower-don-river-taylor-massey-creek-and-inner-harbour-program/",
        "chunk_text": (
            "The City of Toronto is undertaking the largest stormwater management program in "
            "its history, with a budget exceeding $3 billion, to improve water quality in "
            "the Lower Don River, Taylor-Massey Creek, and Toronto's Inner Harbour. The "
            "program addresses combined sewer overflows (CSOs) — events where heavy rainfall "
            "overwhelms the sewer system and sends untreated sewage mixed with stormwater "
            "into the Don River and Lake Ontario. Climate change is increasing the frequency "
            "and intensity of these overflow events. "
            "A key component is the Coxwell Bypass Tunnel: a 10.5-kilometre tunnel running "
            "at 50 metres depth parallel to the Don River, designed to capture, store, and "
            "transport combined sewer overflows for treatment at the Ashbridges Bay Treatment "
            "Plant. The overall program was approved by City Council in 2011, with "
            "construction spanning approximately 25 years (completion target: 2038). "
            "For Thorncliffe Park residents, this infrastructure is directly relevant: the "
            "neighbourhood sits within the Don River watershed, and stormwater from its "
            "dense, heavily paved landscape contributes to downstream flooding and CSO events. "
            "The Don Mouth Naturalization project at the Port Lands is also restoring the "
            "river's natural outlet, creating 1,000 metres of new river channel, 13 hectares "
            "of coastal wetland, and 4 hectares of terrestrial habitat. Flood protection "
            "milestones were reached in late 2024, with parks opening in 2025."
        ),
        "doc_keywords": ["stormwater", "don river", "flood protection", "infrastructure", "toronto", "CSO"],
        "segment_keywords": ["Coxwell tunnel", "combined sewer", "Don Mouth", "Port Lands", "watershed"],
    },
    {
        "title": "Grassroots Climate Action in Thorncliffe Park — TNO and Community Programs",
        "url": "https://tno-toronto.org/from-trash-to-transit-how-thorncliffe-park-is-driving-grassroots-climate-action/",
        "chunk_text": (
            "Thorncliffe Park has a growing ecosystem of grassroots climate action led by "
            "community organizations and funded through city programs. TNO — The Neighbourhood "
            "Organization serves as trustee for the City of Toronto's Neighbourhood Climate "
            "Action Grant, which funds local projects addressing climate change in equity-"
            "deserving communities. "
            "The 'I Am Green' Eco Forum, held in Thorncliffe Park, brings together grassroots "
            "voices to discuss how climate change affects racialized high-rise neighbourhoods "
            "and to build partnerships for locally-driven action. The forum connects residents "
            "with programs spanning gardening, youth engagement, recycling, food security, "
            "and environmental education. "
            "The Gateway Bike Hub, funded by the City of Toronto's Community Reduce and Reuse "
            "Program and run in partnership with TNO, provides bicycle repair workshops and "
            "promotes cycling as low-carbon transportation. This is especially relevant in "
            "Thorncliffe Park where many residents rely on public transit or walking. "
            "The Green Neighbours Network of Toronto (GNN) coordinates community tree walks "
            "in Thorncliffe Park with the Toronto Environmental Alliance, Don Valley West "
            "for Environmental Action, and Thorncliffe Park Urban Farmers, helping residents "
            "explore shade trees, fruit trees, and community gardens. These walks educate "
            "participants about the role of urban canopy in reducing heat and improving air "
            "quality. All programs are free and designed to be accessible to newcomer families "
            "with multilingual support."
        ),
        "doc_keywords": ["climate action", "grassroots", "TNO", "thorncliffe park", "toronto", "community"],
        "segment_keywords": ["eco forum", "bike hub", "GNN", "tree walk", "neighbourhood climate grant"],
    },
    {
        "title": "Toronto Climate Vulnerability Assessment — Neighbourhood Equity and Risk",
        "url": "https://www.toronto.ca/services-payments/water-environment/environmentally-friendly-city-initiatives/becoming-a-climate-ready-toronto/",
        "chunk_text": (
            "In 2025, the City of Toronto released 'Toronto's Climate Risks: Understanding "
            "Vulnerability Today, Preparing for Tomorrow,' a comprehensive climate change "
            "risk and vulnerability assessment. The report finds that climate impacts are "
            "not evenly distributed across the city: neighbourhoods with abundant tree cover, "
            "parks, and proximity to water remain noticeably cooler, while areas dominated "
            "by concrete and asphalt become dangerously hotter during heat waves. This "
            "geographic inequality means that during the same heat event, some residents "
            "face life-threatening conditions while others experience manageable discomfort. "
            "The assessment uses a Green Infrastructure Equity Index combining built "
            "environment and socio-economic variables. Neighbourhood Improvement Areas (NIAs) "
            "like Thorncliffe Park consistently score lower on these equity indices due to "
            "limited green space, aging building stock, higher population density, lower "
            "household incomes, and higher proportions of newcomers and renters. "
            "Climate change disproportionately affects equity-deserving communities who "
            "often face compounding impacts from inadequate infrastructure and social "
            "disparities. The report recommends community-level engagement, multilingual "
            "communication, and targeted investment in green infrastructure for NIAs. "
            "An interdivisional Climate Change Adaptation Action Plan is being developed "
            "with resident engagement to ensure actions are inclusive and locally relevant. "
            "The full report is available at toronto.ca."
        ),
        "doc_keywords": ["climate vulnerability", "equity", "risk assessment", "toronto", "NIA"],
        "segment_keywords": ["heat inequality", "green infrastructure", "equity index", "adaptation plan"],
    },
    {
        "title": "C40 Students Reinventing Cities — 'Flowlines' Design for Thorncliffe Park",
        "url": "https://www.c40reinventingcities.org/en/students/previous-winning-projects/thorncliffe-park-1840.html",
        "chunk_text": (
            "Thorncliffe Park was selected as the Toronto site for C40's third Students "
            "Reinventing Cities competition, a global initiative challenging university "
            "students to redesign urban areas for climate resilience. The winning project, "
            "'Flowlines,' was designed by team 'SixPod' — University of Guelph landscape "
            "architecture students (Emily Pham, Krish Jain, Ryan De Jong) and Toronto "
            "Metropolitan University urban planning students (Reid Hega, Bailey Hansen, "
            "Rafay Choudri). "
            "The design proposes closing sections of parking to create pedestrian community "
            "spaces for gatherings, cultural events, and business vendors, with flora-lined "
            "pathways connecting green spaces throughout Thorncliffe. It includes pollinator "
            "gardens and insect hotels to improve ecology and stormwater quality, aiming to "
            "reconnect Thorncliffe Park with the Don Valley River system. The project is "
            "contextualized within the major neighbourhood transformation underway due to the "
            "Ontario Line, a new 15.6 km rapid transit line that will include a station at "
            "Thorncliffe Park. The Flowlines design provides a community-vetted vision for "
            "climate-resilient neighbourhood design integrating stormwater management, "
            "ecological restoration, heat mitigation through green infrastructure, and active "
            "transportation."
        ),
        "doc_keywords": ["C40", "Reinventing Cities", "Flowlines", "thorncliffe park", "climate design"],
        "segment_keywords": ["urban design", "Ontario Line", "pollinator garden", "green infrastructure"],
    },
    {
        "title": "Deep Building Retrofits for High-Rise Affordable Housing in Toronto",
        "url": "https://taf.ca/retrofit-of-affordable-seniors-building-aims-for-deep-decarbonization/",
        "chunk_text": (
            "Toronto Community Housing Corporation (TCHC), Canada's largest social housing "
            "provider, is undertaking deep energy retrofits applicable to Thorncliffe Park's "
            "aging high-rise stock. Since 2019, TCHC's Facilities Management has invested "
            "$340 million on capital retrofit projects in 39 communities, benefitting more "
            "than 6,000 homes. The energy retrofit initiative targets at least 30% reduction "
            "in annual net utility costs and GHG emissions per building. "
            "A flagship project at 575 Danforth Road (announced September 2024), a partnership "
            "between The Atmospheric Fund (TAF) and TCHC, targets an 80% reduction in carbon "
            "intensity at a 1958-built seniors' residence. It aims for EnerPHIT certification "
            "(Passive House standard for retrofits) and includes fuel-switching to electric "
            "heat pumps, prefabricated envelope overcladding, and individual temperature "
            "controls as a resilience measure against extreme summer heat. A separate TAF-TCHC "
            "project installs mini-split heat pumps in a North York family housing building, "
            "targeting 50% energy and carbon reductions while providing cooling that residents "
            "previously lacked, with projected utility savings exceeding $5 million over 20 "
            "years. These retrofit models demonstrate how deep decarbonization can "
            "simultaneously address climate mitigation, heat resilience, energy poverty, and "
            "housing quality in buildings similar to Thorncliffe Park's 1960s-70s towers."
        ),
        "doc_keywords": ["deep retrofit", "TCHC", "heat pump", "decarbonization", "toronto", "affordable housing"],
        "segment_keywords": ["EnerPHIT", "Passive House", "Atmospheric Fund", "energy poverty", "overcladding"],
    },
    {
        "title": "Ontario Line Thorncliffe Park Station and Transit-Oriented Community",
        "url": "https://www.metrolinx.com/en/projects-and-programs/ontario-line/what-were-building/thorncliffe-park-station-and-msf",
        "chunk_text": (
            "The Ontario Line, a new 15.6 km rapid transit line, will include a station at "
            "Thorncliffe Park, bringing rapid transit to a historically underserved community "
            "that currently relies heavily on bus service. The Thorncliffe Park Station "
            "Community Liaison Committee was established in November 2024, with construction "
            "actively underway. The Transit-Oriented Community planned around the station "
            "includes 2,660 residential units and approximately 980 new jobs. "
            "The Ontario Line has direct climate resilience implications for Thorncliffe Park. "
            "Rapid transit reduces car dependency and associated greenhouse gas emissions. "
            "Residents will gain faster access to cooling centres, emergency services, and "
            "employment during extreme weather events. The station area development presents "
            "an opportunity to integrate green infrastructure, stormwater management, and "
            "urban canopy expansion into the neighbourhood transformation. "
            "However, the construction period brings challenges: disruption to local transit "
            "routes, construction dust and noise, and potential displacement pressure from "
            "rising property values near the new station. Community engagement through the "
            "liaison committee is focused on ensuring benefits reach existing residents, "
            "particularly newcomer and low-income families."
        ),
        "doc_keywords": ["Ontario Line", "transit", "Thorncliffe Park", "station", "metrolinx"],
        "segment_keywords": ["rapid transit", "transit-oriented community", "construction", "TOC", "mobility"],
    },
    {
        "title": "TTC Extreme Weather Resilience and Transit Climate Adaptation",
        "url": "https://www.ttc.ca/about-the-ttc/Moving-toward-a-sustainable-future/Innovation-and-Sustainability-Strategy",
        "chunk_text": (
            "Toronto experienced its highest annual precipitation on record in 2024, "
            "surpassing the 2008 record by 9%. On July 15-16, 2024, over 115 mm of rain fell "
            "within 24 hours, flooding 15 TTC subway stations and disrupting 9 streetcar "
            "routes with delays of 38-59 minutes per route. These events prompted the TTC "
            "Board to direct new planning based on updated climate projections. "
            "Capital budget lines related to extreme weather total $1.4 billion, of which "
            "only $360 million is funded in the 2025-2034 period. Key vulnerabilities include "
            "inadequate drainage for streetcar tracks, subway tunnels, and stations, plus "
            "deferred maintenance and aging pumping equipment. The TTC's Innovation and "
            "Sustainability Strategy (2024-2028) commits to net-zero greenhouse gas emissions "
            "by 2040 while increasing operational resilience. "
            "For Thorncliffe Park residents who rely heavily on TTC bus service, transit "
            "resilience directly affects daily mobility, access to employment, healthcare, "
            "and emergency services during extreme weather. When bus routes are disrupted by "
            "flooding or ice storms, high-density neighbourhoods with limited car ownership "
            "are disproportionately impacted. The future Ontario Line station at Thorncliffe "
            "will improve transit options but also introduces new infrastructure that must be "
            "designed for climate resilience from the outset."
        ),
        "doc_keywords": ["TTC", "transit resilience", "extreme weather", "flooding", "toronto"],
        "segment_keywords": ["subway flooding", "precipitation record", "bus service", "climate adaptation"],
    },
    {
        "title": "Toronto Public Health — Climate-Related Health Monitoring and Heat Mortality",
        "url": "https://www.toronto.ca/community-people/health-wellness-care/health-inspections-monitoring/public-health-impacts-of-climate-change-in-toronto/",
        "chunk_text": (
            "Toronto Public Health (TPH) monitors climate-related health impacts through a "
            "Phase 1 climate monitoring dashboard launched in 2026, visualizing public health "
            "and environmental surveillance indicators. TPH projects that heat-related "
            "mortality in Toronto will double by 2050 and triple by 2080. Air-pollution-"
            "related mortality is expected to increase approximately 20% by 2050 and 25% by "
            "2080, largely due to increased ground-level ozone. "
            "Research shows that people without in-home air conditioning are disproportionately "
            "likely to be born in another country, to rent their residence, and to live in "
            "apartment buildings — a profile that closely matches Thorncliffe Park's population. "
            "They are also more likely to be low-income and to live in community housing. "
            "Toronto was one of the first Canadian jurisdictions to adopt a Hot Weather Response "
            "Plan (1999) and has collaborated with Health Canada on extreme heat adaptation "
            "research since 2009. During Heat Warnings, the Heat Relief Network activates "
            "500+ cool spaces citywide. For Thorncliffe Park, where many residents are "
            "newcomers unfamiliar with Canadian heat extremes and live in older buildings "
            "without central cooling, proactive multilingual health communication and "
            "accessible cooling infrastructure are critical to preventing heat-related "
            "illness and death."
        ),
        "doc_keywords": ["public health", "heat mortality", "air pollution", "climate health", "toronto"],
        "segment_keywords": ["health dashboard", "mortality projections", "ozone", "newcomers", "cooling"],
    },
    {
        "title": "Thorncliffe Park Food Security — Community Programs and Climate Adaptation",
        "url": "https://donate.tno-toronto.org/tno-food-collaborative/",
        "chunk_text": (
            "Thorncliffe Park's food security infrastructure connects multiple programs with "
            "climate resilience dimensions. The TNO Food Collaborative serves 1,750 clients, "
            "providing monthly food hampers with fresh produce, eggs, dairy, and culturally "
            "appropriate food through a partnership between TNO and SummerLunchPlus. Marc "
            "Garneau Collegiate Institute, the only high school in Thorncliffe Park, runs "
            "a free breakfast and lunch program where student volunteers learn to cook "
            "sustainable meals for classmates, addressing high food bank usage. "
            "The Thorncliffe Park Urban Farmers provide a complementary local food production "
            "layer, with 680 kg of free organic produce distributed over four years from "
            "communal vegetable gardens and 20+ fruit trees. The organization received the "
            "2025 June Callwood Outstanding Achievement Award for Voluntarism from the "
            "Province of Ontario. A pollinator habitat restoration project, funded by the "
            "Olive Tree Foundation and administered by TNO, converts spaces overgrown with "
            "invasive species into pollinator-friendly habitats used as outdoor learning "
            "spaces. "
            "Food insecurity in low-income urban communities worsens under climate change due "
            "to food price volatility from extreme weather, heat-related crop failures, and "
            "supply chain disruptions. Local food production through community gardens builds "
            "adaptive capacity by providing supplemental food immune to supply chain shocks, "
            "while delivering co-benefits of green space, stormwater absorption, and heat "
            "mitigation."
        ),
        "doc_keywords": ["food security", "food collaborative", "urban farming", "thorncliffe park", "toronto"],
        "segment_keywords": ["food hamper", "pollinator habitat", "June Callwood", "school food program"],
    },
    {
        "title": "E-Heroes and Repair Cafe — Grassroots Emission Reduction in Thorncliffe Park",
        "url": "https://thorncliffehub.org/grassroots/",
        "chunk_text": (
            "E-Heroes is a community-based grassroots group founded in 2019 with members "
            "from Thorncliffe Park and Flemingdon Park representing diverse cultures and all "
            "age groups. The group focuses on education about indirect greenhouse gas emission "
            "reduction, identifying short- and long-term actions to reduce community-wide "
            "emissions in buildings, waste, and transportation. Their work contributes directly "
            "to the TransformTO strategy. E-Heroes participates in community events such as "
            "the Thorncliffe Park Family Ecofair with the theme 'Reduce, Reuse, Repair — "
            "and Share,' organized in partnership with For Our Kids and TNO. "
            "The Don Valley West for Environmental Action group hosts a Repair Cafe at the "
            "Thorncliffe Park Community Hub, promoting a circular repair economy. Residents "
            "bring broken electronics, clothing, and household items for free repair by "
            "volunteer experts, diverting waste from landfills and reducing the carbon "
            "footprint of manufacturing new goods. The Gateway Bike Hub's 'Earn-A-Bike' "
            "program complements this: participants learn bicycle assembly, repair, and "
            "maintenance over three days and receive a free refurbished bike, connecting "
            "cycling to climate goals and waste reduction. All programs are free and "
            "designed for newcomer families with limited English."
        ),
        "doc_keywords": ["E-Heroes", "repair cafe", "waste reduction", "thorncliffe park", "grassroots"],
        "segment_keywords": ["circular economy", "emissions reduction", "Earn-A-Bike", "ecofair"],
    },
    {
        "title": "Toronto Green Streets Program — Stormwater Infrastructure for NIAs",
        "url": "https://www.toronto.ca/services-payments/streets-parking-transportation/enhancing-our-streets-and-public-realm/green-streets/green-streets-projects/",
        "chunk_text": (
            "Toronto's Green Streets Program, established in 2017, integrates green "
            "infrastructure into streets, sidewalks, and boulevards to reduce air temperatures, "
            "enhance air quality, and manage stormwater. The program originated after a July "
            "2013 event when 60 mm of overnight rain caused the Don River to flood the Don "
            "Valley Parkway, prompting City Council to develop green infrastructure standards "
            "for stormwater management. Green streets incorporate bioswales, permeable "
            "pavement, rain gardens, and bioretention assets that capture and filter stormwater "
            "while cooling surrounding air through evapotranspiration. "
            "The City prioritizes Neighbourhood Improvement Areas that can benefit most from "
            "green infrastructure in terms of stormwater management, air quality, social "
            "equity, tree canopy, and climate resilience. In 2025, a pilot partnership with "
            "GreenForceTO launched to support community-led care of green infrastructure "
            "planters. Transportation Services partnered with RAINscapeTO and Building Up, "
            "two Employment Social Enterprises, to hire and train individuals from NIAs and "
            "people experiencing barriers to employment for maintenance of green streets "
            "infrastructure. For Thorncliffe Park, green streets represent an opportunity "
            "to reduce stormwater runoff entering the Don River watershed while creating "
            "green jobs and improving neighbourhood livability."
        ),
        "doc_keywords": ["green streets", "stormwater", "bioswale", "green infrastructure", "toronto", "NIA"],
        "segment_keywords": ["permeable pavement", "rain garden", "GreenForceTO", "DON River", "equity"],
    },
    {
        "title": "Flemingdon Park — Adjacent Neighbourhood Sharing Climate Programs",
        "url": "https://www.toronto.ca/city-government/accountability-operations-customer-service/long-term-vision-plans-and-strategies/toronto-strong-neighbourhoods-strategy/",
        "chunk_text": (
            "Flemingdon Park is an adjacent neighbourhood that shares deep demographic, "
            "geographic, and programmatic ties with Thorncliffe Park. Both are designated "
            "Neighbourhood Improvement Areas under Toronto's Strong Neighbourhoods Strategy. "
            "The Don River's western branch flows directly through both neighbourhoods before "
            "joining the eastern half of the watershed, making them part of the same flood "
            "risk zone and ecological corridor. "
            "Climate action in Flemingdon Park is closely linked to Thorncliffe Park through "
            "shared organizations: E-Heroes draws members from both communities, the Gateway "
            "Bike Hub at 10 Gateway Boulevard serves both neighbourhoods, and TNO's programs "
            "operate across both areas. The Thorncliffe Park Youth Wellness Hub, supported "
            "by Youth Wellness Hubs Ontario, serves youth in both neighbourhoods — communities "
            "with some of the highest concentrations of individuals under age 25 in the city. "
            "Flemingdon Park was selected for the Neighbourhood Streets Plan in 2024-25, with "
            "Phase 1 public engagement from May to July 2025. Residents of either neighbourhood "
            "can access programs in both, and climate communication should reflect this shared "
            "community identity."
        ),
        "doc_keywords": ["Flemingdon Park", "NIA", "thorncliffe park", "don river", "shared programs"],
        "segment_keywords": ["youth hub", "Gateway Bike Hub", "neighbourhood streets", "flood corridor"],
    },
]


def make_vector_id(title: str, url: str) -> str:
    raw = f"thorncliffe:{title}:{url}"
    return f"tp-{hashlib.sha256(raw.encode()).hexdigest()[:16]}"


def main():
    parser = argparse.ArgumentParser(description="Ingest Thorncliffe Park documents into Pinecone")
    parser.add_argument("--dry-run", action="store_true", help="Embed and print, but don't upsert to Pinecone")
    args = parser.parse_args()

    load_environment()

    index_name = os.getenv("PINECONE_INDEX_NAME", "climate-change-adaptation-index-10-24-prod")
    logger.info(f"Target index: {index_name}")

    logger.info("Initializing HFEmbedder (BGE-M3 via HuggingFace API)...")
    embedder = HFEmbedder()
    logger.info("Embedder ready")

    texts = [doc["chunk_text"] for doc in THORNCLIFFE_DOCUMENTS]
    logger.info(f"Embedding {len(texts)} documents...")
    result = embedder.encode(texts)
    dense_vecs = result["dense_vecs"]
    logger.info(f"Embeddings shape: {dense_vecs.shape}")

    vectors = []
    for i, doc in enumerate(THORNCLIFFE_DOCUMENTS):
        vec_id = make_vector_id(doc["title"], doc["url"])
        metadata = {
            "chunk_text": doc["chunk_text"],
            "title": doc["title"],
            "url": doc["url"],
            "doc_keywords": doc.get("doc_keywords", []),
            "segment_keywords": doc.get("segment_keywords", []),
            "section_title": "Thorncliffe Park Climate Resilience",
            "segment_id": f"thorncliffe-{i}",
        }
        vectors.append({
            "id": vec_id,
            "values": dense_vecs[i].tolist(),
            "metadata": metadata,
        })
        logger.info(f"  [{vec_id}] {doc['title'][:60]}...")

    if args.dry_run:
        logger.info("DRY RUN — skipping Pinecone upsert")
        for v in vectors:
            logger.info(f"  Would upsert: {v['id']} | dim={len(v['values'])} | text={len(v['metadata']['chunk_text'])} chars")
        return

    logger.info("Connecting to Pinecone...")
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    index = pc.Index(index_name)

    logger.info(f"Upserting {len(vectors)} vectors...")
    index.upsert(vectors=vectors)
    logger.info("Upsert complete")

    stats = index.describe_index_stats()
    logger.info(f"Index now has {stats.total_vector_count} total vectors")


if __name__ == "__main__":
    main()
