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
