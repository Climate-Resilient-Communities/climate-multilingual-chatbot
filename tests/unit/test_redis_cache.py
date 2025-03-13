import pytest
from unittest.mock import Mock, patch
import json
import redis
from src.models.redis_cache import ClimateCache

@pytest.fixture
def mock_redis_client():
    mock = Mock()
    mock.ping.return_value = True
    return mock

@pytest.fixture
def cache_instance(mock_redis_client):
    with patch('redis.Redis', return_value=mock_redis_client):
        cache = ClimateCache()
        return cache

def test_successful_initialization(mock_redis_client):
    with patch('redis.Redis', return_value=mock_redis_client) as mock_redis:
        cache = ClimateCache()
        mock_redis.assert_called_once()
        assert cache.redis_client is not None

def test_failed_initialization():
    with patch('redis.Redis', side_effect=Exception("Connection failed")):
        cache = ClimateCache()
        assert cache.redis_client is None

def test_save_to_cache_success(cache_instance, mock_redis_client):
    test_data = {
        "response": "Test response",
        "citations": [
            {"title": "Test Doc", "content": "Test Content"}
        ],
        "faithfulness_score": 0.95
    }
    
    result = cache_instance.save_to_cache("test_key", test_data)
    
    assert result is True
    mock_redis_client.setex.assert_called_once()
    
    # Verify the data was properly serialized
    call_args = mock_redis_client.setex.call_args[0]
    assert call_args[0] == "test_key"
    assert isinstance(call_args[1], int)  # Check for integer TTL
    assert json.loads(call_args[2])["response"] == "Test response"

def test_save_to_cache_failure(cache_instance, mock_redis_client):
    mock_redis_client.setex.side_effect = Exception("Save failed")
    
    result = cache_instance.save_to_cache("test_key", {"data": "test"})
    assert result is False

def test_get_from_cache_hit(cache_instance, mock_redis_client):
    cached_data = {
        "response": "Cached response",
        "citations": []
    }
    mock_redis_client.get.return_value = json.dumps(cached_data)
    
    result = cache_instance.get_from_cache("test_key")
    
    assert result is not None
    assert result["response"] == "Cached response"

def test_get_from_cache_miss(cache_instance, mock_redis_client):
    mock_redis_client.get.return_value = None
    
    result = cache_instance.get_from_cache("test_key")
    assert result is None

def test_get_from_cache_error(cache_instance, mock_redis_client):
    mock_redis_client.get.side_effect = Exception("Retrieval failed")
    
    result = cache_instance.get_from_cache("test_key")
    assert result is None

def test_delete_cache_success(cache_instance, mock_redis_client):
    mock_redis_client.delete.return_value = 1
    result = cache_instance.delete_cache("test_key")
    assert result is True

def test_delete_cache_failure(cache_instance, mock_redis_client):
    mock_redis_client.delete.side_effect = Exception("Delete failed")
    result = cache_instance.delete_cache("test_key")
    assert result is False

def test_clear_cache_success(cache_instance, mock_redis_client):
    mock_redis_client.flushdb.return_value = True
    result = cache_instance.clear_cache()
    assert result is True

def test_clear_cache_failure(cache_instance, mock_redis_client):
    mock_redis_client.flushdb.side_effect = Exception("Clear failed")
    result = cache_instance.clear_cache()
    assert result is False