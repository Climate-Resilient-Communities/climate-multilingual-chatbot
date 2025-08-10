#!/usr/bin/env python3
"""
Test Content Cleaning Issues
============================

Investigate "Content too short after cleaning" warnings in document retrieval.
This helps identify what's causing certain documents to be filtered out.
"""

import asyncio
import sys
import os
import time

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.models.climate_pipeline import ClimateQueryPipeline
from src.models.retrieval import clean_markdown_content

async def test_retrieval_with_monitoring():
    """Test retrieval while monitoring which documents get filtered."""
    print("🔍 CONTENT FILTERING MONITORING")
    print("=" * 35)
    
    try:
        # Initialize pipeline
        print("Initializing pipeline...")
        pipeline = ClimateQueryPipeline(index_name="climate-change-adaptation-index-10-24-prod")
        print("✅ Pipeline initialized")
        
        # Test queries that we know cause "content too short" warnings
        test_queries = [
            "urban green spaces health planning",
            "climate change adaptation guide",
            "flood protection program report",
            "Canada climate change national issues"
        ]
        
        print(f"\n📝 Testing {len(test_queries)} queries to trigger filtering...")
        
        total_filtered = 0
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n🔍 Query {i}: {query}")
            
            # Monitor the retrieval process
            result = await pipeline.process_query(
                query=query,
                language_name="english",
                conversation_history=None
            )
            
            if result.get("success"):
                print(f"✅ Query succeeded - response length: {len(result.get('response', ''))}")
            else:
                print(f"❌ Query failed: {result.get('response', 'No error')[:100]}")
            
            # Add small delay between queries
            await asyncio.sleep(1)
            
        print(f"\n📊 Check the logs above for 'Content too short after cleaning' warnings")
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

async def test_clean_markdown_function():
    """Test the clean_markdown_content function specifically."""
    print(f"\n🧹 TESTING CLEAN_MARKDOWN_CONTENT FUNCTION")
    print(f"=" * 45)
    
    # Test cases that might cause issues based on typical document content
    test_cases = [
        ("Empty string", ""),
        ("Only whitespace", "   \n\t  \n  "),
        ("Only markdown headers", "# \n## \n### \n#### \n"),
        ("Only links and images", "[Link](http://example.com) ![Image](image.jpg) [Another](http://test.com)"),
        ("Headers with minimal text", "# Title\n\n## Section\n\nA.\n\n### Subsection\n\nB."),
        ("Short meaningful content", "# Climate Guide\n\nClimate change is real."),
        ("Normal document content", """
        # Climate Change Adaptation Guide
        
        ## Introduction
        
        Climate change adaptation refers to the process of adjusting to actual or expected climate change and its effects.
        
        ### Key Strategies
        
        1. Infrastructure improvements
        2. Policy development  
        3. Community engagement
        
        For more information, visit [our website](http://example.com).
        """),
        ("Content with lots of formatting", """
        # **Important** Climate Guide
        
        ## _Section 1_
        
        > This is a quote about climate change.
        
        **Bold text** and *italic text* with `inline code`.
        
        - List item 1
        - List item 2
          - Nested item
        
        [Link text](http://example.com) 
        ![Image alt](image.png)
        
        | Table | Header |
        |-------|--------|
        | Cell  | Data   |
        """),
        ("Minimal content after cleaning", "# \n\n[Link only](http://example.com)\n\n## \n\nVery short."),
        ("Document title only", "Guide for Cities on Health-Oriented Planning and Use of Urban Green Spaces"),
    ]
    
    print(f"\n� Testing {len(test_cases)} content scenarios...")
    
    problematic_cases = []
    
    for name, content in test_cases:
        original_length = len(content)
        cleaned = clean_markdown_content(content)
        cleaned_length = len(cleaned.strip())
        
        passes_filter = cleaned_length >= 10
        reduction_percent = ((original_length - cleaned_length) / max(original_length, 1) * 100) if original_length > 0 else 0
        
        status = "✅ PASS" if passes_filter else "❌ FILTERED"
        
        print(f"\n📝 {name}")
        print(f"   � Original: {original_length} chars")
        print(f"   🧹 Cleaned: {cleaned_length} chars")
        print(f"   📉 Reduction: {reduction_percent:.1f}%")
        print(f"   {status}")
        
        if not passes_filter:
            problematic_cases.append({
                'name': name,
                'original': content,
                'cleaned': cleaned,
                'original_length': original_length,
                'cleaned_length': cleaned_length
            })
        
        # Show content samples for short inputs or problematic cases
        if original_length < 200 or not passes_filter:
            print(f"   📄 Original: {repr(content[:150])}")
            print(f"   🧹 Cleaned: {repr(cleaned[:150])}")
    
    # Summary of problematic cases
    if problematic_cases:
        print(f"\n⚠️ PROBLEMATIC CASES ANALYSIS")
        print(f"=" * 35)
        print(f"Found {len(problematic_cases)} cases that would be filtered out:")
        
        for case in problematic_cases:
            print(f"\n❌ {case['name']}")
            print(f"   🔍 Why filtered: {case['original_length']} → {case['cleaned_length']} chars")
            
            # Analyze what was removed
            if case['original_length'] == 0:
                print(f"   💡 Issue: Empty input")
            elif case['cleaned_length'] == 0:
                print(f"   💡 Issue: All content removed by cleaning (likely all markdown/formatting)")
            else:
                print(f"   💡 Issue: Content too aggressively cleaned")
    
    return len(problematic_cases)

async def analyze_cleaning_impact():
    """Analyze the potential impact of content cleaning threshold."""
    print(f"\n📊 CLEANING THRESHOLD IMPACT ANALYSIS")
    print(f"=" * 40)
    
    # Test different thresholds
    thresholds = [5, 10, 15, 20, 25, 50]
    
    # Sample realistic document fragments that might appear in retrieval
    realistic_samples = [
        "Climate change.",  # Very short but meaningful
        "See section 2.1.",  # Reference only
        "Figure 1: Temperature trends.",  # Caption
        "# Introduction\n\nClimate change is a serious issue.",  # Short but complete
        "For more information, contact us.",  # Generic text
        "Table of Contents",  # Navigation element
        "Page 1 of 15",  # Pagination
        "# Climate Adaptation\n\n## Overview\n\nAdaptation involves adjusting systems.",  # Decent content
        "",  # Empty
        "   \n\t  ",  # Whitespace only
    ]
    
    print(f"Testing {len(realistic_samples)} realistic document samples against different thresholds:")
    
    for threshold in thresholds:
        filtered_count = 0
        
        for sample in realistic_samples:
            cleaned = clean_markdown_content(sample)
            if len(cleaned.strip()) < threshold:
                filtered_count += 1
        
        kept_count = len(realistic_samples) - filtered_count
        percentage_kept = (kept_count / len(realistic_samples)) * 100
        
        print(f"   📏 Threshold {threshold:2d}: Keeps {kept_count:2d}/{len(realistic_samples)} samples ({percentage_kept:5.1f}%)")
    
    print(f"\n💡 Current threshold is 10 characters")
    print(f"   Lower threshold = more documents kept (but potentially more noise)")
    print(f"   Higher threshold = fewer documents kept (but higher quality)")

async def main():
    """Main test function."""
    print("🎯 GOAL: Investigate 'Content too short after cleaning' warnings")
    print("🔧 Focus: Understanding what content is being filtered and why")
    print()
    
    problematic_count = await test_clean_markdown_function()
    await analyze_cleaning_impact()
    await test_retrieval_with_monitoring()
    
    print(f"\n📋 FINDINGS & RECOMMENDATIONS:")
    print(f"1. Found {problematic_count} test cases that would be filtered out")
    print(f"2. Check logs above for real 'Content too short' warnings during retrieval")
    print(f"3. Current 10-character threshold may be appropriate for quality control")
    print(f"4. Consider investigating if important documents are being lost")
    print(f"5. Monitor if filtering affects retrieval quality significantly")

if __name__ == "__main__":
    asyncio.run(main())
