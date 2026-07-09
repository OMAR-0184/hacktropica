from __future__ import annotations

from langgraph.graph import END, StateGraph

from agent.nodes.bridge import bridge_node_generator

from agent.nodes.evaluator import evaluator_node
from agent.nodes.lesson_generator import lesson_generator_node
from agent.nodes.quiz import quiz_node
from agent.nodes.next_node import next_node_generator
from agent.nodes.root import root_node
from agent.nodes.orchestrator import orchestrator_node, route_orchestrator
from agent.state import CognimapState


def build_graph(checkpointer=None) -> StateGraph:
    """Construct and compile the Cognimap learning graph."""
    graph = StateGraph(CognimapState)

    # Core nodes
    graph.add_node("root", root_node)
    graph.add_node("orchestrator", orchestrator_node)

    # Tool nodes
    graph.add_node("lesson_generator", lesson_generator_node)
    graph.add_node("quiz", quiz_node)
    graph.add_node("evaluator", evaluator_node)
    graph.add_node("next", next_node_generator)
    graph.add_node("bridge", bridge_node_generator)

    # Entry point
    graph.set_entry_point("root")
    graph.add_edge("root", "orchestrator")

    # Orchestrator dynamic routing
    graph.add_conditional_edges(
        "orchestrator",
        route_orchestrator,
        {
            "lesson_generator": "lesson_generator",
            "quiz": "quiz",
            "evaluator": "evaluator",
            "bridge": "bridge",
            "next": "next",
            "__end__": END,
        },
    )

    # Parallel nodes handled in lesson_generator
    graph.add_edge("lesson_generator", "quiz")

    # Other tools route back to the orchestrator (or pause at evaluator)
    graph.add_edge("quiz", "evaluator")
    graph.add_edge("evaluator", "orchestrator")
    graph.add_edge("next", "orchestrator")
    graph.add_edge("bridge", "orchestrator")

    return graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["evaluator", "next", "bridge"],
    )
