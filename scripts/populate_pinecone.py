"""
Script to populate Pinecone index with sample climate change documents.
This will create embeddings and upload them to your Pinecone index.
"""

import os
import sys
import asyncio
import uuid
from typing import List, Dict, Any
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pinecone import Pinecone
from FlagEmbedding import FlagModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Sample climate documents to populate the index
SAMPLE_DOCUMENTS = [
    {
        "title": "Climate Change Basics",
        "content": """Climate change refers to long-term shifts in global or regional climate patterns. It is largely attributed to human activities, particularly the emission of greenhouse gases like carbon dioxide from burning fossil fuels. The effects include rising global temperatures, melting ice caps, sea level rise, and more frequent extreme weather events. Understanding climate change is crucial for developing effective adaptation and mitigation strategies.""",
        "metadata": {
            "source": "Educational Material",
            "topic": "basics",
            "audience": "general",
            "year": 2024
        }
    },
    {
        "title": "Paris Climate Agreement",
        "content": """The Paris Agreement is a legally binding international treaty on climate change adopted by 196 countries in 2015. Its goal is to limit global warming to well below 2°C, preferably to 1.5°C, compared to pre-industrial levels. Countries submit nationally determined contributions (NDCs) outlining their climate action plans. The agreement includes provisions for climate finance, technology transfer, and capacity building to support developing countries.""",
        "metadata": {
            "source": "International Policy",
            "topic": "policy",
            "audience": "general",
            "year": 2015
        }
    },
    {
        "title": "Climate Change Impacts",
        "content": """Climate change impacts are already visible across the globe. These include more frequent heatwaves, droughts, and extreme precipitation events. Sea levels are rising due to thermal expansion and melting glaciers. Ecosystems are shifting, with species migrating to new areas. Agriculture is affected by changing precipitation patterns and temperatures. Coastal communities face increased flooding risks. These impacts disproportionately affect vulnerable populations.""",
        "metadata": {
            "source": "Scientific Research",
            "topic": "impacts",
            "audience": "general",
            "year": 2024
        }
    },
    {
        "title": "Climate Adaptation Strategies",
        "content": """Climate adaptation involves adjusting natural or human systems to actual or expected climate change effects. Strategies include building sea walls and flood defenses, developing drought-resistant crops, improving early warning systems, and creating green infrastructure. Urban planning must consider heat islands and flooding. Ecosystem-based adaptation uses natural systems like wetlands and forests to reduce climate risks. Community-based adaptation empowers local communities to implement solutions.""",
        "metadata": {
            "source": "Adaptation Guide",
            "topic": "adaptation",
            "audience": "practitioners",
            "year": 2024
        }
    },
    {
        "title": "Renewable Energy Solutions",
        "content": """Renewable energy sources like solar, wind, hydroelectric, and geothermal power are essential for reducing greenhouse gas emissions. Solar photovoltaic technology has become increasingly cost-effective. Wind power, both onshore and offshore, provides significant electricity generation. Hydroelectric power offers reliable baseload energy. Energy storage technologies like batteries help manage intermittent renewable sources. Transitioning to renewables creates jobs and improves energy security.""",
        "metadata": {
            "source": "Energy Guide",
            "topic": "mitigation",
            "audience": "general",
            "year": 2024
        }
    },
    {
        "title": "Greenhouse Gas Emissions",
        "content": """Greenhouse gases trap heat in Earth's atmosphere, causing global warming. The main greenhouse gases are carbon dioxide (CO2) from fossil fuel combustion, methane (CH4) from agriculture and waste, nitrous oxide (N2O) from fertilizers, and fluorinated gases from industrial processes. CO2 is the most significant, accounting for about 76% of emissions. Reducing emissions requires transitioning to clean energy, improving efficiency, and changing consumption patterns.""",
        "metadata": {
            "source": "Scientific Data",
            "topic": "emissions",
            "audience": "technical",
            "year": 2024
        }
    },
    {
        "title": "Sustainable Transportation",
        "content": """Transportation accounts for a significant portion of global greenhouse gas emissions. Sustainable alternatives include electric vehicles, public transit, cycling, and walking. Electric cars are becoming more affordable with improved battery technology. High-speed rail can replace short-haul flights. Sustainable aviation fuels and electric aircraft are being developed. Urban planning that reduces travel distances and promotes active transportation is crucial for emissions reduction.""",
        "metadata": {
            "source": "Transport Policy",
            "topic": "mitigation",
            "audience": "general",
            "year": 2024
        }
    },
    {
        "title": "Carbon Footprint Reduction",
        "content": """Individuals and organizations can reduce their carbon footprint through various actions. These include using renewable energy, improving energy efficiency, choosing sustainable transportation, eating less meat, reducing waste, and supporting carbon offset programs. Businesses can implement sustainability practices, use clean energy, and optimize supply chains. Governments can create policies that incentivize low-carbon activities and penalize high-emission practices.""",
        "metadata": {
            "source": "Action Guide",
            "topic": "mitigation",
            "audience": "general",
            "year": 2024
        }
    },
    {
        "title": "Climate Finance",
        "content": """Climate finance refers to funding for projects that address climate change through mitigation or adaptation. Developed countries committed to providing $100 billion annually to developing countries by 2020. Sources include public finance, private investment, and international climate funds like the Green Climate Fund. Climate finance supports renewable energy projects, adaptation infrastructure, and capacity building. Innovative mechanisms include green bonds and carbon markets.""",
        "metadata": {
            "source": "Financial Policy",
            "topic": "finance",
            "audience": "policy",
            "year": 2024
        }
    },
    {
        "title": "Canadian Climate Action",
        "content": """Canada has committed to net-zero emissions by 2050 and a 40-45% reduction below 2005 levels by 2030. The Pan-Canadian Framework on Clean Growth and Climate Change outlines federal climate action. Provinces like Ontario have their own climate plans. Key initiatives include carbon pricing, clean fuel standards, and investments in clean technology. Canada faces unique challenges with its cold climate, large geography, and resource-based economy.""",
        "metadata": {
            "source": "Government Policy",
            "topic": "policy",
            "audience": "canadian",
            "year": 2024,
            "region": "canada"
        }
    }
]

async def main():
    """Main function to populate the Pinecone index."""
    
    # Check environment variables
    api_key = os.getenv("PINECONE_API_KEY")
    index_name = os.getenv("PINECONE_INDEX_NAME", "climate-chatbot")
    
    if not api_key:
        print("❌ Error: PINECONE_API_KEY not found in environment variables")
        return
    
    print(f"🚀 Starting Pinecone population for index: {index_name}")
    
    # Initialize Pinecone
    try:
        pc = Pinecone(api_key=api_key)
        index = pc.Index(index_name)
        print(f"✅ Connected to Pinecone index: {index_name}")
    except Exception as e:
        print(f"❌ Error connecting to Pinecone: {e}")
        return
    
    # Initialize embedding model
    try:
        # Use the same model from your config
        embed_model_path = os.getenv("EMBED_MODEL_PATH", "BAAI/bge-m3")
        print(f"📥 Loading embedding model: {embed_model_path}")
        embed_model = FlagModel(embed_model_path, use_fp16=True)
        print(f"✅ Embedding model loaded successfully")
    except Exception as e:
        print(f"❌ Error loading embedding model: {e}")
        return
    
    # Process and upload documents
    vectors_to_upsert = []
    
    for i, doc in enumerate(SAMPLE_DOCUMENTS):
        try:
            print(f"📝 Processing document {i+1}/{len(SAMPLE_DOCUMENTS)}: {doc['title']}")
            
            # Create embedding for the document content
            text_to_embed = f"{doc['title']}\n\n{doc['content']}"
            embedding = embed_model.encode(text_to_embed)
            
            # Create vector data
            vector_id = str(uuid.uuid4())
            vector_data = {
                "id": vector_id,
                "values": embedding.tolist(),
                "metadata": {
                    "title": doc["title"],
                    "content": doc["content"],
                    "text": text_to_embed,  # Some systems expect 'text' field
                    **doc["metadata"]
                }
            }
            
            vectors_to_upsert.append(vector_data)
            print(f"   ✅ Embedded: {doc['title']} (dim: {len(embedding)})")
            
        except Exception as e:
            print(f"   ❌ Error processing {doc['title']}: {e}")
            continue
    
    # Upsert vectors to Pinecone
    if vectors_to_upsert:
        try:
            print(f"\n📤 Uploading {len(vectors_to_upsert)} vectors to Pinecone...")
            
            # Upsert in batches (Pinecone recommends batches of 100)
            batch_size = 100
            for i in range(0, len(vectors_to_upsert), batch_size):
                batch = vectors_to_upsert[i:i + batch_size]
                index.upsert(vectors=batch)
                print(f"   ✅ Uploaded batch {i//batch_size + 1}")
            
            print(f"🎉 Successfully uploaded {len(vectors_to_upsert)} documents to Pinecone!")
            
            # Check index stats
            stats = index.describe_index_stats()
            print(f"📊 Index stats: {stats}")
            
        except Exception as e:
            print(f"❌ Error uploading to Pinecone: {e}")
            return
    else:
        print("❌ No vectors to upload")
        return
    
    print("\n✅ Pinecone population complete! You can now test your chatbot.")

if __name__ == "__main__":
    asyncio.run(main())