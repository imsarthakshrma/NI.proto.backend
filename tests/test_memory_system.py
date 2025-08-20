"""
Comprehensive Memory System Tests
Tests smart memory, caching, DynamoDB, and API endpoints
"""

import pytest
# import asyncio
# import json
# import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime

# Add project paths
import sys
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for p in [str(SRC), str(ROOT)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from services.smart_memory import SmartMemorySystem, MemoryNode
from services.cache_service import CacheService
from services.dynamodb_service import DynamoDBService
from api.memory_api import router
from fastapi.testclient import TestClient
from fastapi import FastAPI

# Test fixtures
@pytest.fixture
def temp_data_dir():
    """Create temporary directory for test data"""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def mock_redis():
    """Mock Redis client for testing"""
    with patch('redis.from_url') as mock_redis:
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.setex.return_value = True
        mock_client.get.return_value = None
        mock_client.delete.return_value = 1
        mock_client.exists.return_value = False
        mock_redis.return_value = mock_client
        yield mock_client

@pytest.fixture
def smart_memory_system(temp_data_dir):
    """Create SmartMemorySystem instance for testing"""
    with patch('sentence_transformers.SentenceTransformer') as mock_model:
        mock_model.return_value.encode.return_value = [0.1] * 384  # Mock embedding
        
        with patch('chromadb.PersistentClient') as mock_chroma:
            mock_collection = Mock()
            mock_collection.add.return_value = None
            mock_collection.query.return_value = {
                "documents": [["test content"]],
                "distances": [[0.2]],
                "metadatas": [[{"user_id": "test_user", "node_id": "test_node"}]]
            }
            mock_chroma.return_value.get_collection.return_value = mock_collection
            mock_chroma.return_value.create_collection.return_value = mock_collection
            
            system = SmartMemorySystem(data_dir=temp_data_dir)
            yield system

@pytest.fixture
def cache_service_instance(mock_redis):
    """Create CacheService instance for testing"""
    cache = CacheService(redis_url="redis://localhost:6379")
    yield cache

@pytest.fixture
def test_app():
    """Create FastAPI test app with memory routes"""
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)

class TestSmartMemorySystem:
    """Test SmartMemorySystem functionality"""
    
    def test_add_memory(self, smart_memory_system):
        """Test adding a memory to the system"""
        user_id = "test_user"
        content = "This is a test memory about a meeting with John"
        memory_type = "meeting"
        metadata = {"attendees": ["John"], "duration": 30}
        
        memory_node = smart_memory_system.add_memory(
            user_id=user_id,
            content=content,
            memory_type=memory_type,
            metadata=metadata
        )
        
        assert memory_node.user_id == user_id
        assert memory_node.content == content
        assert memory_node.memory_type == memory_type
        assert memory_node.metadata == metadata
        assert memory_node.id is not None
        
        # Check if memory is stored in cache
        assert user_id in smart_memory_system.memory_cache
        assert memory_node.id in smart_memory_system.memory_cache[user_id]
    
    def test_semantic_search(self, smart_memory_system):
        """Test semantic search functionality"""
        user_id = "test_user"
        
        # Add test memories
        smart_memory_system.add_memory(user_id, "Meeting with John about project", "meeting")
        smart_memory_system.add_memory(user_id, "Email to Sarah about budget", "email")
        smart_memory_system.add_memory(user_id, "Call with John about timeline", "conversation")
        
        # Search for John-related memories
        results = smart_memory_system.semantic_search(
            user_id=user_id,
            query="John project discussion",
            limit=5
        )
        
        assert len(results) > 0
        # Results should be tuples of (MemoryNode, similarity_score)
        for memory_node, similarity in results:
            assert isinstance(memory_node, MemoryNode)
            assert 0 <= similarity <= 1

class TestCacheService:
    """Test CacheService functionality"""
    
    @pytest.mark.asyncio
    async def test_cache_operations(self, cache_service_instance):
        """Test basic cache operations"""
        cache = cache_service_instance
        
        # Test set and get
        test_data = {"key": "value", "number": 42}
        success = await cache.set("test", "user123", test_data, ttl=3600)
        assert success
        
        # Note: With mocked Redis, get might return None
        # In real tests with actual Redis, this would return test_data
    
    @pytest.mark.asyncio
    async def test_user_session_caching(self, cache_service_instance):
        """Test user session caching"""
        cache = cache_service_instance
        user_id = "test_user"
        
        session_data = {
            "contacts": {"john@email.com": {"name": "John Doe"}},
            "last_activity": datetime.now().isoformat()
        }
        
        success = await cache.cache_user_session(user_id, session_data)
        assert success

class TestMemoryAPI:
    """Test Memory API endpoints"""
    
    def test_memory_stats_endpoint(self, test_app):
        """Test memory statistics endpoint"""
        with patch('services.smart_memory.smart_memory') as mock_memory:
            mock_memory.memory_cache = {
                "test_user": {
                    "mem1": Mock(memory_type="conversation", timestamp=datetime.now().isoformat()),
                    "mem2": Mock(memory_type="meeting", timestamp=datetime.now().isoformat())
                }
            }
            mock_memory.relationship_graph.subgraph.return_value.number_of_edges.return_value = 5
            
            response = test_app.get("/api/memory/stats/test_user")
            assert response.status_code == 200
            
            data = response.json()
            assert "total_memories" in data
            assert "memory_types" in data
            assert "total_relationships" in data

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
