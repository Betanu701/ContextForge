"""Tests for SQ8 quantization and temporal memory ordering."""

from __future__ import annotations

import numpy as np

from contextforge.hyperdense import (
    HyperDenseMemoryConfig,
    SQ8VectorIndex,
    TemporalMemoryRecord,
    compact_timeline,
    deduplicate_latest_state,
    dequantize,
    quantize,
    quantized_cosine,
)
from contextforge.index import MemoryIndex
from contextforge.loader import ProactiveLoader
from contextforge.tree import KnowledgeTree


def test_sq8_quantize_dequantize_and_cosine():
    embeddings = np.array(
        [[0.0, 0.5, 1.0], [1.0, 0.25, -1.0]],
        dtype=np.float32,
    )
    q, bounds = quantize(embeddings)
    assert q.dtype == np.uint8
    assert q.nbytes == embeddings.shape[0] * embeddings.shape[1]
    restored = dequantize(q, bounds)
    assert restored.shape == embeddings.shape
    scores = quantized_cosine(q[0], q)
    assert scores[0] >= scores[1]


def test_sq8_vector_index_searches_semantically():
    index = SQ8VectorIndex(HyperDenseMemoryConfig(dimensions=64))
    index.build([
        (1, "revenue profit financial quarter"),
        (2, "python class function module"),
    ])
    results = index.search("quarterly revenue", top_k=1)
    assert results[0][0] == 1
    assert index.byte_size == 2 * 64


def test_memory_index_wraps_temporal_metadata():
    index = MemoryIndex(HyperDenseMemoryConfig(dimensions=64))
    index.add_document(
        1,
        "memory/day1",
        "Day 1",
        "memory",
        "status = draft",
        metadata={"timestamp": 10.0, "turn_sequence": 1},
    )
    result = index.search("status draft", top_k=1)[0]
    assert result.timestamp == 10.0
    assert result.turn_sequence == 1
    assert "state:status" in result.state_anchors


def test_temporal_dedup_keeps_latest_state():
    records = [
        TemporalMemoryRecord(1, 10, 1.0, 1, ("state:status",)),
        TemporalMemoryRecord(2, 10, 2.0, 2, ("state:status",)),
        TemporalMemoryRecord(3, 10, 3.0, 3, ("state:other",)),
    ]
    deduped = deduplicate_latest_state(records)
    assert [record.key for record in deduped] == [2, 3]


def test_compact_timeline_preserves_oldest_and_recent_states():
    records = [TemporalMemoryRecord(i, 10, float(i), i, ()) for i in range(6)]
    compacted = compact_timeline(records, token_ceiling=30, foundation_states=1, recent_states=2)
    keys = [record.key for record in compacted]
    assert keys[0] == 0
    assert 4 in keys and 5 in keys
    assert keys == sorted(keys)


def test_loader_chrono_pass_discards_stale_updates():
    tree = KnowledgeTree(":memory:")
    tree.open()
    try:
        tree.add(
            "memory/day1",
            "Day 1",
            "Project Condor status = blocked pending diligence.",
            category="memory",
            metadata={"timestamp": 1.0, "turn_sequence": 1, "state_anchor": "condor_status"},
        )
        tree.add(
            "memory/day2",
            "Day 2",
            "Project Condor status = approved after Jamie review.",
            category="memory",
            metadata={"timestamp": 2.0, "turn_sequence": 2, "state_anchor": "condor_status"},
        )
        idx = MemoryIndex(HyperDenseMemoryConfig(dimensions=64))
        idx.build_from_tree(tree)
        loader = ProactiveLoader(tree, idx, max_context_tokens=1000)
        loaded = loader.load("What is Project Condor status?")
        assert "approved" in loaded.system_prefix
        assert "blocked pending" not in loaded.system_prefix
    finally:
        tree.close()
