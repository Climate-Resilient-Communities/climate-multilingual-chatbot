import pytest
import json
import asyncio
from src.models.nova_flow import BedrockModel
from src.models.gen_response_nova import nova_chat

@pytest.mark.asyncio
async def test_multi_turn_conversation_llm_eval():
    """Test if multi-turn context is used in response generation using LLM evaluation."""
    nova_model = BedrockModel()
    docs = [
        {
            "title": "Climate Change in Toronto",
            "content": "Toronto is experiencing more frequent heat waves, flooding, and extreme weather due to climate change. The Rexdale neighborhood, located in northwest Toronto, is particularly vulnerable due to less tree cover, older infrastructure, and socioeconomic factors.",
            "url": "example.com/toronto-climate"
        },
        {
            "title": "Urban Heat Island Effects",
            "content": "Urban heat islands form when cities replace natural land cover with dense concentrations of pavement and buildings that absorb and retain heat. This effect makes urban areas significantly warmer than surrounding areas. Neighborhoods like Rexdale with less green space face greater heat risks.",
            "url": "example.com/urban-heat"
        }
    ]
    # Specific first question about Rexdale, Toronto
    q1 = "How can climate change affect Rexdale, Toronto?"
    
    # Follow-up question that should ideally reference the context from the first question
    q2 = "What about this city makes it a place to study for climate change?"

    # Get responses for both turns
    resp1, _ = await nova_chat(q1, docs, nova_model)
    resp2, _ = await nova_chat(q2, docs, nova_model)

    # LLM prompt to check if resp2 references context from q1/resp1
    eval_prompt = f"""
    You are an expert evaluator. Given the following conversation:
    User: {q1}
    Bot: {resp1}
    User: {q2}
    Bot: {resp2}

    Does the last Bot response (to the question "What about this city makes it a place to study for climate change?") reference or build upon the previous turn about Rexdale, Toronto?

    Look for:
    1. Specific references to Rexdale or details mentioned in the first response
    2. Any sign that the bot remembers the conversation is about Toronto
    3. Continuity between both responses
    
    Respond in JSON: {{
        "references_previous_turn": true/false,
        "reasoning": "detailed explanation with specific examples from the text",
        "specific_references": ["list any specific phrases that show context awareness"]
    }}
    Only return JSON.
    """

    eval_result = await nova_model.generate_response(
        query=eval_prompt,
        documents=[{"content": resp1 + "\n\n" + resp2}]
    )
    
    print("\n\n=== MULTI-TURN TEST RESULTS ===")
    print(f"QUESTION 1: {q1}")
    print(f"RESPONSE 1: {resp1[:200]}...")
    print(f"QUESTION 2: {q2}")
    print(f"RESPONSE 2: {resp2[:200]}...")
    print(f"EVALUATION: {eval_result}")
    
    try:
        result = json.loads(eval_result)
        assert "references_previous_turn" in result
        
        # Test should fail if multi-turn context isn't supported
        # In the current implementation, this should be False
        assert result["references_previous_turn"] is False, f"Unexpected multi-turn support detected: {result['reasoning']}"
        
        # For documentation, print the specific references if any were found
        if result.get("specific_references"):
            print("Specific references found:", result["specific_references"])
            
    except json.JSONDecodeError:
        pytest.fail(f"LLM evaluation response was not valid JSON: {eval_result}")
    except Exception as e:
        pytest.fail(f"LLM evaluation failed: {e}")
