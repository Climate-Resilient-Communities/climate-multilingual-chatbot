#!/usr/bin/env python3
"""
Test Command-A Specific Languages
=================================

Debug conversation history formatting specifically for Command-A languages.
This will help us identify and fix the Cohere conversation history issue.
"""

import asyncio
import sys
import os
import json
import time
import warnings

# Filter out transformer warnings
warnings.filterwarnings("ignore", message="You're using a XLMRobertaTokenizerFast tokenizer")
warnings.filterwarnings("ignore", message=".*XLMRobertaTokenizerFast.*", category=UserWarning)
warnings.filterwarnings("ignore", category=UserWarning, module="transformers")

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.models.climate_pipeline import ClimateQueryPipeline

async def evaluate_context_synthesis(first_query, first_response, follow_up_query, follow_up_response, pipeline):
    """
    Use LLM to evaluate if the follow-up response demonstrates proper context synthesis.
    Returns a dict with 'has_context' (bool), 'display' (str), and 'reasoning' (str).
    """
    try:
        # Create evaluation prompt
        evaluation_prompt = f"""
        Analyze this conversation to determine if the follow-up response demonstrates proper context synthesis.

        CONVERSATION:
        User: {first_query}
        Assistant: {first_response[:300]}...

        User: {follow_up_query} 
        Assistant: {follow_up_response[:300]}...

        EVALUATION CRITERIA:
        Does the second response show that the AI understood and built upon the context from the first conversation turn?

        Look for:
        1. References to concepts mentioned in the first response
        2. Logical continuation of the topic
        3. Building upon previously established context
        4. Connecting greenhouse gases to the climate change discussion from turn 1

        RESPOND IN JSON FORMAT:
        {{
            "has_context": true/false,
            "confidence": 0.0-1.0,
            "reasoning": "Brief explanation of why this shows good/poor context synthesis"
        }}

        Focus on whether the AI connected "greenhouse gases" (follow-up) to "climate change" (first query).
        """

        # Use the pipeline's Nova model to evaluate
        try:
            # Get the Nova model from the pipeline
            nova_model = getattr(pipeline, 'nova_model', None)
            if not nova_model:
                # Fallback to basic keyword detection
                return await basic_context_evaluation(follow_up_response)
            
            evaluation_result = await nova_model.content_generation(
                prompt=evaluation_prompt,
                system_message="You are an expert conversation analyst. Evaluate context synthesis accurately and return valid JSON."
            )
            
            # Try to parse JSON response
            import json
            try:
                result = json.loads(evaluation_result)
                has_context = result.get('has_context', False)
                confidence = result.get('confidence', 0.5)
                reasoning = result.get('reasoning', 'No reasoning provided')
                
                # Create display based on confidence
                if has_context and confidence > 0.8:
                    display = "✅ EXCELLENT"
                elif has_context and confidence > 0.6:
                    display = "✅ YES"
                elif confidence > 0.4:
                    display = "🟡 PARTIAL"
                else:
                    display = "⚠️ LIMITED"
                
                return {
                    'has_context': has_context,
                    'display': display,
                    'reasoning': reasoning,
                    'confidence': confidence
                }
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                has_basic = "greenhouse" in evaluation_result.lower() or "context" in evaluation_result.lower()
                return {
                    'has_context': has_basic,
                    'display': "✅ YES" if has_basic else "⚠️ LIMITED",
                    'reasoning': evaluation_result[:100] if evaluation_result else "JSON parse failed",
                    'confidence': 0.5
                }
                
        except Exception as e:
            print(f"LLM evaluation failed: {str(e)}")
            return await basic_context_evaluation(follow_up_response)
            
    except Exception as e:
        print(f"Context synthesis evaluation error: {str(e)}")
        return await basic_context_evaluation(follow_up_response)

async def basic_context_evaluation(response):
    """Fallback to basic keyword-based evaluation."""
    response_lower = response.lower()
    
    # Enhanced keyword detection
    climate_keywords = ["climate change", "global warming", "temperature", "weather"]
    greenhouse_keywords = ["greenhouse", "gas", "emission", "carbon", "co2", "methane"]
    connection_keywords = ["because", "due to", "causes", "leads to", "results in", "contributes"]
    
    has_climate = any(kw in response_lower for kw in climate_keywords)
    has_greenhouse = any(kw in response_lower for kw in greenhouse_keywords)
    has_connection = any(kw in response_lower for kw in connection_keywords)
    
    # Score based on presence of different types of keywords
    if has_climate and has_greenhouse and has_connection:
        return {'has_context': True, 'display': "✅ YES", 'reasoning': "Contains climate + greenhouse + connection words", 'confidence': 0.8}
    elif has_greenhouse and (has_climate or has_connection):
        return {'has_context': True, 'display': "🟡 PARTIAL", 'reasoning': "Contains some contextual connections", 'confidence': 0.6}
    elif has_greenhouse:
        return {'has_context': False, 'display': "⚠️ LIMITED", 'reasoning': "Only mentions greenhouse gases without context", 'confidence': 0.3}
    else:
        return {'has_context': False, 'display': "❌ NONE", 'reasoning': "No relevant keywords found", 'confidence': 0.1}

async def test_command_a_languages():
    """Test Command-A languages specifically."""
    print("🧪 COMMAND-A LANGUAGES CONVERSATION HISTORY TEST")
    print("=" * 55)
    
    # Test languages that should route to Command-A
    test_languages = [
        {'code': 'ar', 'name': 'arabic', 'query': 'ما هو تغير المناخ؟', 'multi_turn': 'أخبرني المزيد عن الغازات الدفيئة'},
        {'code': 'fr', 'name': 'french', 'query': 'Qu\'est-ce que le changement climatique?', 'multi_turn': 'Parlez-moi davantage des gaz à effet de serre'},
        {'code': 'ko', 'name': 'korean', 'query': '기후 변화란 무엇인가요?', 'multi_turn': '온실가스에 대해 더 알려주세요'},
    ]
    
    try:
        # Initialize pipeline
        print("Initializing pipeline...")
        pipeline = ClimateQueryPipeline(index_name="climate-change-adaptation-index-10-24-prod")
        print("✅ Pipeline initialized")
        
        for lang in test_languages:
            try:
                print(f"\n🌍 Testing {lang['name'].upper()} (should route to Command-A)")
                print("-" * 40)
                
                # Test 1: Simple query without history
                print(f"\n📝 Step 1: Simple query (no history)")
                print(f"Query: {lang['query']}")
                
                result1 = await asyncio.wait_for(
                    pipeline.process_query(
                        query=lang['query'],
                        language_name=lang['name'],
                        conversation_history=None
                    ),
                    timeout=60.0  # 60 second timeout
                )
                
                if result1.get("success"):
                    model_used = result1.get("model_used", "Unknown")
                    print(f"✅ SUCCESS: Simple query worked")
                    print(f"🤖 Model used: {model_used}")
                    print(f"📏 Response length: {len(result1.get('response', ''))}")
                    
                    # Accept both "Cohere" and "Command-A" as valid Command-A model responses
                    if model_used not in ["Cohere", "Command-A"]:
                        print(f"⚠️ WARNING: Expected Cohere Command-A, got {model_used}")
                        continue
                    else:
                        print(f"✅ Correctly using Command-A model (reported as: {model_used})")
                    
                    # Test 2: Multi-turn with conversation history
                    print(f"\n📝 Step 2: Multi-turn with conversation history")
                    print(f"Follow-up: {lang['multi_turn']}")
                    
                    # Format conversation history as expected by our test
                    conversation_history = [
                        {
                            "user": lang['query'],
                            "assistant": result1.get("response", "")[:200]  # Truncate for test
                        }
                    ]
                    
                    print(f"\n🔍 Debug: Conversation history format:")
                    print(f"   user: {conversation_history[0]['user'][:50]}...")
                    print(f"   assistant: {conversation_history[0]['assistant'][:50]}...")
                    
                    print(f"⏱️ Starting multi-turn test with 60s timeout...")
                    start_time = time.time()
                    
                    try:
                        # Add timeout to prevent hanging
                        result2 = await asyncio.wait_for(
                            pipeline.process_query(
                                query=lang['multi_turn'],
                                language_name=lang['name'],
                                conversation_history=conversation_history
                            ),
                            timeout=60.0  # 60 second timeout
                        )
                        
                        elapsed_time = time.time() - start_time
                        if result2.get("success"):
                            print(f"✅ SUCCESS: Multi-turn query worked! ({elapsed_time:.1f}s)")
                            print(f"🤖 Model used: {result2.get('model_used', 'Unknown')}")
                            print(f"📏 Response length: {len(result2.get('response', ''))}")
                            
                            # Test context synthesis with LLM evaluation
                            context_synthesis_result = await evaluate_context_synthesis(
                                first_query=lang['query'],
                                first_response=result1.get("response", ""),
                                follow_up_query=lang['multi_turn'],
                                follow_up_response=result2.get("response", ""),
                                pipeline=pipeline
                            )
                            print(f"🧠 Context synthesis: {context_synthesis_result['display']}")
                            if context_synthesis_result['reasoning']:
                                print(f"   💭 Reasoning: {context_synthesis_result['reasoning'][:100]}...")
                            
                        else:
                            print(f"❌ FAILED: Multi-turn query failed ({elapsed_time:.1f}s)")
                            print(f"Error: {result2.get('response', 'No error message')[:200]}")
                            
                    except asyncio.TimeoutError:
                        elapsed_time = time.time() - start_time
                        print(f"⏰ TIMEOUT: Multi-turn query timed out after {elapsed_time:.1f}s")
                        print(f"   This suggests a hanging API call or infinite loop")
                            
                    except Exception as e:
                        elapsed_time = time.time() - start_time
                        print(f"❌ EXCEPTION in multi-turn test ({elapsed_time:.1f}s): {str(e)}")
                        if "all elements in history must have a message" in str(e):
                            print(f"🔍 This is the conversation history formatting issue!")
                        # Print more detailed error info
                        import traceback
                        print(f"📋 Full error traceback:")
                        traceback.print_exc()
                        
                else:
                    print(f"❌ FAILED: Simple query failed")
                    print(f"Error: {result1.get('response', 'No error message')[:200]}")
                    
            except asyncio.TimeoutError:
                print(f"⏰ TIMEOUT: Simple query timed out after 60s for {lang['name']}")
                print(f"   This suggests API issues or infinite loops")
                
            except Exception as e:
                print(f"❌ EXCEPTION in {lang['name']} testing: {str(e)}")
                import traceback
                print(f"📋 Full error traceback:")
                traceback.print_exc()
                    
            print(f"\n✅ Completed testing {lang['name']}")
            
    except Exception as e:
        print(f"❌ FATAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

async def test_conversation_history_formats_cohere():
    """Test different conversation history formats specifically with Command-A/Cohere."""
    print(f"\n🔬 TESTING CONVERSATION HISTORY FORMATS WITH COMMAND-A")
    print("=" * 60)
    
    # Use Arabic since it should definitely route to Command-A
    test_lang = {'name': 'arabic', 'query': 'ما هو تغير المناخ؟', 'follow_up': 'أخبرني المزيد عن الغازات الدفيئة'}
    
    try:
        pipeline = ClimateQueryPipeline(index_name="climate-change-adaptation-index-10-24-prod")
        
        # Get base response
        print(f"📝 Getting base response in Arabic...")
        base_result = await pipeline.process_query(
            query=test_lang['query'],
            language_name=test_lang['name'],
            conversation_history=None
        )
        
        if not base_result.get("success"):
            print(f"❌ Base query failed, cannot test formats")
            return
        
        model_used = base_result.get("model_used", "Unknown")
        print(f"✅ Base response obtained using {model_used}")
        
        # Accept both "Cohere" and "Command-A" as valid
        if model_used not in ["Cohere", "Command-A"]:
            print(f"❌ ERROR: Expected Cohere Command-A, got {model_used}")
            return
        else:
            print(f"✅ Correctly using Command-A model (reported as: {model_used})")
            
        base_response = base_result.get("response", "")[:150]
        
        # Test our current format that's failing
        print(f"\n📝 Testing: {{user, assistant}} format (current failing format)")
        history_current = [
            {
                "user": test_lang['query'],
                "assistant": base_response
            }
        ]
        
        try:
            result = await pipeline.process_query(
                query=test_lang['follow_up'],
                language_name=test_lang['name'],
                conversation_history=history_current
            )
            
            if result.get("success"):
                print(f"✅ SUCCESS: Current format works!")
            else:
                print(f"❌ FAILED: Current format failed")
                print(f"   Error: {result.get('response', '')[:100]}")
        except Exception as e:
            print(f"❌ EXCEPTION with current format: {str(e)}")
            print(f"   This confirms the conversation history formatting issue")
            
    except Exception as e:
        print(f"❌ ERROR in format testing: {str(e)}")

async def main():
    """Main test function."""
    print("🎯 GOAL: Test Command-A languages and identify conversation history issue")
    print("🔧 Focus: Languages that should route to Cohere Command-A model")
    print()
    
    await test_command_a_languages()
    await test_conversation_history_formats_cohere()
    
    print(f"\n📋 NEXT STEPS:")
    print(f"1. Identify the exact conversation history format that works")
    print(f"2. Fix the format in our comprehensive test")
    print(f"3. Re-run comprehensive multilingual validation")

if __name__ == "__main__":
    asyncio.run(main())
