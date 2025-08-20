#!/usr/bin/env python3
"""
Redis Setup Script for Native IQ
Sets up Redis for caching and session management
"""

import redis
import os
from dotenv import load_dotenv
import json
from datetime import datetime

load_dotenv()

def test_redis_connection():
    """Test Redis connection and basic operations"""
    
    redis_host = os.getenv('REDIS_HOST', 'localhost')
    redis_port = int(os.getenv('REDIS_PORT', 6379))
    redis_password = os.getenv('REDIS_PASSWORD', None)
    redis_db = int(os.getenv('REDIS_DB', 0))
    
    try:
        # Create Redis client
        r = redis.Redis(
            host=redis_host,
            port=redis_port,
            password=redis_password if redis_password and redis_password != 'your_redis_password' else None,
            db=redis_db,
            decode_responses=True
        )
        
        print(f"🔄 Testing Redis connection to {redis_host}:{redis_port}")
        
        # Test connection
        r.ping()
        print("✅ Redis connection successful!")
        
        # Test basic operations
        test_key = "native_iq_test"
        test_data = {
            "user_id": "test_user_123",
            "session_data": {
                "contacts": {"john": "john@company.com"},
                "last_activity": datetime.now().isoformat(),
                "message_count": 5
            },
            "timestamp": datetime.now().isoformat()
        }
        
        # Test write
        r.setex(test_key, 300, json.dumps(test_data))  # 5 minute expiry
        print("✅ Test write successful!")
        
        # Test read
        retrieved_data = r.get(test_key)
        if retrieved_data:
            parsed_data = json.loads(retrieved_data)
            print("✅ Test read successful!")
            print(f"Retrieved data: {parsed_data['session_data']}")
        else:
            print("❌ Test read failed - data not found")
            return False
        
        # Test TTL
        ttl = r.ttl(test_key)
        print(f"✅ TTL test successful! Key expires in {ttl} seconds")
        
        # Clean up
        r.delete(test_key)
        print("✅ Test cleanup successful!")
        
        # Test hash operations (for user sessions)
        hash_key = "user_sessions:test_user"
        r.hset(hash_key, mapping={
            "session_id": "sess_123",
            "last_seen": datetime.now().isoformat(),
            "message_count": "10"
        })
        
        session_data = r.hgetall(hash_key)
        if session_data:
            print("✅ Hash operations test successful!")
            print(f"Session data: {session_data}")
        
        r.delete(hash_key)
        
        return True
        
    except redis.ConnectionError:
        print("❌ Redis connection failed!")
        print("Make sure Redis is running:")
        print("  - Windows: Download from https://github.com/microsoftarchive/redis/releases")
        print("  - Docker: docker run -d -p 6379:6379 redis:alpine")
        print("  - WSL: sudo apt install redis-server && sudo service redis-server start")
        return False
        
    except Exception as e:
        print(f"❌ Redis test failed: {e}")
        return False

def setup_redis_for_native_iq():
    """Set up Redis configuration for Native IQ"""
    
    try:
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_port = int(os.getenv('REDIS_PORT', 6379))
        redis_password = os.getenv('REDIS_PASSWORD', None)
        redis_db = int(os.getenv('REDIS_DB', 0))
        
        r = redis.Redis(
            host=redis_host,
            port=redis_port,
            password=redis_password if redis_password and redis_password != 'your_redis_password' else None,
            db=redis_db,
            decode_responses=True
        )
        
        print("🔄 Setting up Redis for Native IQ...")
        
        # Set up key prefixes for organization
        prefixes = {
            "sessions": "native_iq:sessions:",
            "contacts": "native_iq:contacts:",
            "conversations": "native_iq:conversations:",
            "pending_actions": "native_iq:pending:",
            "user_contexts": "native_iq:contexts:"
        }
        
        # Store configuration
        r.hset("native_iq:config", mapping={
            "version": "0.1.0",
            "setup_date": datetime.now().isoformat(),
            "key_prefixes": json.dumps(prefixes)
        })
        
        print("✅ Redis configuration stored!")
        print("Key prefixes configured:")
        for name, prefix in prefixes.items():
            print(f"  - {name}: {prefix}")
        
        # Test session storage pattern
        test_user_id = "demo_user_123"
        session_key = f"{prefixes['sessions']}{test_user_id}"
        
        demo_session = {
            "user_id": test_user_id,
            "contacts": {"alice": "alice@company.com", "bob": "bob@company.com"},
            "last_meeting": {
                "title": "Demo Meeting",
                "time": "2025-08-20T10:00:00+05:30",
                "attendees": ["alice@company.com"]
            },
            "message_count": 15,
            "last_activity": datetime.now().isoformat()
        }
        
        # Store with 1 hour expiry
        r.setex(session_key, 3600, json.dumps(demo_session))
        print(f"✅ Demo session stored: {session_key}")
        
        return True
        
    except Exception as e:
        print(f"❌ Redis setup failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Native IQ Redis Setup")
    print("=" * 40)
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("❌ .env file not found!")
        print("Please create a .env file with your Redis configuration")
        exit(1)
    
    # Test connection
    if test_redis_connection():
        print("\n🔧 Setting up Redis for Native IQ...")
        if setup_redis_for_native_iq():
            print("\n🎉 Redis setup complete!")
            print("\nRedis is ready for:")
            print("• Session caching (fast user context access)")
            print("• Contact storage (quick email resolution)")
            print("• Pending actions (approval workflows)")
            print("• Conversation history (recent message cache)")
            print("\nNext: Set up ChromaDB for vector storage")
        else:
            print("\n❌ Redis setup failed")
    else:
        print("\n❌ Redis connection failed. Please install and start Redis first.")
        print("\nQuick Redis installation:")
        print("• Docker: docker run -d -p 6379:6379 --name redis redis:alpine")
        print("• Windows: Download from GitHub releases")
        print("• WSL/Linux: sudo apt install redis-server")
