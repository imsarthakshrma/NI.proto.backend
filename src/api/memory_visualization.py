"""
Memory Visualization Helper - Generate frontend-ready data structures
Provides formatted data for memory graphs, timelines, and insights visualization
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import json
from collections import defaultdict

class MemoryVisualization:
    """
    Helper class to format smart memory data for frontend visualization
    """
    
    @staticmethod
    def format_memory_timeline(memories: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Format memories into a timeline structure for frontend
        """
        timeline_data = {
            "events": [],
            "date_range": {"start": None, "end": None},
            "memory_types": set(),
            "daily_counts": defaultdict(int)
        }
        
        # Sort memories by timestamp
        sorted_memories = sorted(memories, key=lambda x: x.get("timestamp", ""))
        
        for memory in sorted_memories:
            timestamp = memory.get("timestamp", "")
            if not timestamp:
                continue
                
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                date_str = dt.strftime("%Y-%m-%d")
                
                # Add to timeline
                timeline_data["events"].append({
                    "id": memory.get("id", ""),
                    "date": date_str,
                    "time": dt.strftime("%H:%M"),
                    "title": memory.get("content", "")[:50] + "...",
                    "type": memory.get("memory_type", "unknown"),
                    "content": memory.get("content", ""),
                    "metadata": memory.get("metadata", {})
                })
                
                # Track memory types
                timeline_data["memory_types"].add(memory.get("memory_type", "unknown"))
                
                # Count daily activities
                timeline_data["daily_counts"][date_str] += 1
                
                # Update date range
                if not timeline_data["date_range"]["start"]:
                    timeline_data["date_range"]["start"] = date_str
                timeline_data["date_range"]["end"] = date_str
                
            except Exception:
                continue
        
        # Convert sets to lists for JSON serialization
        timeline_data["memory_types"] = list(timeline_data["memory_types"])
        timeline_data["daily_counts"] = dict(timeline_data["daily_counts"])
        
        return timeline_data
    
    @staticmethod
    def format_relationship_network(nodes: List[Dict], edges: List[Dict]) -> Dict[str, Any]:
        """
        Format memory graph for network visualization (D3.js, vis.js, etc.)
        """
        # Color mapping for different memory types
        type_colors = {
            "conversation": "#4CAF50",
            "contact": "#2196F3", 
            "meeting": "#FF9800",
            "email": "#9C27B0",
            "insight": "#607D8B",
            "opportunity": "#F44336"
        }
        
        # Size mapping based on relationship count
        def get_node_size(node_id: str) -> int:
            connection_count = sum(1 for edge in edges if edge["source"] == node_id or edge["target"] == node_id)
            return max(10, min(50, 10 + connection_count * 3))
        
        formatted_nodes = []
        for node in nodes:
            formatted_nodes.append({
                "id": node["id"],
                "label": node.get("content", "")[:30] + "...",
                "type": node.get("type", "unknown"),
                "color": type_colors.get(node.get("type", "unknown"), "#9E9E9E"),
                "size": get_node_size(node["id"]),
                "timestamp": node.get("timestamp", ""),
                "full_content": node.get("content", "")
            })
        
        formatted_edges = []
        for edge in edges:
            formatted_edges.append({
                "id": f"{edge['source']}-{edge['target']}",
                "source": edge["source"],
                "target": edge["target"],
                "type": edge.get("type", "unknown"),
                "strength": edge.get("strength", 0.5),
                "width": max(1, edge.get("strength", 0.5) * 5),
                "color": "#999999"
            })
        
        return {
            "nodes": formatted_nodes,
            "edges": formatted_edges,
            "legend": [
                {"type": mem_type, "color": color, "label": mem_type.title()}
                for mem_type, color in type_colors.items()
            ]
        }
    
    @staticmethod
    def format_memory_insights(patterns: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format user pattern analysis for dashboard insights
        """
        insights = {
            "summary": {
                "total_patterns": len(patterns.get("patterns", [])),
                "confidence_level": "high" if len(patterns.get("insights", [])) > 3 else "medium",
                "last_updated": datetime.now().isoformat()
            },
            "behavioral_patterns": [],
            "communication_style": {},
            "productivity_insights": [],
            "recommendations": patterns.get("recommendations", [])
        }
        
        # Process insights into categories
        for insight in patterns.get("insights", []):
            if "meeting" in insight.lower():
                insights["behavioral_patterns"].append({
                    "category": "Meeting Preferences",
                    "insight": insight,
                    "icon": "calendar"
                })
            elif "email" in insight.lower() or "communication" in insight.lower():
                insights["communication_style"]["primary_style"] = insight
            else:
                insights["productivity_insights"].append({
                    "insight": insight,
                    "actionable": True
                })
        
        # Memory distribution analysis
        memory_dist = patterns.get("memory_distribution", {})
        if memory_dist:
            total_memories = sum(memory_dist.values())
            insights["activity_breakdown"] = [
                {
                    "type": mem_type,
                    "count": count,
                    "percentage": round((count / total_memories) * 100, 1)
                }
                for mem_type, count in memory_dist.items()
            ]
        
        return insights
    
    @staticmethod
    def format_search_results_with_context(results: List[Dict], query: str) -> Dict[str, Any]:
        """
        Format search results with additional context for better frontend display
        """
        formatted_results = {
            "query": query,
            "total_results": len(results),
            "results_by_type": defaultdict(list),
            "similarity_distribution": {"high": 0, "medium": 0, "low": 0},
            "timeline_matches": []
        }
        
        for result in results:
            memory = result.get("memory", {})
            similarity = result.get("similarity_score", 0)
            
            # Categorize by similarity
            if similarity > 0.8:
                formatted_results["similarity_distribution"]["high"] += 1
            elif similarity > 0.6:
                formatted_results["similarity_distribution"]["medium"] += 1
            else:
                formatted_results["similarity_distribution"]["low"] += 1
            
            # Group by memory type
            memory_type = memory.get("memory_type", "unknown")
            formatted_results["results_by_type"][memory_type].append({
                "id": memory.get("id", ""),
                "content": memory.get("content", ""),
                "timestamp": memory.get("timestamp", ""),
                "similarity": similarity,
                "highlighted_content": MemoryVisualization._highlight_query_in_content(
                    memory.get("content", ""), query
                )
            })
            
            # Add to timeline if has timestamp
            if memory.get("timestamp"):
                try:
                    dt = datetime.fromisoformat(memory["timestamp"].replace('Z', '+00:00'))
                    formatted_results["timeline_matches"].append({
                        "date": dt.strftime("%Y-%m-%d"),
                        "content": memory.get("content", "")[:100] + "...",
                        "type": memory_type,
                        "similarity": similarity
                    })
                except:
                    pass
        
        # Convert defaultdict to regular dict
        formatted_results["results_by_type"] = dict(formatted_results["results_by_type"])
        
        # Sort timeline matches by date
        formatted_results["timeline_matches"].sort(key=lambda x: x["date"], reverse=True)
        
        return formatted_results
    
    @staticmethod
    def _highlight_query_in_content(content: str, query: str) -> str:
        """
        Highlight query terms in content for frontend display
        """
        if not query or not content:
            return content
        
        # Simple highlighting - replace with <mark> tags
        query_terms = query.lower().split()
        highlighted_content = content
        
        for term in query_terms:
            if len(term) > 2:  # Only highlight meaningful terms
                # Case-insensitive replacement
                import re
                pattern = re.compile(re.escape(term), re.IGNORECASE)
                highlighted_content = pattern.sub(f"<mark>{term}</mark>", highlighted_content)
        
        return highlighted_content
    
    @staticmethod
    def format_memory_stats_for_dashboard(stats: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format memory statistics for dashboard widgets
        """
        dashboard_stats = {
            "overview": {
                "total_memories": stats.get("total_memories", 0),
                "total_relationships": stats.get("total_relationships", 0),
                "recent_activity": stats.get("recent_memories_count", 0),
                "growth_trend": "stable"  # Could be calculated from historical data
            },
            "memory_breakdown": [],
            "activity_chart": [],
            "top_connections": []
        }
        
        # Format memory type breakdown for pie chart
        memory_types = stats.get("memory_types", {})
        total = sum(memory_types.values()) if memory_types else 1
        
        for mem_type, count in memory_types.items():
            dashboard_stats["memory_breakdown"].append({
                "type": mem_type.title(),
                "count": count,
                "percentage": round((count / total) * 100, 1),
                "color": MemoryVisualization._get_type_color(mem_type)
            })
        
        # Format top memory types
        top_types = stats.get("top_memory_types", [])
        dashboard_stats["top_connections"] = [
            {
                "name": item.get("type", "").title(),
                "value": item.get("count", 0),
                "trend": "up"  # Could be calculated from historical data
            }
            for item in top_types[:5]
        ]
        
        return dashboard_stats
    
    @staticmethod
    def _get_type_color(memory_type: str) -> str:
        """Get consistent color for memory type"""
        colors = {
            "conversation": "#4CAF50",
            "contact": "#2196F3",
            "meeting": "#FF9800", 
            "email": "#9C27B0",
            "insight": "#607D8B",
            "opportunity": "#F44336"
        }
        return colors.get(memory_type, "#9E9E9E")

# Global instance
memory_viz = MemoryVisualization()
