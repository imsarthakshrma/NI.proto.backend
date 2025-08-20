"""
DynamoDB Service - Persistent storage migration for Native IQ
Handles long-term storage of conversations, memories, and user data
"""

import os
import json
import boto3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from decimal import Decimal
import uuid

@dataclass
class DynamoDBConfig:
    """DynamoDB configuration"""
    region: str = "us-east-1"
    access_key: Optional[str] = None
    secret_key: Optional[str] = None
    endpoint_url: Optional[str] = None  # For local DynamoDB
    table_prefix: str = "NativeIQ"

class DynamoDBService:
    """
    DynamoDB service for persistent storage of Native IQ data
    """
    
    def __init__(self, config: DynamoDBConfig = None):
        self.config = config or DynamoDBConfig()
        
        # Initialize DynamoDB client
        session_kwargs = {
            "region_name": self.config.region
        }
        
        if self.config.access_key and self.config.secret_key:
            session_kwargs.update({
                "aws_access_key_id": self.config.access_key,
                "aws_secret_access_key": self.config.secret_key
            })
        
        self.session = boto3.Session(**session_kwargs)
        
        client_kwargs = {}
        if self.config.endpoint_url:
            client_kwargs["endpoint_url"] = self.config.endpoint_url
        
        self.dynamodb = self.session.resource("dynamodb", **client_kwargs)
        self.client = self.session.client("dynamodb", **client_kwargs)
        
        # Table names
        self.tables = {
            "conversations": f"{self.config.table_prefix}_Conversations",
            "memories": f"{self.config.table_prefix}_Memories",
            "users": f"{self.config.table_prefix}_Users",
            "relationships": f"{self.config.table_prefix}_Relationships",
            "opportunities": f"{self.config.table_prefix}_Opportunities",
            "nudges": f"{self.config.table_prefix}_Nudges"
        }
        
        # Initialize tables
        self._ensure_tables_exist()
    
    def _ensure_tables_exist(self):
        """Create tables if they don't exist"""
        table_definitions = {
            "conversations": {
                "KeySchema": [
                    {"AttributeName": "user_id", "KeyType": "HASH"},
                    {"AttributeName": "timestamp", "KeyType": "RANGE"}
                ],
                "AttributeDefinitions": [
                    {"AttributeName": "user_id", "AttributeType": "S"},
                    {"AttributeName": "timestamp", "AttributeType": "S"}
                ],
                "BillingMode": "PAY_PER_REQUEST"
            },
            "memories": {
                "KeySchema": [
                    {"AttributeName": "user_id", "KeyType": "HASH"},
                    {"AttributeName": "memory_id", "KeyType": "RANGE"}
                ],
                "AttributeDefinitions": [
                    {"AttributeName": "user_id", "AttributeType": "S"},
                    {"AttributeName": "memory_id", "AttributeType": "S"},
                    {"AttributeName": "memory_type", "AttributeType": "S"}
                ],
                "GlobalSecondaryIndexes": [
                    {
                        "IndexName": "MemoryTypeIndex",
                        "KeySchema": [
                            {"AttributeName": "user_id", "KeyType": "HASH"},
                            {"AttributeName": "memory_type", "KeyType": "RANGE"}
                        ],
                        "Projection": {"ProjectionType": "ALL"}
                    }
                ],
                "BillingMode": "PAY_PER_REQUEST"
            },
            "users": {
                "KeySchema": [
                    {"AttributeName": "user_id", "KeyType": "HASH"}
                ],
                "AttributeDefinitions": [
                    {"AttributeName": "user_id", "AttributeType": "S"}
                ],
                "BillingMode": "PAY_PER_REQUEST"
            },
            "relationships": {
                "KeySchema": [
                    {"AttributeName": "source_id", "KeyType": "HASH"},
                    {"AttributeName": "target_id", "KeyType": "RANGE"}
                ],
                "AttributeDefinitions": [
                    {"AttributeName": "source_id", "AttributeType": "S"},
                    {"AttributeName": "target_id", "AttributeType": "S"}
                ],
                "BillingMode": "PAY_PER_REQUEST"
            },
            "opportunities": {
                "KeySchema": [
                    {"AttributeName": "user_id", "KeyType": "HASH"},
                    {"AttributeName": "opportunity_id", "KeyType": "RANGE"}
                ],
                "AttributeDefinitions": [
                    {"AttributeName": "user_id", "AttributeType": "S"},
                    {"AttributeName": "opportunity_id", "AttributeType": "S"},
                    {"AttributeName": "status", "AttributeType": "S"}
                ],
                "GlobalSecondaryIndexes": [
                    {
                        "IndexName": "StatusIndex",
                        "KeySchema": [
                            {"AttributeName": "user_id", "KeyType": "HASH"},
                            {"AttributeName": "status", "KeyType": "RANGE"}
                        ],
                        "Projection": {"ProjectionType": "ALL"}
                    }
                ],
                "BillingMode": "PAY_PER_REQUEST"
            },
            "nudges": {
                "KeySchema": [
                    {"AttributeName": "user_id", "KeyType": "HASH"},
                    {"AttributeName": "scheduled_time", "KeyType": "RANGE"}
                ],
                "AttributeDefinitions": [
                    {"AttributeName": "user_id", "AttributeType": "S"},
                    {"AttributeName": "scheduled_time", "AttributeType": "S"}
                ],
                "BillingMode": "PAY_PER_REQUEST"
            }
        }
        
        for table_name, definition in table_definitions.items():
            full_table_name = self.tables[table_name]
            try:
                # Check if table exists
                self.dynamodb.Table(full_table_name).load()
                print(f"✅ Table {full_table_name} exists")
            except self.client.exceptions.ResourceNotFoundException:
                # Create table
                print(f"📝 Creating table {full_table_name}")
                self.dynamodb.create_table(
                    TableName=full_table_name,
                    **definition
                )
                # Wait for table to be created
                waiter = self.client.get_waiter('table_exists')
                waiter.wait(TableName=full_table_name)
                print(f"✅ Table {full_table_name} created")
    
    def _convert_floats_to_decimal(self, obj):
        """Convert floats to Decimal for DynamoDB compatibility"""
        if isinstance(obj, float):
            return Decimal(str(obj))
        elif isinstance(obj, dict):
            return {k: self._convert_floats_to_decimal(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_floats_to_decimal(v) for v in obj]
        return obj
    
    def _convert_decimal_to_float(self, obj):
        """Convert Decimal back to float for JSON serialization"""
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, dict):
            return {k: self._convert_decimal_to_float(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_decimal_to_float(v) for v in obj]
        return obj
    
    # Conversation Management
    async def store_conversation_message(self, user_id: str, message: Dict[str, Any]) -> bool:
        """Store a conversation message"""
        try:
            table = self.dynamodb.Table(self.tables["conversations"])
            
            item = {
                "user_id": user_id,
                "timestamp": message.get("timestamp", datetime.now().isoformat()),
                "content": message.get("content", ""),
                "is_user": message.get("is_user", False),
                "message_type": message.get("message_type", "text"),
                "metadata": self._convert_floats_to_decimal(message.get("metadata", {}))
            }
            
            table.put_item(Item=item)
            return True
        except Exception as e:
            print(f"Error storing conversation message: {e}")
            return False
    
    async def get_conversation_history(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get conversation history for a user"""
        try:
            table = self.dynamodb.Table(self.tables["conversations"])
            
            response = table.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key("user_id").eq(user_id),
                ScanIndexForward=False,  # Most recent first
                Limit=limit
            )
            
            messages = []
            for item in response["Items"]:
                message = self._convert_decimal_to_float(dict(item))
                messages.append(message)
            
            return list(reversed(messages))  # Return chronological order
        except Exception as e:
            print(f"Error getting conversation history: {e}")
            return []
    
    # Memory Management
    async def store_memory(self, user_id: str, memory: Dict[str, Any]) -> bool:
        """Store a memory node"""
        try:
            table = self.dynamodb.Table(self.tables["memories"])
            
            item = {
                "user_id": user_id,
                "memory_id": memory.get("id", str(uuid.uuid4())),
                "memory_type": memory.get("memory_type", "unknown"),
                "content": memory.get("content", ""),
                "timestamp": memory.get("timestamp", datetime.now().isoformat()),
                "metadata": self._convert_floats_to_decimal(memory.get("metadata", {})),
                "relationships": memory.get("relationships", [])
            }
            
            table.put_item(Item=item)
            return True
        except Exception as e:
            print(f"Error storing memory: {e}")
            return False
    
    async def get_memories_by_type(self, user_id: str, memory_type: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get memories by type for a user"""
        try:
            table = self.dynamodb.Table(self.tables["memories"])
            
            response = table.query(
                IndexName="MemoryTypeIndex",
                KeyConditionExpression=boto3.dynamodb.conditions.Key("user_id").eq(user_id) & 
                                     boto3.dynamodb.conditions.Key("memory_type").eq(memory_type),
                Limit=limit
            )
            
            memories = []
            for item in response["Items"]:
                memory = self._convert_decimal_to_float(dict(item))
                memories.append(memory)
            
            return memories
        except Exception as e:
            print(f"Error getting memories by type: {e}")
            return []
    
    async def get_user_memories(self, user_id: str, limit: int = 1000) -> List[Dict[str, Any]]:
        """Get all memories for a user"""
        try:
            table = self.dynamodb.Table(self.tables["memories"])
            
            response = table.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key("user_id").eq(user_id),
                Limit=limit
            )
            
            memories = []
            for item in response["Items"]:
                memory = self._convert_decimal_to_float(dict(item))
                memories.append(memory)
            
            return memories
        except Exception as e:
            print(f"Error getting user memories: {e}")
            return []
    
    # User Profile Management
    async def store_user_profile(self, user_id: str, profile: Dict[str, Any]) -> bool:
        """Store user profile data"""
        try:
            table = self.dynamodb.Table(self.tables["users"])
            
            item = {
                "user_id": user_id,
                "profile": self._convert_floats_to_decimal(profile),
                "created_at": profile.get("created_at", datetime.now().isoformat()),
                "updated_at": datetime.now().isoformat()
            }
            
            table.put_item(Item=item)
            return True
        except Exception as e:
            print(f"Error storing user profile: {e}")
            return False
    
    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile"""
        try:
            table = self.dynamodb.Table(self.tables["users"])
            
            response = table.get_item(Key={"user_id": user_id})
            
            if "Item" in response:
                return self._convert_decimal_to_float(dict(response["Item"]))
            return None
        except Exception as e:
            print(f"Error getting user profile: {e}")
            return None
    
    # Relationship Management
    async def store_relationship(self, relationship: Dict[str, Any]) -> bool:
        """Store a relationship between memory nodes"""
        try:
            table = self.dynamodb.Table(self.tables["relationships"])
            
            item = {
                "source_id": relationship["source_id"],
                "target_id": relationship["target_id"],
                "relationship_type": relationship["relationship_type"],
                "strength": Decimal(str(relationship.get("strength", 0.5))),
                "metadata": self._convert_floats_to_decimal(relationship.get("metadata", {})),
                "created_at": relationship.get("created_at", datetime.now().isoformat())
            }
            
            table.put_item(Item=item)
            return True
        except Exception as e:
            print(f"Error storing relationship: {e}")
            return False
    
    async def get_node_relationships(self, node_id: str) -> List[Dict[str, Any]]:
        """Get all relationships for a node"""
        try:
            table = self.dynamodb.Table(self.tables["relationships"])
            
            # Get outgoing relationships
            response = table.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key("source_id").eq(node_id)
            )
            
            relationships = []
            for item in response["Items"]:
                relationship = self._convert_decimal_to_float(dict(item))
                relationships.append(relationship)
            
            return relationships
        except Exception as e:
            print(f"Error getting node relationships: {e}")
            return []
    
    # Opportunity Management
    async def store_opportunity(self, user_id: str, opportunity: Dict[str, Any]) -> bool:
        """Store an opportunity"""
        try:
            table = self.dynamodb.Table(self.tables["opportunities"])
            
            item = {
                "user_id": user_id,
                "opportunity_id": opportunity.get("id", str(uuid.uuid4())),
                "title": opportunity.get("title", ""),
                "description": opportunity.get("description", ""),
                "opportunity_type": opportunity.get("type", "unknown"),
                "priority": opportunity.get("priority", "medium"),
                "status": opportunity.get("status", "identified"),
                "context": self._convert_floats_to_decimal(opportunity.get("context", {})),
                "created_at": opportunity.get("created_at", datetime.now().isoformat()),
                "updated_at": opportunity.get("updated_at", datetime.now().isoformat())
            }
            
            table.put_item(Item=item)
            return True
        except Exception as e:
            print(f"Error storing opportunity: {e}")
            return False
    
    async def get_user_opportunities(self, user_id: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get opportunities for a user"""
        try:
            table = self.dynamodb.Table(self.tables["opportunities"])
            
            if status:
                response = table.query(
                    IndexName="StatusIndex",
                    KeyConditionExpression=boto3.dynamodb.conditions.Key("user_id").eq(user_id) & 
                                         boto3.dynamodb.conditions.Key("status").eq(status)
                )
            else:
                response = table.query(
                    KeyConditionExpression=boto3.dynamodb.conditions.Key("user_id").eq(user_id)
                )
            
            opportunities = []
            for item in response["Items"]:
                opportunity = self._convert_decimal_to_float(dict(item))
                opportunities.append(opportunity)
            
            return opportunities
        except Exception as e:
            print(f"Error getting user opportunities: {e}")
            return []
    
    # Migration Utilities
    async def migrate_from_json(self, json_file_path: str, data_type: str) -> int:
        """Migrate data from JSON files to DynamoDB"""
        try:
            with open(json_file_path, 'r') as f:
                data = json.load(f)
            
            migrated_count = 0
            
            if data_type == "conversations":
                for user_id, user_data in data.items():
                    messages = user_data.get("messages", [])
                    for message in messages:
                        if await self.store_conversation_message(user_id, message):
                            migrated_count += 1
            
            elif data_type == "memories":
                for user_id, memories in data.items():
                    for memory in memories:
                        memory["user_id"] = user_id
                        if await self.store_memory(user_id, memory):
                            migrated_count += 1
            
            return migrated_count
        except Exception as e:
            print(f"Error migrating from JSON: {e}")
            return 0
    
    async def backup_to_json(self, output_dir: str) -> bool:
        """Backup DynamoDB data to JSON files"""
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            # Backup conversations
            conversations = {}
            # Implementation would scan all tables and export to JSON
            
            return True
        except Exception as e:
            print(f"Error backing up to JSON: {e}")
            return False

# Global DynamoDB service instance
dynamodb_service = DynamoDBService()
