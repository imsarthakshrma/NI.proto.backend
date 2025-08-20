"""
Smart Memory API - Endpoints to expose memory data to frontend
Provides access to stored memories, relationships, and insights
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
import sys
from pathlib import Path

# Add project paths
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
for p in [str(SRC), str(ROOT)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from services.smart_memory import smart_memory
from services.cache_service import cache_service

router = APIRouter(prefix="/api/memory", tags=["Smart Memory"])

# Pydantic models for API responses
class MemoryNodeResponse(BaseModel):
    id: str
    user_id: str
    content: str
    memory_type: str
    timestamp: str
    metadata: Dict[str, Any]
    relationships: List[str]

class SearchResult(BaseModel):
    memory: MemoryNodeResponse
    similarity_score: float

class RelationshipResponse(BaseModel):
    source_id: str
    target_id: str
    relationship_type: str
    strength: float
    metadata: Dict[str, Any]
    created_at: str

class MemoryStatsResponse(BaseModel):
    total_memories: int
    memory_types: Dict[str, int]
    total_relationships: int
    recent_memories_count: int
    top_memory_types: List[Dict[str, Any]]

class GraphVisualizationResponse(BaseModel):
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    stats: Dict[str, Any]

@router.get("/stats/{user_id}", response_model=MemoryStatsResponse)
async def get_memory_stats(user_id: str):
    """
    Get comprehensive statistics about user's stored memories
    """
    try:
        # Get user memories from cache first, then smart memory
        cached_stats = await cache_service.get_user_stats(user_id)
        if cached_stats:
            return MemoryStatsResponse(**cached_stats)
        
        # Generate fresh stats
        user_memories = smart_memory.memory_cache.get(user_id, {})
        
        # Memory type distribution
        memory_types = {}
        for memory in user_memories.values():
            memory_types[memory.memory_type] = memory_types.get(memory.memory_type, 0) + 1
        
        # Get relationship count
        user_graph = smart_memory.relationship_graph.subgraph([
            node for node, data in smart_memory.relationship_graph.nodes(data=True)
            if data.get("user_id") == user_id
        ])
        
        # Recent memories (last 7 days)
        from datetime import datetime, timedelta
        recent_cutoff = datetime.now() - timedelta(days=7)
        recent_count = sum(
            1 for memory in user_memories.values()
            if datetime.fromisoformat(memory.timestamp) > recent_cutoff
        )
        
        # Top memory types
        top_types = [
            {"type": mem_type, "count": count}
            for mem_type, count in sorted(memory_types.items(), key=lambda x: x[1], reverse=True)[:5]
        ]
        
        stats = {
            "total_memories": len(user_memories),
            "memory_types": memory_types,
            "total_relationships": user_graph.number_of_edges(),
            "recent_memories_count": recent_count,
            "top_memory_types": top_types
        }
        
        # Cache the stats
        await cache_service.cache_user_stats(user_id, stats, ttl=1800)  # 30 minutes
        
        return MemoryStatsResponse(**stats)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting memory stats: {str(e)}")

@router.get("/list/{user_id}")
async def get_user_memories(
    user_id: str,
    memory_type: Optional[str] = Query(None, description="Filter by memory type"),
    limit: int = Query(50, description="Maximum number of memories to return"),
    offset: int = Query(0, description="Offset for pagination")
):
    """
    Get list of user's stored memories with pagination and filtering
    """
    try:
        user_memories = smart_memory.memory_cache.get(user_id, {})
        
        # Filter by type if specified
        if memory_type:
            filtered_memories = [
                memory for memory in user_memories.values()
                if memory.memory_type == memory_type
            ]
        else:
            filtered_memories = list(user_memories.values())
        
        # Sort by timestamp (most recent first)
        filtered_memories.sort(key=lambda x: x.timestamp, reverse=True)
        
        # Apply pagination
        paginated_memories = filtered_memories[offset:offset + limit]
        
        # Convert to response format
        memories = []
        for memory in paginated_memories:
            memories.append({
                "id": memory.id,
                "user_id": memory.user_id,
                "content": memory.content[:200] + "..." if len(memory.content) > 200 else memory.content,
                "memory_type": memory.memory_type,
                "timestamp": memory.timestamp,
                "metadata": memory.metadata,
                "relationships_count": len(memory.relationships or [])
            })
        
        return {
            "memories": memories,
            "total_count": len(filtered_memories),
            "has_more": offset + limit < len(filtered_memories),
            "memory_types_available": list(set(m.memory_type for m in user_memories.values()))
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting memories: {str(e)}")

@router.get("/search/{user_id}")
async def search_memories(
    user_id: str,
    query: str = Query(..., description="Search query"),
    memory_types: Optional[str] = Query(None, description="Comma-separated memory types to search"),
    limit: int = Query(10, description="Maximum number of results"),
    similarity_threshold: float = Query(0.5, description="Minimum similarity score")
):
    """
    Perform semantic search across user's memories
    """
    try:
        # Check cache first
        cached_results = await cache_service.get_cached_memory_search(user_id, query)
        if cached_results:
            return {"results": cached_results, "cached": True}
        
        # Parse memory types
        search_types = None
        if memory_types:
            search_types = [t.strip() for t in memory_types.split(",")]
        
        # Perform semantic search
        search_results = smart_memory.semantic_search(
            user_id=user_id,
            query=query,
            memory_types=search_types,
            limit=limit,
            similarity_threshold=similarity_threshold
        )
        
        # Format results
        formatted_results = []
        for memory_node, similarity in search_results:
            formatted_results.append({
                "memory": {
                    "id": memory_node.id,
                    "content": memory_node.content,
                    "memory_type": memory_node.memory_type,
                    "timestamp": memory_node.timestamp,
                    "metadata": memory_node.metadata
                },
                "similarity_score": round(similarity, 3)
            })
        
        # Cache results
        await cache_service.cache_memory_search(user_id, query, formatted_results)
        
        return {
            "results": formatted_results,
            "query": query,
            "total_found": len(formatted_results),
            "cached": False
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching memories: {str(e)}")

@router.get("/memory/{memory_id}")
async def get_memory_details(memory_id: str):
    """
    Get detailed information about a specific memory including relationships
    """
    try:
        # Find the memory node
        memory_node = smart_memory._find_node_by_id(memory_id)
        if not memory_node:
            raise HTTPException(status_code=404, detail="Memory not found")
        
        # Get related memories
        related_memories = smart_memory.get_related_memories(memory_id, max_depth=2)
        
        # Format related memories
        related_formatted = []
        for related in related_memories[:10]:  # Limit to 10 related memories
            related_formatted.append({
                "id": related.id,
                "content": related.content[:100] + "..." if len(related.content) > 100 else related.content,
                "memory_type": related.memory_type,
                "timestamp": related.timestamp
            })
        
        return {
            "memory": {
                "id": memory_node.id,
                "user_id": memory_node.user_id,
                "content": memory_node.content,
                "memory_type": memory_node.memory_type,
                "timestamp": memory_node.timestamp,
                "metadata": memory_node.metadata,
                "relationships": memory_node.relationships or []
            },
            "related_memories": related_formatted,
            "relationship_count": len(memory_node.relationships or [])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting memory details: {str(e)}")

@router.get("/graph/{user_id}", response_model=GraphVisualizationResponse)
async def get_memory_graph(user_id: str):
    """
    Get user's memory graph for visualization
    """
    try:
        # Get graph data
        graph_data = smart_memory.get_user_memory_graph(user_id)
        
        # Add statistics
        stats = {
            "total_nodes": len(graph_data["nodes"]),
            "total_edges": len(graph_data["edges"]),
            "node_types": {},
            "relationship_types": {}
        }
        
        # Count node types
        for node in graph_data["nodes"]:
            node_type = node.get("type", "unknown")
            stats["node_types"][node_type] = stats["node_types"].get(node_type, 0) + 1
        
        # Count relationship types
        for edge in graph_data["edges"]:
            rel_type = edge.get("type", "unknown")
            stats["relationship_types"][rel_type] = stats["relationship_types"].get(rel_type, 0) + 1
        
        return GraphVisualizationResponse(
            nodes=graph_data["nodes"],
            edges=graph_data["edges"],
            stats=stats
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting memory graph: {str(e)}")

@router.get("/patterns/{user_id}")
async def get_user_patterns(user_id: str):
    """
    Get analyzed patterns and insights about the user
    """
    try:
        patterns = smart_memory.analyze_user_patterns(user_id)
        return {
            "user_id": user_id,
            "analysis": patterns,
            "generated_at": smart_memory._time_difference("2025-01-01T00:00:00", "2025-01-01T00:00:00")  # Current time
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing user patterns: {str(e)}")

@router.post("/add/{user_id}")
async def add_memory(
    user_id: str,
    content: str,
    memory_type: str,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Add a new memory (useful for testing or manual memory creation)
    """
    try:
        memory_node = smart_memory.add_memory(
            user_id=user_id,
            content=content,
            memory_type=memory_type,
            metadata=metadata or {}
        )
        
        return {
            "success": True,
            "memory_id": memory_node.id,
            "message": "Memory added successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding memory: {str(e)}")

@router.delete("/clear/{user_id}")
async def clear_user_memories(user_id: str):
    """
    Clear all memories for a user (use with caution!)
    """
    try:
        smart_memory.clear_user_memories(user_id)
        await cache_service.clear_user_cache(user_id)
        
        return {
            "success": True,
            "message": f"All memories cleared for user {user_id}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing memories: {str(e)}")

@router.get("/types")
async def get_memory_types():
    """
    Get available memory types in the system
    """
    return {
        "memory_types": [
            {
                "type": "conversation",
                "description": "Chat messages and conversations"
            },
            {
                "type": "contact",
                "description": "Contact information and relationships"
            },
            {
                "type": "meeting",
                "description": "Scheduled meetings and events"
            },
            {
                "type": "email",
                "description": "Email communications"
            },
            {
                "type": "insight",
                "description": "Learned insights about user patterns"
            },
            {
                "type": "opportunity",
                "description": "Identified opportunities and suggestions"
            }
        ]
    }
