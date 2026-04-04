"""
CLI entry point for Cognimap.

Usage:
    python -m cognimap "Machine Learning"
    cognimap "Python basics"

Output is JSON for easy frontend integration.
"""

from __future__ import annotations

import argparse
import json
import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from agent.graph import build_graph

console = Console()


def _print_json(state: dict) -> None:
    """Print the final state as pretty JSON to stdout."""
    output = {
        "topic": state.get("topic", ""),
        "subtopics": state.get("subtopics", []),
        "scores": state.get("scores", {}),
        "mastery": state.get("mastery", {}),
        "graph_nodes": state.get("graph_nodes", {}),
        "history": state.get("history", []),
        "weak_areas": state.get("weak_areas", {}),
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))


def _print_rich(state: dict) -> None:
    """Pretty-print a summary using Rich panels and tables."""
    console.print()
    console.print(Panel(f"[bold cyan]{state.get('topic', '')}[/]", title="📚 Cognimap"))

    table = Table(title="Subtopic Progress", show_lines=True)
    table.add_column("Subtopic", style="bold")
    table.add_column("Status")
    table.add_column("Score")
    table.add_column("Mastered")

    graph_nodes = state.get("graph_nodes", {})
    scores = state.get("scores", {})
    mastery = state.get("mastery", {})

    for st in state.get("subtopics", []):
        meta = graph_nodes.get(st, {})
        score_val = scores.get(st, None)
        score_str = f"{score_val:.0%}" if score_val is not None else "—"
        mastered = "✅" if mastery.get(st, False) else "❌"
        table.add_row(st, meta.get("status", "?"), score_str, mastered)

    console.print(table)
    console.print()


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="cognimap",
        description="Adaptive learning system powered by LangGraph",
    )
    parser.add_argument("topic", help="The topic you want to learn")
    parser.add_argument(
        "--json", dest="json_output", action="store_true",
        help="Output raw JSON (for frontend integration)",
    )
    args = parser.parse_args()

    console.print(f"\n🚀 Starting Cognimap for: [bold]{args.topic}[/]\n")

    graph = build_graph()
    initial_state = {"topic": args.topic}

    try:
        final_state = graph.invoke(initial_state)
    except Exception as exc:
        console.print(f"[bold red]Error:[/] {exc}")
        sys.exit(1)

    if args.json_output:
        _print_json(final_state)
    else:
        _print_rich(final_state)
        sys.stderr.write(json.dumps({
            "topic": final_state.get("topic", ""),
            "subtopics": final_state.get("subtopics", []),
            "scores": final_state.get("scores", {}),
            "mastery": final_state.get("mastery", {}),
        }, indent=2) + "\n")


if __name__ == "__main__":
    main()
