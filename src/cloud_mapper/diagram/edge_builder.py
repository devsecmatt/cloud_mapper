"""Builds diagram edges from resource relationships."""

from __future__ import annotations

from cloud_mapper.discovery.models import ResourceGraph

# Edge styles by relationship type
EDGE_STYLES = {
    "routes_to": {"style": "solid", "color": "#333333"},
    "triggers": {"style": "dashed", "color": "#FF6600"},
    "contains": {"style": "dotted", "color": "#999999"},
    "attached_to": {"style": "dashed", "color": "#666666"},
}


def build_edges(graph: ResourceGraph, node_refs: dict) -> list[tuple]:
    """Build a list of (source_node, target_node, edge_kwargs) tuples.

    Args:
        graph: The resource graph with relationships.
        node_refs: Dict mapping resource IDs to diagram node instances.

    Returns:
        List of (source_node, target_node, edge_kwargs) for rendering.
    """
    edges = []

    for rel in graph.relationships:
        # Skip containment relationships (handled by clusters)
        if rel.relation_type == "contains":
            continue

        source = node_refs.get(rel.source_id)
        target = node_refs.get(rel.target_id)

        if source is None or target is None:
            continue

        style = EDGE_STYLES.get(rel.relation_type, EDGE_STYLES["routes_to"])

        edges.append((source, target, style))

    return edges
