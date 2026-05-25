"""
Conditional edge functions for the LangGraph workflow.

Each function receives the current state and returns the name of
the next node to execute.  Return values must match node names
registered in graph_builder.py.
"""
from app.graph.state import GraphState


def route_after_routing(state: GraphState) -> str:
    """
    After routing_node: decide whether to retrieve or go straight to generation.
    """
    if state.get("needs_retrieval", True):
        return "retrieval"
    return "generation"


def route_after_generation(state: GraphState) -> str:
    """
    After generation_node: always persist, regardless of errors.
    """
    return "persistence"


def route_after_persistence(state: GraphState) -> str:
    """
    After persistence_node: end the graph.
    """
    return "end"
