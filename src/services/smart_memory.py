"""
Smart Memory System - ChromaDB + Semantic Search + Relationship Graphs
Advanced memory system for Native IQ with vector embeddings and graph relationships
"""

import os
import json
import hashlib
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from uuid import uuid4

import chromadb
from chromadb.config import Settings
import networkx as nx
import numpy as np
from sentence_transformers import SentenceTransformer
import boto3
import redis
from dotenv import load_dotenv

load_dotenv()

@dataclass
class MemoryNode:
    """Represents a memory node with embeddings and metadata"""
    id: str
    user_id: str
    content: str
    memory_type: str  # "conversation", "contact", "meeting", "email", "insight", "opportunity"
    timestamp: str
    metadata: Dict[str, Any]
    embedding_id: Optional[str] = None
    relationships: List[str] = None  # Connected node IDs

@dataclass
class Relationship:
    """Represents a relationship between memory nodes"""
    source_id: str
    target_id: str
    relationship_type: str  # "mentions", "follows_up", "collaborates_with", "scheduled_with"
    strength: float  # 0.0 to 1.0
    metadata: Dict[str, Any]
    created_at: str

class SmartMemorySystem:
    """
    Advanced memory system combining ChromaDB vector search with NetworkX graphs
    """
    
    def __init__(self, data_dir: Path = None, model_name: str = "all-MiniLM-L6-v2"):
        self.data_dir = data_dir or Path(__file__).resolve().parents[2] / "data" / "memory"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB for semantic search
        self.chroma_client = chromadb.PersistentClient(
            path=str(self.data_dir / "chromadb"),
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Collections for different memory types
        self.collections = {}
        self._init_collections()
        
        # Sentence transformer for embeddings
        self.embedding_model = SentenceTransformer(model_name)
        
        # NetworkX graph for relationships
        self.relationship_graph = nx.MultiDiGraph()
        self._load_graph()
        
        # In-memory cache for fast access
        self.memory_cache: Dict[str, Dict[str, MemoryNode]] = {}  # user_id -> {node_id: node}
        self.relationship_cache: Dict[str, List[Relationship]] = {}  # user_id -> relationships
        
        # Initialize Redis and DynamoDB for session persistence
        self.redis_client = None
        self.dynamodb = None
        self._init_persistence()
        
        # Load existing memories
        self._load_memories()
    
    def _init_collections(self):
        """Initialize ChromaDB collections for different memory types"""
        memory_types = ["conversation", "contact", "meeting", "email", "insight", "opportunity"]
        
        for memory_type in memory_types:
            try:
                collection = self.chroma_client.get_collection(f"memory_{memory_type}")
            except:
                collection = self.chroma_client.create_collection(
                    name=f"memory_{memory_type}",
                    metadata={"description": f"Memory collection for {memory_type} data"}
                )
            self.collections[memory_type] = collection
    
    def _init_persistence(self):
        """Initialize Redis and DynamoDB for session persistence"""
        try:
            # Redis for fast caching
            self.redis_client = redis.Redis(
                host=os.getenv('REDIS_HOST', 'localhost'),
                port=int(os.getenv('REDIS_PORT', 6379)),
                password=os.getenv('REDIS_PASSWORD') if os.getenv('REDIS_PASSWORD') != 'your_redis_password' else None,
                db=int(os.getenv('REDIS_DB', 0)),
                decode_responses=True
            )
            
            # DynamoDB for persistent storage
            self.dynamodb = boto3.resource(
                'dynamodb',
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                region_name=os.getenv('AWS_REGION', 'us-east-1')
            )
            self.table = self.dynamodb.Table(os.getenv('DYNAMODB_TABLE_NAME', 'native_iq_sessions'))
            
        except Exception as e:
            print(f"Warning: Failed to initialize persistence layer: {e}")
    
    def _load_graph(self):
        """Load relationship graph from file"""
        graph_file = self.data_dir / "relationship_graph.json"
        if graph_file.exists():
            try:
                with open(graph_file, 'r') as f:
                    graph_data = json.load(f)
                    self.relationship_graph = nx.node_link_graph(graph_data, directed=True, multigraph=True)
            except Exception as e:
                print(f"Error loading graph: {e}")
                self.relationship_graph = nx.MultiDiGraph()
    
    def _save_graph(self):
        """Save relationship graph to file"""
        try:
            graph_file = self.data_dir / "relationship_graph.json"
            graph_data = nx.node_link_data(self.relationship_graph)
            with open(graph_file, 'w') as f:
                json.dump(graph_data, f, indent=2)
        except Exception as e:
            print(f"Error saving graph: {e}")
    
    def _load_memories(self):
        """Load memories into cache"""
        memories_file = self.data_dir / "memory_nodes.json"
        if memories_file.exists():
            try:
                with open(memories_file, 'r') as f:
                    data = json.load(f)
                    for user_id, nodes in data.items():
                        self.memory_cache[user_id] = {
                            node_id: MemoryNode(**node_data)
                            for node_id, node_data in nodes.items()
                        }
            except Exception as e:
                print(f"Error loading memories: {e}")
    
    def _save_memories(self):
        """Save memories from cache"""
        try:
            memories_file = self.data_dir / "memory_nodes.json"
            data = {
                user_id: {
                    node_id: asdict(node)
                    for node_id, node in nodes.items()
                }
                for user_id, nodes in self.memory_cache.items()
            }
            with open(memories_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving memories: {e}")
    
    def add_memory(self, user_id: str, content: str, memory_type: str, 
                   metadata: Dict[str, Any] = None) -> MemoryNode:
        """
        Add a new memory with semantic embedding and graph node
        """
        node_id = str(uuid4())
        embedding_id = f"{user_id}_{node_id}"
        
        memory_node = MemoryNode(
            id=node_id,
            user_id=user_id,
            content=content,
            memory_type=memory_type,
            timestamp=datetime.now().isoformat(),
            metadata=metadata or {},
            embedding_id=embedding_id,
            relationships=[]
        )
        
        # Add to cache
        if user_id not in self.memory_cache:
            self.memory_cache[user_id] = {}
        self.memory_cache[user_id][node_id] = memory_node
        
        # Generate embedding and store in ChromaDB
        embedding = self.embedding_model.encode(content).tolist()
        
        collection = self.collections.get(memory_type, self.collections["conversation"])
        collection.add (
            embeddings=[embedding],
            documents=[content],
            metadatas=[{
                "user_id": user_id,
                "node_id": node_id,
                "memory_type": memory_type,
                "timestamp": memory_node.timestamp,
                "metadata": metadata or {}
            }],
            ids=[embedding_id]
        )
        
        # Add to relationship graph
        self.relationship_graph.add_node(
            node_id,
            user_id=user_id,
            memory_type=memory_type,
            content=content[:100],  # Truncated for graph storage
            timestamp=memory_node.timestamp
        )
        
        # Auto-detect relationships with existing memories
        self._detect_relationships(memory_node)
        
        # Save changes
        self._save_memories()
        self._save_graph()
        
        return memory_node
    
    def _detect_relationships(self, new_node: MemoryNode):
        """
        Automatically detect relationships between new memory and existing ones
        """
        user_memories = self.memory_cache.get(new_node.user_id, {})
        
        for existing_id, existing_node in user_memories.items():
            if existing_id == new_node.id:
                continue
            
            # Detect different types of relationships
            relationships = []
            
            # Contact mentions
            if new_node.memory_type in ["conversation", "meeting", "email"]:
                if existing_node.memory_type == "contact":
                    contact_name = existing_node.metadata.get("name", "")
                    if contact_name.lower() in new_node.content.lower():
                        relationships.append(("mentions", 0.8))
            
            # Meeting follow-ups
            if (new_node.memory_type == "email" and 
                existing_node.memory_type == "meeting"):
                time_diff = self._time_difference(new_node.timestamp, existing_node.timestamp)
                if 0 < time_diff < 24:  # Email within 24 hours after meeting
                    relationships.append(("follows_up", 0.9))
            
            # Conversation continuity
            if (new_node.memory_type == "conversation" and 
                existing_node.memory_type == "conversation"):
                time_diff = self._time_difference(new_node.timestamp, existing_node.timestamp)
                if 0 < time_diff < 2:  # Within 2 hours
                    relationships.append(("continues", 0.7))
            
            # Semantic similarity
            similarity = self._calculate_semantic_similarity(new_node.content, existing_node.content)
            if similarity > 0.7:
                relationships.append(("similar_to", similarity))
            
            # Add relationships to graph
            for rel_type, strength in relationships:
                self.add_relationship(
                    new_node.id, existing_id, rel_type, strength,
                    {"auto_detected": True, "confidence": strength}
                )
    
    def add_relationship(self, source_id: str, target_id: str, relationship_type: str,
                        strength: float, metadata: Dict[str, Any] = None):
        """
        Add a relationship between two memory nodes
        """
        relationship = Relationship(
            source_id=source_id,
            target_id=target_id,
            relationship_type=relationship_type,
            strength=strength,
            metadata=metadata or {},
            created_at=datetime.now().isoformat()
        )
        
        # Add to graph
        self.relationship_graph.add_edge(
            source_id, target_id,
            relationship_type=relationship_type,
            strength=strength,
            metadata=metadata or {},
            created_at=relationship.created_at
        )
        
        # Update node relationships
        source_node = self._find_node_by_id(source_id)
        if source_node and target_id not in source_node.relationships:
            source_node.relationships.append(target_id)
        
        self._save_graph()
        return relationship
    
    def semantic_search(self, user_id: str, query: str, memory_types: List[str] = None,
                       limit: int = 10, similarity_threshold: float = 0.5) -> List[Tuple[MemoryNode, float]]:
        """
        Perform semantic search across user's memories
        """
        results = []
        search_types = memory_types or list(self.collections.keys())
        
        # Generate query embedding
        query_embedding = self.embedding_model.encode(query).tolist()
        
        for memory_type in search_types:
            collection = self.collections[memory_type]
            
            # Search in ChromaDB
            search_results = collection.query(
                query_embeddings=[query_embedding],
                where={"user_id": user_id},
                n_results=limit
            )
            
            # Process results
            for i, (doc, distance, metadata) in enumerate(zip(
                search_results["documents"][0],
                search_results["distances"][0],
                search_results["metadatas"][0]
            )):
                similarity = 1 - distance  # Convert distance to similarity
                if similarity >= similarity_threshold:
                    node_id = metadata["node_id"]
                    memory_node = self.memory_cache.get(user_id, {}).get(node_id)
                    if memory_node:
                        results.append((memory_node, similarity))
        
        # Sort by similarity and return top results
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]
    
    def get_related_memories(self, node_id: str, max_depth: int = 2,
                           relationship_types: List[str] = None) -> List[MemoryNode]:
        """
        Get memories related to a specific node using graph traversal
        """
        if not self.relationship_graph.has_node(node_id):
            return []
        
        related_nodes = []
        visited = set()
        
        def traverse(current_id: str, depth: int):
            if depth > max_depth or current_id in visited:
                return
            
            visited.add(current_id)
            
            # Get neighbors
            for neighbor in self.relationship_graph.neighbors(current_id):
                edge_data = self.relationship_graph.get_edge_data(current_id, neighbor)
                
                # Filter by relationship type if specified
                if relationship_types:
                    valid_edge = any(
                        data.get("relationship_type") in relationship_types
                        for data in edge_data.values()
                    )
                    if not valid_edge:
                        continue
                
                # Find the memory node
                memory_node = self._find_node_by_id(neighbor)
                if memory_node and memory_node not in related_nodes:
                    related_nodes.append(memory_node)
                
                # Recursive traversal
                traverse(neighbor, depth + 1)
        
        traverse(node_id, 0)
        return related_nodes
    
    def get_user_memory_graph(self, user_id: str) -> Dict[str, Any]:
        """
        Get user's memory graph for visualization
        """
        user_nodes = [
            node for node, data in self.relationship_graph.nodes(data=True)
            if data.get("user_id") == user_id
        ]
        
        subgraph = self.relationship_graph.subgraph(user_nodes)
        
        # Convert to JSON-serializable format
        nodes = []
        edges = []
        
        for node_id, data in subgraph.nodes(data=True):
            nodes.append({
                "id": node_id,
                "type": data.get("memory_type", "unknown"),
                "content": data.get("content", "")[:50] + "...",
                "timestamp": data.get("timestamp", "")
            })
        
        for source, target, data in subgraph.edges(data=True):
            edges.append({
                "source": source,
                "target": target,
                "type": data.get("relationship_type", "unknown"),
                "strength": data.get("strength", 0.5)
            })
        
        return {"nodes": nodes, "edges": edges}
    
    def analyze_user_patterns(self, user_id: str) -> Dict[str, Any]:
        """
        Analyze user patterns from memory graph
        """
        user_memories = self.memory_cache.get(user_id, {})
        
        if not user_memories:
            return {"patterns": [], "insights": [], "recommendations": []}
        
        # Memory type distribution
        type_counts = {}
        for memory in user_memories.values():
            type_counts[memory.memory_type] = type_counts.get(memory.memory_type, 0) + 1
        
        # Relationship analysis
        user_graph = self.relationship_graph.subgraph([
            node for node, data in self.relationship_graph.nodes(data=True)
            if data.get("user_id") == user_id
        ])
        
        # Find central nodes (most connected)
        centrality = nx.degree_centrality(user_graph)
        top_central = sorted(centrality.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Communication patterns
        meeting_nodes = [m for m in user_memories.values() if m.memory_type == "meeting"]
        email_nodes = [m for m in user_memories.values() if m.memory_type == "email"]
        
        patterns = []
        insights = []
        recommendations = []
        
        # Pattern detection
        if len(meeting_nodes) > len(email_nodes) * 2:
            patterns.append("meeting_heavy")
            insights.append("User prefers meetings over email communication")
            recommendations.append("Consider scheduling follow-up emails after meetings")
        
        if len(top_central) > 0:
            central_node = self._find_node_by_id(top_central[0][0])
            if central_node:
                insights.append(f"Most connected memory: {central_node.content[:50]}...")
        
        return {
            "patterns": patterns,
            "insights": insights,
            "recommendations": recommendations,
            "memory_distribution": type_counts,
            "total_memories": len(user_memories),
            "total_relationships": user_graph.number_of_edges()
        }
    
    def _find_node_by_id(self, node_id: str) -> Optional[MemoryNode]:
        """Find memory node by ID across all users"""
        for user_memories in self.memory_cache.values():
            if node_id in user_memories:
                return user_memories[node_id]
        return None
    
    def _time_difference(self, time1: str, time2: str) -> float:
        """Calculate time difference in hours"""
        try:
            dt1 = datetime.fromisoformat(time1)
            dt2 = datetime.fromisoformat(time2)
            return abs((dt1 - dt2).total_seconds() / 3600)
        except:
            return float('inf')
    
    def _calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity between two texts"""
        try:
            embeddings = self.embedding_model.encode([text1, text2])
            similarity = np.dot(embeddings[0], embeddings[1]) / (
                np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
            )
            return float(similarity)
        except:
            return 0.0
    
    def clear_user_memories(self, user_id: str):
        """Clear all memories for a user"""
        # Remove from cache
        if user_id in self.memory_cache:
            del self.memory_cache[user_id]
        
        # Remove from ChromaDB
        for collection in self.collections.values():
            try:
                collection.delete(where={"user_id": user_id})
            except:
                pass
        
        # Remove from graph
        user_nodes = [
            node for node, data in self.relationship_graph.nodes(data=True)
            if data.get("user_id") == user_id
        ]
        self.relationship_graph.remove_nodes_from(user_nodes)
        
        self._save_memories()
        self._save_graph()
    
    async def store_session_context(self, user_id: str, session_data: Dict[str, Any], ttl: int = 3600):
        """Store session context with Redis caching and DynamoDB persistence"""
        if not self.redis_client or not self.dynamodb:
            return False
            
        try:
            session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Cache in Redis for fast access
            redis_key = f"native_iq:sessions:{user_id}"
            await asyncio.to_thread(
                self.redis_client.setex,
                redis_key,
                ttl,
                json.dumps(session_data)
            )
            
            # Persist in DynamoDB
            await asyncio.to_thread(
                self.table.put_item,
                Item={
                    'user_id': user_id,
                    'session_id': session_id,
                    'session_data': session_data,
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat(),
                    'ttl': int((datetime.now() + timedelta(days=30)).timestamp())
                }
            )
            
            return True
            
        except Exception as e:
            print(f"Failed to store session context: {e}")
            return False
    
    async def get_session_context(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve session context from Redis cache or DynamoDB"""
        if not self.redis_client or not self.dynamodb:
            return None
            
        try:
            # Try Redis first (fast)
            redis_key = f"native_iq:sessions:{user_id}"
            cached_data = await asyncio.to_thread(self.redis_client.get, redis_key)
            
            if cached_data:
                return json.loads(cached_data)
            
            # Fallback to DynamoDB
            response = await asyncio.to_thread(
                self.table.query,
                KeyConditionExpression='user_id = :uid',
                ExpressionAttributeValues={':uid': user_id},
                ScanIndexForward=False,  # Latest first
                Limit=1
            )
            
            if response['Items']:
                session_data = response['Items'][0]['session_data']
                
                # Cache back to Redis
                await asyncio.to_thread(
                    self.redis_client.setex,
                    redis_key,
                    3600,
                    json.dumps(session_data)
                )
                
                return session_data
            
            return None
            
        except Exception as e:
            print(f"Failed to get session context: {e}")
            return None

# Global instance
smart_memory = SmartMemorySystem()
