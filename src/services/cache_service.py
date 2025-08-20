"""
Redis Caching Service - High-performance caching for Native IQ
User session caching, conversation history, and smart memory acceleration
"""

import json
import redis
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import pickle
import hashlib

@dataclass
class CacheEntry:
    """Represents a cached entry with metadata"""
    key: str
    value: Any
    created_at: str
    expires_at: Optional[str] = None
    access_count: int = 0
    last_accessed: str = None

class CacheService:
    """
    Redis-based caching service for Native IQ
    Handles user sessions, conversation history, and smart memory acceleration
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379", 
                 default_ttl: int = 3600):  # 1 hour default TTL
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        
        # Initialize Redis connection
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=False)
            self.redis_client.ping()  # Test connection
            print("Redis connection established")
        except Exception as e:
            print(f"Redis connection failed: {e}")
            print("Falling back to in-memory cache")
            self.redis_client = None
            self._memory_cache = {}  # Fallback in-memory cache
        
        # Cache key prefixes for organization
        self.prefixes = {
            "session": "ni:session:",
            "conversation": "ni:conv:",
            "contacts": "ni:contacts:",
            "memory": "ni:memory:",
            "opportunities": "ni:opps:",
            "nudges": "ni:nudges:",
            "embeddings": "ni:embed:",
            "graph": "ni:graph:",
            "user_stats": "ni:stats:"
        }
    
    def _make_key(self, prefix: str, identifier: str) -> str:
        """Create a standardized cache key"""
        return f"{self.prefixes.get(prefix, 'ni:')}{identifier}"
    
    def _serialize(self, value: Any) -> bytes:
        """Serialize value for Redis storage"""
        if isinstance(value, (str, int, float, bool)):
            return json.dumps(value).encode()
        return pickle.dumps(value)
    
    def _deserialize(self, data: bytes) -> Any:
        """Deserialize value from Redis"""
        try:
            # Try JSON first (for simple types)
            return json.loads(data.decode())
        except:
            # Fall back to pickle
            return pickle.loads(data)
    
    async def set(self, prefix: str, identifier: str, value: Any, 
                  ttl: Optional[int] = None) -> bool:
        """
        Set a value in cache with optional TTL
        """
        key = self._make_key(prefix, identifier)
        ttl = ttl or self.default_ttl
        
        try:
            if self.redis_client:
                serialized = self._serialize(value)
                result = self.redis_client.setex(key, ttl, serialized)
                return bool(result)
            else:
                # Fallback to memory cache
                expires_at = datetime.now() + timedelta(seconds=ttl)
                self._memory_cache[key] = {
                    "value": value,
                    "expires_at": expires_at
                }
                return True
        except Exception as e:
            print(f"Cache set error: {e}")
            return False
    
    async def get(self, prefix: str, identifier: str) -> Optional[Any]:
        """
        Get a value from cache
        """
        key = self._make_key(prefix, identifier)
        
        try:
            if self.redis_client:
                data = self.redis_client.get(key)
                if data:
                    return self._deserialize(data)
            else:
                # Fallback to memory cache
                if key in self._memory_cache:
                    entry = self._memory_cache[key]
                    if datetime.now() < entry["expires_at"]:
                        return entry["value"]
                    else:
                        del self._memory_cache[key]
            return None
        except Exception as e:
            print(f"Cache get error: {e}")
            return None
    
    async def delete(self, prefix: str, identifier: str) -> bool:
        """
        Delete a value from cache
        """
        key = self._make_key(prefix, identifier)
        
        try:
            if self.redis_client:
                result = self.redis_client.delete(key)
                return bool(result)
            else:
                if key in self._memory_cache:
                    del self._memory_cache[key]
                    return True
            return False
        except Exception as e:
            print(f"Cache delete error: {e}")
            return False
    
    async def exists(self, prefix: str, identifier: str) -> bool:
        """
        Check if a key exists in cache
        """
        key = self._make_key(prefix, identifier)
        
        try:
            if self.redis_client:
                return bool(self.redis_client.exists(key))
            else:
                if key in self._memory_cache:
                    entry = self._memory_cache[key]
                    if datetime.now() < entry["expires_at"]:
                        return True
                    else:
                        del self._memory_cache[key]
                return False
        except Exception as e:
            print(f"Cache exists error: {e}")
            return False
    
    # User Session Caching
    async def cache_user_session(self, user_id: str, session_data: Dict[str, Any], 
                                ttl: int = 7200) -> bool:  # 2 hours
        """Cache user session data"""
        return await self.set("session", user_id, session_data, ttl)
    
    async def get_user_session(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get cached user session"""
        return await self.get("session", user_id)
    
    async def update_user_session(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update specific fields in user session"""
        session = await self.get_user_session(user_id)
        if session:
            session.update(updates)
            return await self.cache_user_session(user_id, session)
        return False
    
    # Conversation History Caching
    async def cache_conversation(self, user_id: str, messages: List[Dict[str, Any]], 
                                ttl: int = 86400) -> bool:  # 24 hours
        """Cache conversation history"""
        return await self.set("conversation", user_id, messages, ttl)
    
    async def get_conversation(self, user_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached conversation history"""
        return await self.get("conversation", user_id)
    
    async def append_to_conversation(self, user_id: str, message: Dict[str, Any]) -> bool:
        """Append message to cached conversation"""
        conversation = await self.get_conversation(user_id) or []
        conversation.append(message)
        
        # Keep only last 100 messages to prevent memory bloat
        if len(conversation) > 100:
            conversation = conversation[-100:]
        
        return await self.cache_conversation(user_id, conversation)
    
    # Contact Caching
    async def cache_contacts(self, user_id: str, contacts: Dict[str, Any], 
                           ttl: int = 86400) -> bool:  # 24 hours
        """Cache user contacts"""
        return await self.set("contacts", user_id, contacts, ttl)
    
    async def get_contacts(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get cached contacts"""
        return await self.get("contacts", user_id)
    
    async def add_contact(self, user_id: str, email: str, contact_data: Dict[str, Any]) -> bool:
        """Add contact to cache"""
        contacts = await self.get_contacts(user_id) or {"by_email": {}, "by_name": {}}
        
        contacts["by_email"][email] = contact_data
        name = contact_data.get("name", "").lower()
        if name:
            if name not in contacts["by_name"]:
                contacts["by_name"][name] = []
            if email not in contacts["by_name"][name]:
                contacts["by_name"][name].append(email)
        
        return await self.cache_contacts(user_id, contacts)
    
    # Smart Memory Caching
    async def cache_memory_search(self, user_id: str, query: str, 
                                 results: List[Any], ttl: int = 1800) -> bool:  # 30 minutes
        """Cache semantic search results"""
        query_hash = hashlib.md5(query.encode()).hexdigest()
        cache_key = f"{user_id}_{query_hash}"
        return await self.set("memory", cache_key, results, ttl)
    
    async def get_cached_memory_search(self, user_id: str, query: str) -> Optional[List[Any]]:
        """Get cached semantic search results"""
        query_hash = hashlib.md5(query.encode()).hexdigest()
        cache_key = f"{user_id}_{query_hash}"
        return await self.get("memory", cache_key)
    
    # Opportunities Caching
    async def cache_opportunities(self, user_id: str, opportunities: List[Dict[str, Any]], 
                                ttl: int = 3600) -> bool:  # 1 hour
        """Cache user opportunities"""
        return await self.set("opportunities", user_id, opportunities, ttl)
    
    async def get_opportunities(self, user_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached opportunities"""
        return await self.get("opportunities", user_id)
    
    # Nudges Caching
    async def cache_nudges(self, user_id: str, nudges: List[Dict[str, Any]], 
                          ttl: int = 7200) -> bool:  # 2 hours
        """Cache user nudges"""
        return await self.set("nudges", user_id, nudges, ttl)
    
    async def get_nudges(self, user_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached nudges"""
        return await self.get("nudges", user_id)
    
    # User Statistics Caching
    async def cache_user_stats(self, user_id: str, stats: Dict[str, Any], 
                             ttl: int = 3600) -> bool:  # 1 hour
        """Cache user statistics"""
        return await self.set("user_stats", user_id, stats, ttl)
    
    async def get_user_stats(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get cached user statistics"""
        return await self.get("user_stats", user_id)
    
    async def increment_stat(self, user_id: str, stat_name: str, increment: int = 1) -> int:
        """Increment a user statistic"""
        if self.redis_client:
            key = self._make_key("user_stats", f"{user_id}:{stat_name}")
            return self.redis_client.incr(key, increment)
        else:
            # Fallback for memory cache
            stats = await self.get_user_stats(user_id) or {}
            stats[stat_name] = stats.get(stat_name, 0) + increment
            await self.cache_user_stats(user_id, stats)
            return stats[stat_name]
    
    # Bulk Operations
    async def cache_multiple(self, items: List[Tuple[str, str, Any, Optional[int]]]) -> int:
        """
        Cache multiple items at once
        items: List of (prefix, identifier, value, ttl) tuples
        Returns: Number of successfully cached items
        """
        success_count = 0
        for prefix, identifier, value, ttl in items:
            if await self.set(prefix, identifier, value, ttl):
                success_count += 1
        return success_count
    
    async def get_multiple(self, keys: List[Tuple[str, str]]) -> Dict[str, Any]:
        """
        Get multiple items at once
        keys: List of (prefix, identifier) tuples
        Returns: Dict of {full_key: value}
        """
        results = {}
        for prefix, identifier in keys:
            value = await self.get(prefix, identifier)
            if value is not None:
                full_key = self._make_key(prefix, identifier)
                results[full_key] = value
        return results
    
    # Cache Management
    async def clear_user_cache(self, user_id: str) -> int:
        """Clear all cached data for a user"""
        cleared_count = 0
        prefixes_to_clear = ["session", "conversation", "contacts", "memory", 
                           "opportunities", "nudges", "user_stats"]
        
        for prefix in prefixes_to_clear:
            if await self.delete(prefix, user_id):
                cleared_count += 1
        
        return cleared_count
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if self.redis_client:
            try:
                info = self.redis_client.info()
                return {
                    "connected_clients": info.get("connected_clients", 0),
                    "used_memory": info.get("used_memory_human", "0B"),
                    "total_commands_processed": info.get("total_commands_processed", 0),
                    "keyspace_hits": info.get("keyspace_hits", 0),
                    "keyspace_misses": info.get("keyspace_misses", 0),
                    "hit_rate": info.get("keyspace_hits", 0) / max(1, info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0))
                }
            except Exception as e:
                return {"error": str(e)}
        else:
            return {
                "cache_type": "memory",
                "total_keys": len(self._memory_cache),
                "memory_usage": "N/A"
            }

# Global cache instance
cache_service = CacheService()
