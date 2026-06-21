"""Hyper-dense memory primitives: SQ8 vectors, temporal metadata, compaction."""

from __future__ import annotations

import hashlib
import math
import re
import time
from dataclasses import dataclass, field
from typing import Iterable, Literal, Optional, Sequence

import numpy as np

from .utils import estimate_tokens

DistanceMetric = Literal["cosine", "euclidean"]

_TOKEN_RE = re.compile(r"[A-Za-z0-9_./:-]+")
_MAX_TOKEN_WEIGHT_LENGTH = 24
_STATE_PATTERNS = (
    re.compile(r"\b(?:file|path|module)\s*[:=]\s*([A-Za-z0-9_./\\-]+)", re.IGNORECASE),
    re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*(?:=|:=|->|became|changed to|updated to)", re.IGNORECASE),
    re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+)\b"),
)


@dataclass(frozen=True)
class HyperDenseMemoryConfig:
    """Configuration for ContextForge's local hyper-dense memory engine."""

    dimensions: int = 384
    semantic_top_k: int = 20
    search_multiplier: int = 4
    token_ceiling: int = 4096
    foundation_states: int = 1
    recent_states: int = 3
    distance_metric: DistanceMetric = "cosine"
    enable_state_deduplication: bool = True

    def __post_init__(self) -> None:
        if self.dimensions <= 0:
            raise ValueError("dimensions must be positive")
        if self.semantic_top_k <= 0:
            raise ValueError("semantic_top_k must be positive")
        if self.search_multiplier <= 0:
            raise ValueError("search_multiplier must be positive")
        if self.token_ceiling <= 0:
            raise ValueError("token_ceiling must be positive")
        if self.foundation_states < 0 or self.recent_states < 0:
            raise ValueError("foundation_states and recent_states must be non-negative")
        if self.distance_metric not in {"cosine", "euclidean"}:
            raise ValueError("distance_metric must be 'cosine' or 'euclidean'")


@dataclass(frozen=True)
class QuantizationBounds:
    """Per-dimension SQ8 calibration bounds for a batch of embeddings."""

    minimum: np.ndarray
    maximum: np.ndarray

    @property
    def scale(self) -> np.ndarray:
        span = self.maximum - self.minimum
        return np.where(span == 0.0, 1.0, span / 255.0).astype(np.float32)


@dataclass(frozen=True)
class TemporalMetadata:
    """Strict chronology metadata attached to every memory object."""

    timestamp: float
    turn_sequence: int
    state_anchors: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class TemporalMemoryRecord:
    """A retrieved memory fragment ready for chrono pass and compaction."""

    key: int | str
    token_estimate: int
    timestamp: float
    turn_sequence: int
    state_anchors: tuple[str, ...] = field(default_factory=tuple)


def text_to_embedding(text: str, dimensions: int) -> np.ndarray:
    """Create a deterministic, local semantic embedding with signed feature hashing."""
    if dimensions <= 0:
        raise ValueError("dimensions must be positive")
    vector = np.zeros(dimensions, dtype=np.float32)
    if not text:
        return vector

    for token in _TOKEN_RE.findall(text.lower()):
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        bucket = int.from_bytes(digest[:4], "little") % dimensions
        sign = 1.0 if digest[4] & 1 else -1.0
        weight = 1.0 + min(len(token), _MAX_TOKEN_WEIGHT_LENGTH) / _MAX_TOKEN_WEIGHT_LENGTH
        vector[bucket] += sign * weight

    norm = float(np.linalg.norm(vector))
    if norm > 0.0 and math.isfinite(norm):
        vector /= norm
    return vector


def calibrate_bounds(embeddings: np.ndarray) -> QuantizationBounds:
    """Calculate per-dimension min/max SQ8 calibration bounds for a batch."""
    matrix = _as_float_matrix(embeddings)
    if matrix.size == 0 or matrix.shape[0] == 0:
        raise ValueError("cannot calibrate an empty embedding batch")
    return QuantizationBounds(
        minimum=np.min(matrix, axis=0).astype(np.float32),
        maximum=np.max(matrix, axis=0).astype(np.float32),
    )


def quantize(embeddings: np.ndarray, bounds: Optional[QuantizationBounds] = None) -> tuple[np.ndarray, QuantizationBounds]:
    """Quantize FP32 embeddings to uint8 with batch SQ8 calibration."""
    matrix = _as_float_matrix(embeddings)
    if matrix.size == 0 or matrix.shape[0] == 0:
        raise ValueError("cannot quantize an empty embedding batch")
    q_bounds = bounds or calibrate_bounds(matrix)
    scale = q_bounds.scale
    safe = np.where(scale == 0.0, 1.0, scale)
    quantized = np.rint((matrix - q_bounds.minimum) / safe)
    return np.clip(quantized, 0, 255).astype(np.uint8), q_bounds


def dequantize(quantized_vectors: np.ndarray, bounds: QuantizationBounds) -> np.ndarray:
    """Restore SQ8 vectors to approximate FP32 values."""
    q_matrix = _as_uint8_matrix(quantized_vectors)
    return (q_matrix.astype(np.float32) * bounds.scale) + bounds.minimum


def quantized_euclidean(query: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """Integer-domain negative squared Euclidean score for uint8 vectors."""
    q = _as_uint8_vector(query).astype(np.int16)
    m = _as_uint8_matrix(matrix).astype(np.int16)
    diff = m - q
    return -np.sum(diff.astype(np.int32) * diff.astype(np.int32), axis=1).astype(np.float32)


def quantized_cosine(query: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """Integer-domain cosine similarity over SQ8 vectors."""
    q = _as_uint8_vector(query).astype(np.int32)
    m = _as_uint8_matrix(matrix).astype(np.int32)
    dot = np.sum(m * q, axis=1).astype(np.float32)
    q_norm = math.sqrt(float(np.sum(q * q)))
    m_norm = np.sqrt(np.sum(m * m, axis=1).astype(np.float32))
    denom = np.maximum(m_norm * max(q_norm, 1e-12), 1e-12)
    return dot / denom


class SQ8VectorIndex:
    """Local uint8 semantic index with deterministic embeddings and vectorized search."""

    def __init__(self, config: Optional[HyperDenseMemoryConfig] = None) -> None:
        self.config = config or HyperDenseMemoryConfig()
        self._keys: list[int | str] = []
        self._matrix: Optional[np.ndarray] = None
        self._bounds: Optional[QuantizationBounds] = None

    @property
    def size(self) -> int:
        return len(self._keys)

    @property
    def byte_size(self) -> int:
        return int(self._matrix.nbytes) if self._matrix is not None else 0

    def clear(self) -> None:
        self._keys.clear()
        self._matrix = None
        self._bounds = None

    def build(self, documents: Sequence[tuple[int | str, str]]) -> None:
        """Build the SQ8 matrix from ``(key, text)`` documents."""
        self.clear()
        if not documents:
            return
        embeddings = np.vstack([
            text_to_embedding(text, self.config.dimensions) for _, text in documents
        ]).astype(np.float32)
        self._matrix, self._bounds = quantize(embeddings)
        self._keys = [key for key, _ in documents]

    def search(self, query: str, top_k: Optional[int] = None) -> list[tuple[int | str, float]]:
        """Return top semantic matches using only quantized integer vectors."""
        if not query or self._matrix is None or self._bounds is None or not self._keys:
            return []
        query_embedding = text_to_embedding(query, self.config.dimensions).reshape(1, -1)
        query_quantized, _ = quantize(query_embedding, self._bounds)
        metric = self.config.distance_metric
        if metric == "euclidean":
            scores = quantized_euclidean(query_quantized[0], self._matrix)
        else:
            scores = quantized_cosine(query_quantized[0], self._matrix)
        limit = max(1, min(top_k or self.config.semantic_top_k, len(self._keys)))
        order = np.argsort(scores)[::-1][:limit]
        return [(self._keys[int(i)], float(scores[int(i)])) for i in order]


def normalize_temporal_metadata(
    metadata: Optional[dict],
    *,
    timestamp: Optional[float] = None,
    turn_sequence: Optional[int] = None,
    fallback_sequence: int = 0,
    content: str = "",
    path: str = "",
) -> TemporalMetadata:
    """Coerce user metadata into the strict temporal schema with safe fallbacks."""
    meta = dict(metadata or {})
    ts_raw = timestamp if timestamp is not None else meta.get("timestamp")
    seq_raw = turn_sequence if turn_sequence is not None else meta.get("turn_sequence")

    try:
        ts = float(ts_raw) if ts_raw is not None else time.time()
    except (TypeError, ValueError):
        ts = time.time()
    if not math.isfinite(ts):
        ts = time.time()

    try:
        seq = int(seq_raw) if seq_raw is not None else int(fallback_sequence)
    except (TypeError, ValueError):
        seq = int(fallback_sequence)

    anchors = extract_state_anchors(content=content, path=path, metadata=meta)
    return TemporalMetadata(timestamp=ts, turn_sequence=seq, state_anchors=tuple(sorted(anchors)))


def temporal_sort(records: Iterable[TemporalMemoryRecord]) -> list[TemporalMemoryRecord]:
    """Sort records in strict chronological order."""
    return sorted(records, key=lambda r: (r.turn_sequence, r.timestamp, str(r.key)))


def deduplicate_latest_state(records: Iterable[TemporalMemoryRecord]) -> list[TemporalMemoryRecord]:
    """Drop older fragments that update the same state anchor as a newer fragment."""
    ordered = temporal_sort(records)
    seen: set[str] = set()
    kept: list[TemporalMemoryRecord] = []
    for record in reversed(ordered):
        anchors = set(record.state_anchors)
        if anchors and seen.intersection(anchors):
            continue
        kept.append(record)
        seen.update(anchors)
    return temporal_sort(kept)


def compact_timeline(
    records: Sequence[TemporalMemoryRecord],
    token_ceiling: int,
    *,
    foundation_states: int = 1,
    recent_states: int = 3,
) -> list[TemporalMemoryRecord]:
    """Fill context backwards while preserving oldest foundation and newest states."""
    if token_ceiling <= 0:
        raise ValueError("token_ceiling must be positive")
    ordered = temporal_sort(records)
    if not ordered:
        return []
    total = sum(max(0, r.token_estimate) for r in ordered)
    if total <= token_ceiling:
        return ordered

    selected: dict[int | str, TemporalMemoryRecord] = {}
    used = 0

    def try_add(record: TemporalMemoryRecord, *, force: bool = False) -> None:
        nonlocal used
        if record.key in selected:
            return
        tokens = max(0, record.token_estimate)
        if force or used + tokens <= token_ceiling or not selected:
            selected[record.key] = record
            used += tokens

    for record in ordered[:foundation_states]:
        try_add(record, force=True)
    for record in reversed(ordered[-recent_states:] if recent_states else []):
        try_add(record, force=True)

    for record in reversed(ordered):
        try_add(record)

    return temporal_sort(selected.values())


def extract_state_anchors(content: str = "", path: str = "", metadata: Optional[dict] = None) -> set[str]:
    """Extract state-tracking anchors from metadata, paths, variables, and update text."""
    anchors: set[str] = set()
    if path:
        anchors.add(f"path:{path.lower()}")
    meta = metadata or {}
    for key in ("state_anchor", "state_anchors", "variable", "variable_name", "file_path", "path"):
        value = meta.get(key)
        if value is None:
            continue
        if isinstance(value, (list, tuple, set)):
            values = value
        else:
            values = [value]
        for item in values:
            text = str(item).strip().lower()
            if text:
                anchors.add(f"state:{text}")

    for pattern in _STATE_PATTERNS:
        for match in pattern.findall(content or ""):
            anchor = str(match).strip().lower().rstrip(".,;:)")
            if len(anchor) >= 2:
                anchors.add(f"state:{anchor}")
    return anchors


def _as_float_matrix(values: np.ndarray) -> np.ndarray:
    matrix = np.asarray(values, dtype=np.float32)
    if matrix.ndim == 1:
        matrix = matrix.reshape(1, -1)
    if matrix.ndim != 2:
        raise ValueError("expected a 1D or 2D embedding array")
    return matrix


def _as_uint8_matrix(values: np.ndarray) -> np.ndarray:
    matrix = np.asarray(values, dtype=np.uint8)
    if matrix.ndim == 1:
        matrix = matrix.reshape(1, -1)
    if matrix.ndim != 2:
        raise ValueError("expected a 1D or 2D quantized array")
    return matrix


def _as_uint8_vector(values: np.ndarray) -> np.ndarray:
    vector = np.asarray(values, dtype=np.uint8)
    if vector.ndim == 2 and vector.shape[0] == 1:
        vector = vector[0]
    if vector.ndim != 1:
        raise ValueError("expected a single quantized vector")
    return vector
