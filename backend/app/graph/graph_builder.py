"""
Graph builder — assembles the LangGraph StateGraph.

Workflow:
  START
    → memory        (load history + persona from Supabase)
    → routing       (decide: retrieval needed? summary needed?)
    → [conditional] retrieval OR skip_to_generation
    → generation    (build prompt + call Groq LLM)
    → persistence   (save turn to Supabase, trigger summary if needed)
  END

The compiled graph is cached as a module-level singleton.
"""
import logging

from langgraph.graph import END, StateGraph

from app.graph.edges.conditional_edges import (
    route_after_generation,
    route_after_persistence,
    route_after_routing,
)
from app.graph.nodes.generation_node import generation_node
from app.graph.nodes.memory_node import memory_node
from app.graph.nodes.persistence_node import persistence_node
from app.graph.nodes.retrieval_node import retrieval_node
from app.graph.nodes.routing_node import routing_node
from app.graph.state import GraphState

logger = logging.getLogger(__name__)

_compiled_graph = None


def build_graph():
    """Build and compile the LangGraph StateGraph."""
    g = StateGraph(GraphState)

    # Register nodes
    g.add_node("memory",      memory_node)
    g.add_node("routing",     routing_node)
    g.add_node("retrieval",   retrieval_node)
    g.add_node("generation",  generation_node)
    g.add_node("persistence", persistence_node)

    # Entry point
    g.set_entry_point("memory")

    # Fixed edges
    g.add_edge("memory", "routing")

    # Conditional: routing → retrieval OR generation
    g.add_conditional_edges(
        "routing",
        route_after_routing,
        {"retrieval": "retrieval", "generation": "generation"},
    )

    # retrieval always feeds generation
    g.add_edge("retrieval", "generation")

    # generation → persistence (always)
    g.add_conditional_edges(
        "generation",
        route_after_generation,
        {"persistence": "persistence"},
    )

    # persistence → END
    g.add_conditional_edges(
        "persistence",
        route_after_persistence,
        {"end": END},
    )

    compiled = g.compile()
    logger.info("LangGraph compiled successfully")
    return compiled


def get_graph():
    """Return the cached compiled graph (lazy-init singleton)."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph
