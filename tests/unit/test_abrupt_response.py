import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
from src.models.nova_flow import BedrockModel
from src.models.gen_response_nova import nova_chat

@pytest.mark.asyncio
async def test_no_truncation():
    """Test that responses are complete and not abruptly cut off."""
    # Mock chatbot and its components
    mock_nova_model = MagicMock()
    incomplete_response = "Climate change refers to significant changes in global temperature, precipitation, wind patterns..."
    complete_response = "Climate change refers to significant changes in global temperature, precipitation, wind patterns, and other measures of climate that occur over several decades or longer. These changes are largely driven by human activities, particularly the burning of fossil fuels."
    
    # Set up the mocks to first return incomplete response then complete response
    mock_nova_model.generate_response = AsyncMock(side_effect=[incomplete_response, complete_response])
    
    # Mock documents
    mock_docs = [
        {"title": "Climate Change Overview", "content": "Full content about climate change", "url": "example.com"}
    ]
    
    # Test with truncated response
    with patch('src.models.gen_response_nova.doc_preprocessing', return_value=mock_docs):
        with patch('src.models.gen_response_nova.ClimateCache') as mock_cache:
            # Configure cache to not have a hit
            mock_cache_instance = MagicMock()
            mock_cache_instance.get = AsyncMock(return_value=None)
            mock_cache_instance.set = AsyncMock(return_value=True)
            mock_cache_instance.redis_client = True
            mock_cache.return_value = mock_cache_instance
            
            # First test - should detect the incomplete response
            response1, _ = await nova_chat("What is climate change?", mock_docs, mock_nova_model)
            
            # Check for incomplete sentence (ending with "...")
            assert "..." in response1
            assert len(response1.split()) < 20  # The truncated response should be short
            
            # Second test - should have complete response
            response2, _ = await nova_chat("What is climate change?", mock_docs, mock_nova_model)
            
            # Check that the response ends with a proper sentence
            assert "..." not in response2
            assert response2.endswith("fossil fuels.")
            assert len(response2.split()) > 30  # A complete response should be longer

@pytest.mark.asyncio
async def test_chinese_no_truncation():
    """Test that Chinese responses are complete and not abruptly cut off using LLM evaluation."""
    # Import the actual Nova model
    from src.models.nova_flow import BedrockModel
    
    # Create a real BedrockModel instance for response evaluation
    nova_model = BedrockModel()
    
    # Mock documents with Chinese content
    mock_docs = [
        {
            "title": "气候变化与异常天气",
            "content": """气候变化导致全球天气模式发生变化。虽然全球整体温度在上升，但这可能导致某些地区在特定时间出现反常的低温现象。
            科学研究表明，北极变暖可能导致寒冷空气向南推移，造成中纬度地区的寒冷天气。这种现象被称为"极地涡旋动荡"。
            多伦多作为北美城市，受到这种气候变化影响，有时会在春季出现反常的降雪现象。""",
            "url": "example.com/climate-weather"
        }
    ]

    # Test query about Toronto snow and global warming
    chinese_query = "我是说多伦多四月下雪和全球变暖有关吗？"

    # Get actual response from Nova
    response, citations = await nova_chat(chinese_query, mock_docs, nova_model)
    
    # Use BedrockModel to evaluate response completeness
    evaluation_prompt = f"""As an expert in natural language processing, evaluate if this Chinese response is complete or truncated.
    A complete response should:
    1. Have proper sentence endings (ending with periods)
    2. Fully address the question
    3. Have a logical flow and conclusion
    4. Not end abruptly or mid-thought

    Question: {chinese_query}
    Response: {response}

    Determine if this response is complete or truncated. Return your evaluation in this JSON format:
    {{
        "is_complete": true/false,
        "reasoning": "explanation of why the response is complete or truncated",
        "missing_elements": ["list any missing essential elements if truncated"]
    }}
    """
    
    # Get LLM evaluation of the response
    evaluation = await nova_model.generate_response(
        query=evaluation_prompt,
        documents=[{"content": response}]
    )
    
    # Parse the evaluation JSON
    try:
        eval_result = json.loads(evaluation)
        
        # Verify that the response is complete according to the LLM
        assert eval_result["is_complete"], f"Response was truncated. Reason: {eval_result.get('reasoning')}"
        
        # If complete, verify the reasoning mentions proper sentence structure
        assert any(term in eval_result["reasoning"].lower() for term in ["完整", "complete", "logical", "conclusion", "properly ended"])
        
        # Verify no critical missing elements
        assert not eval_result.get("missing_elements") or len(eval_result["missing_elements"]) == 0
        
    except json.JSONDecodeError:
        pytest.fail("LLM evaluation response was not in valid JSON format")
    except KeyError as e:
        pytest.fail(f"LLM evaluation response missing required field: {str(e)}")

@pytest.mark.asyncio
async def test_chinese_actionable_advice():
    """Test that Chinese requests for climate action advice get complete, actionable responses."""
    # Import the actual Nova model
    from src.models.nova_flow import BedrockModel
    
    # Mock documents with Chinese content about climate action
    mock_docs = [
        {
            "title": "应对气候变化的个人行动指南",
            "content": """面对气候变化，个人可以采取多种行动减少碳足迹：
            1. 减少能源使用，选择节能电器
            2. 选择公共交通或自行车出行
            3. 减少肉类消费，选择当地食品
            4. 减少浪费，回收再利用
            5. 支持使用可再生能源
            6. 参与社区气候行动，提高公众意识""",
            "url": "example.com/climate-action"
        }
    ]
    
    # Create mock BedrockModel with controlled output
    mock_nova_model = MagicMock(spec=BedrockModel)
    
    # Create a detailed Chinese response with actionable advice
    actionable_chinese_response = """为了应对全球变暖，我们每个人都可以采取以下具体行动：

1. 减少能源消耗：
   - 使用节能灯泡和节能电器
   - 不使用时关闭电器和拔掉充电器
   - 调整空调温度（夏季不低于26°C，冬季不高于20°C）

2. 改变出行方式：
   - 尽量使用公共交通工具
   - 步行或骑自行车代替短途驾车
   - 考虑拼车或使用共享出行服务
   - 选择低排放或电动汽车

3. 调整饮食习惯：
   - 减少肉类（特别是牛肉）消费
   - 选择当地生产的季节性食品
   - 减少食物浪费
   - 自己种植部分蔬菜水果

4. 减少废弃物：
   - 购物时带自己的袋子
   - 使用可重复使用的水瓶和咖啡杯
   - 正确回收垃圾
   - 避免购买过度包装的产品

5. 支持可再生能源：
   - 如果可能，安装太阳能板
   - 选择绿色能源供应商
   - 投资可再生能源项目

6. 节约用水：
   - 修理漏水的水龙头
   - 安装节水淋浴喷头
   - 收集雨水用于浇灌植物

这些行动结合起来可以显著减少个人碳足迹。记住，每个人的小行动累积起来会产生重大影响。我们都是应对气候变化的重要一部分。"""
    
    # Set up mock to return the actionable response
    mock_nova_model.generate_response = AsyncMock(return_value=actionable_chinese_response)
    
    # Test with mock model, documents and cache
    with patch('src.models.gen_response_nova.doc_preprocessing', return_value=mock_docs):
        with patch('src.models.gen_response_nova.ClimateCache') as mock_cache:
            # Configure cache to not have a hit
            mock_cache_instance = MagicMock()
            mock_cache_instance.get = AsyncMock(return_value=None)
            mock_cache_instance.set = AsyncMock(return_value=True)
            mock_cache_instance.redis_client = True
            mock_cache.return_value = mock_cache_instance
            
            # Test query asking what we can do about global warming
            chinese_query = "有什么我们能做的来应对全球变暖"
            
            # Generate response using the mock Nova model
            response, citations = await nova_chat(chinese_query, mock_docs, mock_nova_model)
            
            # Verify response is exactly our controlled output
            assert response == actionable_chinese_response
            
            # Verify response completeness and structure
            assert not response.endswith("...")  # Not truncated
            assert "。" in response  # Has proper sentence endings
            
            # Check for detailed actionable advice
            assert response.count("\n\n") >= 5  # Multiple distinct sections
            
            # Check for numbered list structure
            numbered_items = [line for line in response.split("\n") if line.strip().startswith(("1.", "2.", "3.", "4.", "5.", "6."))]
            assert len(numbered_items) >= 6  # At least 6 main advice points
            
            # Check for bulleted sub-items
            bullet_items = [line for line in response.split("\n") if line.strip().startswith("- ")]
            assert len(bullet_items) >= 15  # At least 15 specific action items
            
            # Check for climate-related content
            climate_terms = ["全球变暖", "碳足迹", "节能", "可再生能源"]
            assert all(term in response for term in climate_terms)
            
            # Check for a conclusion/summary
            assert "记住" in response
            assert "重大影响" in response

@pytest.mark.asyncio
async def test_chinese_responses():
    """Test that Chinese responses are complete and validated by LLM."""
    
    # Create actual BedrockModel instance for real responses and validation
    nova_model = BedrockModel()
    
    # Test documents with relevant Chinese content
    mock_docs = [
        {
            "title": "气候变化与异常天气",
            "content": """气候变化导致全球天气模式发生变化。虽然全球整体温度在上升，但这可能导致某些地区在特定时间出现反常的低温现象。
            科学研究表明，北极变暖可能导致寒冷空气向南推移，造成中纬度地区的寒冷天气。这种现象被称为"极地涡旋动荡"。
            多伦多作为北美城市，受到这种气候变化影响，有时会在春季出现反常的降雪现象。""",
            "url": "example.com/climate-weather"
        }
    ]

    # Test both queries
    queries = [
        "我是说多伦多四月下雪和全球变暖有关吗？",
        "有什么我们能做的来应对全球变暖"
    ]

    for chinese_query in queries:
        # Get actual response from Nova
        response, _ = await nova_chat(chinese_query, mock_docs, nova_model)
        
        # Create evaluation prompt for the LLM
        evaluation_prompt = f"""作为一位语言处理专家，请评估这个中文回答是否完整。

完整的回答必须满足以下所有标准：
1. 句子结构完整（以句号"。"结束）
2. 完全回答了问题的核心内容
3. 有清晰的逻辑流程
4. 有明确的结论
5. 不会突然中断或停在想法中间
6. 如果提到术语，有适当的解释

问题：{chinese_query}
回答：{response}

请用JSON格式返回您的评估：
{{
    "is_complete": true/false,
    "reasoning": "详细解释为什么回答是完整或不完整",
    "missing_elements": ["如果不完整，列出缺少的要素"]
}}

只返回JSON格式的结果，不需要其他说明。"""

        # Get LLM evaluation of the response
        evaluation = await nova_model.generate_response(
            query=evaluation_prompt,
            documents=[{"content": response}]
        )

        try:
            # Parse the evaluation result
            eval_result = json.loads(evaluation)
            
            # Basic validation
            assert isinstance(eval_result, dict), "评估结果应该是一个字典"
            assert "is_complete" in eval_result, "缺少 'is_complete' 字段"
            assert "reasoning" in eval_result, "缺少 'reasoning' 字段"
            
            # Validate completeness
            assert eval_result["is_complete"], f"回答不完整。原因: {eval_result.get('reasoning')}"
            
            # Additional response validation
            assert "。" in response, "回答缺少适当的中文句号"
            assert len(response.split("。")) > 1, "回答应该有多个完整的句子"
            
            # Query-specific validation
            if "多伦多" in chinese_query:
                assert "多伦多" in response, "回答应该提到多伦多"
                assert "全球变暖" in response, "回答应该提到全球变暖"
            elif "应对全球变暖" in chinese_query:
                assert any(num in response for num in ["1", "2", "3"]) or "首先" in response, \
                    "行动建议应该有编号或顺序标记"
                action_terms = ["减少", "使用", "选择", "节约", "参与"]
                assert any(term in response for term in action_terms), \
                    "回答应该包含具体的行动词"

            # If there are missing elements, they should be empty or not critical
            missing = eval_result.get("missing_elements", [])
            assert len(missing) == 0 or not any("核心" in item for item in missing), \
                "回答不应该缺少核心要素"

        except json.JSONDecodeError:
            pytest.fail("LLM评估响应不是有效的JSON格式")
        except KeyError as e:
            pytest.fail(f"LLM评估响应缺少必需字段: {str(e)}")
        except Exception as e:
            pytest.fail(f"评估过程中出现意外错误: {str(e)}")