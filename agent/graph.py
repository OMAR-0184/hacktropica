"""
Graph assembly — wires all nodes into a LangGraph StateGraph.

    root → tutor → curator → merge → evaluator → router
    router →(conditional)→ next | bridge | END
    next → tutor   (progression loop)
    bridge → tutor (remediation loop)
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from agent.nodes.bridge import bridge_node_generator
from agent.nodes.curator import curator_node
from agent.nodes.evaluator import evaluator_node
from agent.nodes.merge import merge_node
from agent.nodes.quiz import quiz_node
from agent.nodes.next_node import next_node_generator
from agent.nodes.root import root_node
from agent.nodes.router import router_node
from agent.nodes.tutor import tutor_node
from agent.state import CognimapState


def build_graph(checkpointer=None) -> StateGraph:
    """Construct and compile the Cognimap learning graph."""
    graph = StateGraph(CognimapState)

    graph.add_node("root", root_node)
    graph.add_node("tutor", tutor_node)
    graph.add_node("curator", curator_node)
    graph.add_node("merge", merge_node)
    graph.add_node("quiz", quiz_node)
    graph.add_node("evaluator", evaluator_node)
    graph.add_node("next", next_node_generator)
    graph.add_node("bridge", bridge_node_generator)

    graph.set_entry_point("root")
    graph.add_edge("root", "tutor")
    graph.add_edge("tutor", "curator")
    graph.add_edge("curator", "merge")
    graph.add_edge("merge", "quiz")
    graph.add_edge("quiz", "evaluator")

    graph.add_conditional_edges(
        "evaluator",
        router_node,
        {
            "next": "next",
            "bridge": "bridge",
            "__end__": END,
        },
    )

    graph.add_edge("next", "tutor")
    graph.add_edge("bridge", "tutor")

    return graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["evaluator", "next", "bridge"],
    )
