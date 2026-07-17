"""Task 4-1 Step 3 -- node <-> project-state-machine mapping sanity checks."""

from __future__ import annotations

from app.pipeline.state import NodeName
from app.pipeline.status_map import (
    NODE_COMPLETE_STATUS,
    NODE_ENTRY_STATUS,
    NODE_ORDER,
    next_node,
)
from app.services.state_machine_edges import is_valid_edge


def test_node_order_matches_all_six_nodes():
    assert set(NODE_ORDER) == set(NodeName)
    assert len(NODE_ORDER) == 6


def test_next_node_walks_sequence_and_ends_at_none():
    assert next_node(NodeName.RESEARCH) == NodeName.RANKING
    assert next_node(NodeName.RANKING) == NodeName.WRITE
    assert next_node(NodeName.WRITE) == NodeName.STORYBOARD
    assert next_node(NodeName.STORYBOARD) == NodeName.PRODUCE
    assert next_node(NodeName.PRODUCE) == NodeName.RENDER
    assert next_node(NodeName.RENDER) is None


def test_research_entry_is_valid_edge_from_draft():
    assert is_valid_edge("DRAFT", NODE_ENTRY_STATUS[NodeName.RESEARCH])


def test_research_complete_is_valid_edge_from_researching():
    assert is_valid_edge("RESEARCHING", NODE_COMPLETE_STATUS[NodeName.RESEARCH])


def test_every_non_none_entry_status_is_a_reachable_edge():
    """Every configured entry transition must be a real edge from *some*
    state this node can plausibly be entered from -- catches typos that
    would make the state machine reject the transition at runtime."""
    reachable_from = {
        NodeName.RESEARCH: "DRAFT",
        NodeName.PRODUCE: "APPROVED",
        NodeName.RENDER: "PRODUCING",
    }
    for node, from_status in reachable_from.items():
        to_status = NODE_ENTRY_STATUS[node]
        assert to_status is not None
        assert is_valid_edge(from_status, to_status), (node, from_status, to_status)
