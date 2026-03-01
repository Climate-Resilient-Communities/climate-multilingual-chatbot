import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
from src.models.nova_flow import BedrockModel
from src.models.gen_response_nova import generate_chat_response
from tests.unit.conftest import parse_llm_json


@pytest.mark.asyncio
async def test_chinese_response_completeness():
    """Test that Chinese responses are complete and properly evaluated by the LLM."""

    nova_model = BedrockModel()

    mock_docs = [
        {
            "title": "气候变化与极端天气",
            "content": """多伦多近年来的天气模式变化显著。全球变暖导致气候系统获得更多能量，
            使得天气变得更加不稳定。虽然整体趋势是变暖，但短期内仍可能出现极端寒冷天气。
            这种现象与北极涡旋的变化有关，全球变暖可能导致极地气流异常，影响中纬度地区。""",
            "url": "example.com/weather-patterns"
        }
    ]

    chinese_query = "我是说多伦多四月下雪和全球变暖有关吗？"

    response, _ = await generate_chat_response(chinese_query, mock_docs, nova_model)

    evaluation_text = f"""作为一位语言处理专家，请评估这个中文回答是否完整或被截断。

完整的回答应该：
1. 有完整的句子结构（以句号结束）
2. 完全回答了问题的核心内容
3. 有清晰的逻辑流程和结论
4. 不会突然中断或停在想法中间

问题：{chinese_query}
回答：{response}

请用JSON格式返回您的评估：
{{
    "is_complete": true/false,
    "reasoning": "解释为什么回答是完整或被截断的",
    "missing_elements": ["如果被截断，列出缺少的要素"]
}}"""

    evaluation = await nova_model.generate_response(
        query=evaluation_text,
        documents=[{"content": response}]
    )

    try:
        eval_result = parse_llm_json(evaluation)

        assert isinstance(eval_result, dict), "Evaluation result should be a dictionary"
        assert "is_complete" in eval_result, "Missing 'is_complete' field"
        assert "reasoning" in eval_result, "Missing 'reasoning' field"

        if not eval_result["is_complete"]:
            pytest.fail(f"Response was incomplete. Reason: {eval_result['reasoning']}")

        # Model may respond in Chinese or English — validate completeness either way
        cjk_chars = sum(1 for c in response if '\u4e00' <= c <= '\u9fff')
        non_ws_chars = sum(1 for c in response if not c.isspace())
        is_chinese = non_ws_chars > 0 and (cjk_chars / non_ws_chars) > 0.1
        if is_chinese:
            assert "。" in response, "Response missing proper Chinese sentence endings"
            assert len(response.split("。")) > 1, "Response should have multiple complete sentences"
        else:
            assert "." in response, "Response missing proper English sentence endings"
            assert len(response.split(".")) > 2, "Response should have multiple complete sentences"

        assert "多伦多" in response or "toronto" in response.lower(), "Response should mention Toronto"
        assert "全球变暖" in response or "global warming" in response.lower() or "climate change" in response.lower(), \
            "Response should address global warming"

        assert len(eval_result["reasoning"]) > 20, "Reasoning should be detailed"

        missing = eval_result.get("missing_elements", [])
        assert len(missing) == 0 or not any("核心" in item for item in missing), "No critical elements should be missing"

    except json.JSONDecodeError:
        pytest.fail("LLM evaluation response was not in valid JSON format")
    except KeyError as e:
        pytest.fail(f"LLM evaluation response missing required field: {str(e)}")
    except Exception as e:
        pytest.fail(f"Unexpected error in evaluation: {str(e)}")


@pytest.mark.asyncio
async def test_chinese_response_actionable():
    """Test that Chinese responses about climate action are complete and actionable."""

    nova_model = BedrockModel()

    mock_docs = [
        {
            "title": "气候行动指南",
            "content": """应对气候变化需要采取具体行动。我们可以通过改变日常生活方式来减少碳排放，
            例如使用公共交通、节约能源、减少浪费等。每个人的小行动都能带来重大改变。""",
            "url": "example.com/climate-action"
        }
    ]

    chinese_query = "有什么我们能做的来应对全球变暖"

    response, _ = await generate_chat_response(chinese_query, mock_docs, nova_model)

    evaluation_text = f"""请评估这个关于气候行动的中文回答是否同时满足完整性和可执行性要求。

评估标准：
1. 完整性：句子结构完整，逻辑连贯，有明确结论
2. 可执行性：包含具体、可实施的行动建议

问题：{chinese_query}
回答：{response}

请用JSON格式返回评估结果：
{{
    "completeness": {{
        "is_complete": true/false,
        "reasoning": "完整性评估理由"
    }},
    "actionability": {{
        "is_actionable": true/false,
        "action_count": 0,
        "examples": ["具体行动示例"],
        "reasoning": "可执行性评估理由"
    }}
}}"""

    evaluation = await nova_model.generate_response(
        query=evaluation_text,
        documents=[{"content": response}]
    )

    try:
        eval_result = parse_llm_json(evaluation)

        assert eval_result["completeness"]["is_complete"], \
            f"Response incomplete: {eval_result['completeness']['reasoning']}"

        assert eval_result["actionability"]["is_actionable"], \
            f"Response not actionable: {eval_result['actionability']['reasoning']}"

        assert eval_result["actionability"]["action_count"] >= 3, \
            "Response should contain at least 3 concrete actions"

        # Model may respond in Chinese or English — validate structure either way
        cjk_chars = sum(1 for c in response if '\u4e00' <= c <= '\u9fff')
        non_ws_chars = sum(1 for c in response if not c.isspace())
        is_chinese = non_ws_chars > 0 and (cjk_chars / non_ws_chars) > 0.1
        if is_chinese:
            assert "。" in response, "Response should have proper Chinese sentence endings"
            action_terms = ["减少", "使用", "选择", "节约", "参与"]
            assert any(term in response for term in action_terms), \
                "Response should contain practical action verbs (Chinese)"
        else:
            assert "." in response, "Response should have proper English sentence endings"
            action_terms = ["reduce", "use", "support", "save", "walk", "bike", "energy", "recycle"]
            assert any(term in response.lower() for term in action_terms), \
                "Response should contain practical action verbs (English)"

        assert any(num in response for num in ["1", "2", "3"]) or \
               "首先" in response or "其次" in response or "-" in response, \
               "Response should have numbered points or sequential markers"

    except json.JSONDecodeError:
        pytest.fail("LLM evaluation response was not in valid JSON format")
    except KeyError as e:
        pytest.fail(f"LLM evaluation response missing required field: {str(e)}")
    except Exception as e:
        pytest.fail(f"Unexpected error in evaluation: {str(e)}")
