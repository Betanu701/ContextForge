"""Compiled wiki memory for source-backed long-term knowledge."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, Optional

from .tree import KnowledgeNode, KnowledgeTree
from .utils import estimate_tokens, extract_keywords


WIKI_CATEGORY = "wiki"
WIKI_PREFIX = "wiki/"

_DATE_RE = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")
_DAY_RE = re.compile(r"\bday[-_\s]*(\d{1,4})\b", re.IGNORECASE)
_ENTITY_RE = re.compile(r"\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,2}\b")
_SOURCE_REF_RE = re.compile(
    r"\bSource(?:s)?:\s*([^\n]+)|^-\s*(?!wiki/)([\w./-]+/[\w./-]+)\s*$",
    re.MULTILINE,
)
_WIKI_REF_RE = re.compile(r"\bwiki/[\w./-]+")

_ENTITY_STOP_WORDS = {
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
    "January", "February", "March", "April", "May", "June", "July", "August",
    "September", "October", "November", "December", "Today", "Tomorrow", "Yesterday",
    "Morning", "Afternoon", "Evening", "Subject", "From", "To", "Cc", "Bcc",
    "Source", "Date", "Day",
}

_DECISION_WORDS = {
    "approved", "approval", "decided", "decision", "deferred", "rejected",
    "cancelled", "canceled", "rescheduled", "moved", "blocked", "unblocked",
    "confirmed", "declined", "accepted", "changed", "superseded",
}

_NEGATIVE_WORDS = {
    "not", "never", "no longer", "cancelled", "canceled", "declined", "rejected",
    "blocked", "unavailable", "cannot", "can't", "won't", "without",
}

_STATUS_WORDS = {
    "approved": {"approved", "approval", "confirmed", "accepted", "granted"},
    "blocked": {"blocked", "stalled", "waiting", "pending", "cannot", "can't"},
    "cancelled": {"cancelled", "canceled", "called off", "scrapped"},
    "deferred": {"deferred", "delayed", "postponed", "rescheduled", "moved"},
    "rejected": {"rejected", "declined", "denied", "not granted"},
    "superseded": {"changed", "superseded", "replaced", "no longer"},
}

_CONSTRAINT_WORDS = {
    "constraint", "constrained", "gating", "gate", "blocked", "pending", "waiting",
    "dependency", "dependencies", "requires", "required", "prerequisite", "before",
    "until", "unless", "permission", "permissions", "approval", "hold", "holds",
    "must", "cannot", "can't", "without",
}

_APPROVAL_EXCEPTION_WORDS = {
    "approved", "approval", "authorized", "authorization", "granted", "not granted",
    "denied", "declined", "exception", "exceptions", "disclosure", "external",
    "circulate", "circulation", "distribution", "distributed", "send", "sent",
    "share", "shared", "review", "permission", "permissions",
}

_CHANGE_WORDS = {
    "changed", "shifted", "moved", "became", "converted", "transitioned",
    "from", "to", "before", "after", "by", "latest", "prior", "earlier",
    "remained", "still", "no longer", "superseded", "replaced", "follow-through",
}


@dataclass
class WikiIssue:
    """A lint issue detected in compiled wiki memory."""

    severity: str
    path: str
    message: str
    suggestion: str = ""


@dataclass
class WikiCompilationResult:
    """Summary of pages created or updated by a compilation pass."""

    source_path: str
    pages_created: list[str] = field(default_factory=list)
    pages_updated: list[str] = field(default_factory=list)

    @property
    def touched_pages(self) -> list[str]:
        return [*self.pages_created, *self.pages_updated]


class WikiMemory:
    """Maintains a source-backed compiled wiki inside a KnowledgeTree.

    The wiki is a compiled layer, not the source of truth. Generated pages keep
    source paths in plain text so query-time retrieval can pull raw evidence for
    grounding when precision matters.
    """

    def __init__(self, tree: KnowledgeTree) -> None:
        self._tree = tree

    def compile_source_node(self, node: KnowledgeNode) -> WikiCompilationResult:
        """Compile a stored knowledge node into source, entity, concept, and timeline pages."""
        return self.compile_source(
            source_path=node.path,
            title=node.title,
            content=node.content,
            source_category=node.category,
            metadata=node.metadata,
        )

    def compile_source(
        self,
        source_path: str,
        title: str,
        content: str,
        source_category: str = "general",
        metadata: Optional[dict] = None,
    ) -> WikiCompilationResult:
        """Compile one raw source into wiki pages and return touched paths."""
        result = WikiCompilationResult(source_path=source_path)
        source_page = self._upsert_page(
            path=f"wiki/sources/{self._slug(source_path)}",
            title=f"Source Summary: {title}",
            content=self._source_summary(source_path, title, content, source_category, metadata),
            page_type="source",
        )
        self._record_touch(result, source_page)

        related_pages = [source_page]
        for entity in self._extract_entities(content):
            page = self._merge_fact_page(
                path=f"wiki/entities/{self._slug(entity)}",
                title=entity,
                page_type="entity",
                source_path=source_path,
                facts=self._sentences_for_terms(content, [entity], limit=4),
                related=[source_page],
            )
            self._record_touch(result, page)
            related_pages.append(page)

        for concept in self._extract_concepts(content, title):
            page = self._merge_fact_page(
                path=f"wiki/concepts/{self._slug(concept)}",
                title=concept.replace("_", " ").title(),
                page_type="concept",
                source_path=source_path,
                facts=self._sentences_for_terms(content, [concept.replace("_", " ")], limit=3),
                related=[source_page],
            )
            self._record_touch(result, page)
            related_pages.append(page)

        timeline_page = self._timeline_page(source_path, title, content, related_pages, metadata)
        if timeline_page:
            self._record_touch(result, timeline_page)

        temporal_facts = self._temporal_facts(source_path, title, content, metadata)
        if temporal_facts:
            page = self._merge_fact_page(
                path="wiki/facts/temporal-state",
                title="Temporal State",
                page_type="temporal-facts",
                source_path=source_path,
                facts=temporal_facts,
                related=related_pages[:8],
            )
            self._record_touch(result, page)

        for status, facts in self._status_facts(content).items():
            page = self._merge_fact_page(
                path=f"wiki/status/{self._slug(status)}",
                title=f"Status: {status}",
                page_type="status-register",
                source_path=source_path,
                facts=facts,
                related=related_pages[:8],
            )
            self._record_touch(result, page)

        for thread in self._extract_threads(content, title):
            page = self._merge_fact_page(
                path=f"wiki/threads/{self._slug(thread)}",
                title=f"Thread: {thread}",
                page_type="thread",
                source_path=source_path,
                facts=self._sentences_for_terms(content, thread.split(), limit=5),
                related=related_pages[:8],
            )
            self._record_touch(result, page)

        decision_facts = self._decision_facts(content)
        if decision_facts:
            page = self._merge_fact_page(
                path="wiki/decisions/decision-log",
                title="Decision Log",
                page_type="decision-log",
                source_path=source_path,
                facts=decision_facts,
                related=related_pages[:8],
            )
            self._record_touch(result, page)

        negative_facts = self._negative_facts(content)
        if negative_facts:
            page = self._merge_fact_page(
                path="wiki/facts/negative-facts",
                title="Negative Facts and Cancellations",
                page_type="negative-facts",
                source_path=source_path,
                facts=negative_facts,
                related=related_pages[:8],
            )
            self._record_touch(result, page)

        constraint_facts = self._constraint_facts(content)
        if constraint_facts:
            page = self._merge_fact_page(
                path="wiki/facts/constraints",
                title="Constraints and Gating Items",
                page_type="constraint-facts",
                source_path=source_path,
                facts=constraint_facts,
                related=related_pages[:8],
            )
            self._record_touch(result, page)

        approval_exception_facts = self._approval_exception_facts(content)
        if approval_exception_facts:
            page = self._merge_fact_page(
                path="wiki/facts/approvals-and-exceptions",
                title="Approvals and Exceptions",
                page_type="approval-exception-facts",
                source_path=source_path,
                facts=approval_exception_facts,
                related=related_pages[:8],
            )
            self._record_touch(result, page)

        change_facts = self._change_facts(source_path, title, content, metadata)
        if change_facts:
            page = self._merge_fact_page(
                path="wiki/facts/change-log",
                title="Change Log",
                page_type="change-facts",
                source_path=source_path,
                facts=change_facts,
                related=related_pages[:8],
            )
            self._record_touch(result, page)

        self._update_index()
        self._append_log("ingest", source_path, result.touched_pages)
        return result

    def compile_existing(self, prefix: str = "") -> int:
        """Compile existing non-wiki nodes, optionally restricted by path prefix."""
        count = 0
        for path in self._tree.list_paths(prefix):
            if path.startswith(WIKI_PREFIX):
                continue
            node = self._tree.get(path)
            if node is None:
                continue
            self.compile_source_node(node)
            count += 1
        return count

    def lint(self) -> list[WikiIssue]:
        """Run lightweight consistency checks over compiled wiki pages."""
        issues: list[WikiIssue] = []
        wiki_paths = self._tree.list_paths(WIKI_PREFIX)
        wiki_set = set(wiki_paths)

        if "wiki/index" not in wiki_set:
            issues.append(WikiIssue("error", "wiki/index", "Missing wiki index page."))

        inbound = {path: 0 for path in wiki_paths}
        for path in wiki_paths:
            node = self._tree.get(path)
            if node is None:
                continue
            if "Source:" not in node.content and path not in {"wiki/index", "wiki/log"}:
                issues.append(WikiIssue("warning", path, "Wiki page has no source reference."))
            if node.token_estimate > 2500:
                issues.append(
                    WikiIssue(
                        "warning",
                        path,
                        "Wiki page is large enough to hurt targeted retrieval.",
                        "Split this page into narrower pages.",
                    ),
                )
            for ref in self.extract_wiki_refs(node.content):
                if ref in inbound:
                    inbound[ref] += 1
                elif ref.startswith(WIKI_PREFIX):
                    issues.append(WikiIssue("warning", path, f"Broken wiki reference: {ref}"))

        for path, count in inbound.items():
            if count == 0 and path not in {"wiki/index", "wiki/log"}:
                issues.append(WikiIssue("info", path, "Wiki page has no inbound links."))

        return issues

    @staticmethod
    def extract_source_refs(content: str) -> list[str]:
        """Extract raw source paths referenced by a wiki page."""
        refs: list[str] = []
        for match in _SOURCE_REF_RE.finditer(content):
            text = (match.group(1) or match.group(2) or "").strip()
            if not text:
                continue
            for value in re.split(r"[,\s]+", text):
                value = value.strip(" []()`.,")
                if value and not value.startswith(WIKI_PREFIX) and "/" in value and value not in refs:
                    refs.append(value)
        return refs

    @staticmethod
    def extract_wiki_refs(content: str) -> list[str]:
        """Extract wiki page paths mentioned in content."""
        refs: list[str] = []
        for match in _WIKI_REF_RE.finditer(content):
            value = match.group(0).strip(".,)")
            if value not in refs:
                refs.append(value)
        return refs

    def _upsert_page(self, path: str, title: str, content: str, page_type: str) -> str:
        existed = self._tree.get(path) is not None
        self._tree.add(
            path=path,
            title=title,
            content=content,
            category=WIKI_CATEGORY,
            metadata={"type": page_type},
        )
        return path if existed else f"+{path}"

    def _merge_fact_page(
        self,
        path: str,
        title: str,
        page_type: str,
        source_path: str,
        facts: list[str],
        related: Iterable[str],
    ) -> str:
        existing = self._tree.get(path)
        existing_content = existing.content if existing else ""
        lines = existing_content.splitlines() if existing_content else self._page_header(title, page_type)

        source_line = f"- {source_path}"
        if source_line not in lines:
            self._ensure_section(lines, "## Sources")
            lines.append(source_line)

        if facts:
            self._ensure_section(lines, "## Facts")
            for fact in facts:
                fact_line = f"- {fact.strip()} (Source: {source_path})"
                if fact_line not in lines:
                    lines.append(fact_line)

        related_values = [self._clean_touched_path(path) for path in related]
        related_values = [value for value in related_values if value and value != path]
        if related_values:
            self._ensure_section(lines, "## Related")
            for ref in related_values:
                ref_line = f"- {ref}"
                if ref_line not in lines:
                    lines.append(ref_line)

        content = "\n".join(lines).strip() + "\n"
        existed = existing is not None
        self._tree.add(path, title, content, category=WIKI_CATEGORY, metadata={"type": page_type})
        return path if existed else f"+{path}"

    def _source_summary(
        self,
        source_path: str,
        title: str,
        content: str,
        source_category: str,
        metadata: Optional[dict] = None,
    ) -> str:
        sentences = self._top_sentences(content, limit=8)
        keywords = self._extract_concepts(content, title)[:12]
        entities = self._extract_entities(content)[:12]
        dates = self._extract_dates_and_days(source_path, title, content, metadata)
        parts = self._page_header(f"Source Summary: {title}", "source")
        parts.extend([
            "## Source",
            f"Source: {source_path}",
            f"Category: {source_category}",
            "",
            "## Summary",
        ])
        parts.extend(f"- {sentence}" for sentence in sentences)
        parts.extend(["", "## Key Concepts"])
        parts.extend(f"- {keyword}" for keyword in keywords)
        parts.extend(["", "## Entities"])
        parts.extend(f"- {entity}" for entity in entities)
        if dates:
            parts.extend(["", "## Dates and Days"])
            parts.extend(f"- {value}" for value in dates)
        return "\n".join(parts).strip() + "\n"

    def _timeline_page(
        self,
        source_path: str,
        title: str,
        content: str,
        related: list[str],
        metadata: Optional[dict] = None,
    ) -> Optional[str]:
        dates = self._extract_dates_and_days(source_path, title, content, metadata)
        if not dates:
            return None
        facts = self._top_sentences(content, limit=5)
        key = self._slug(dates[0])
        return self._merge_fact_page(
            path=f"wiki/timeline/{key}",
            title=f"Timeline: {dates[0]}",
            page_type="timeline",
            source_path=source_path,
            facts=facts,
            related=related[:8],
        )

    def _update_index(self) -> None:
        rows = []
        for path in self._tree.list_paths(WIKI_PREFIX):
            if path in {"wiki/index", "wiki/log"}:
                continue
            node = self._tree.get(path)
            if node is None:
                continue
            summary = self._first_fact_or_line(node.content)
            rows.append((path, node.title, summary, node.token_estimate))

        parts = [
            "# Wiki Index",
            "",
            "Compiled source-backed memory. Read this first for wiki-aware retrieval.",
            "",
        ]
        current_section = None
        for path, title, summary, tokens in sorted(rows):
            section = path.split("/", 2)[1] if "/" in path else "misc"
            if section != current_section:
                current_section = section
                parts.extend(["", f"## {section.replace('_', ' ').title()}"])
            parts.append(f"- {path} | {title} | {summary} ({tokens} tokens)")

        self._tree.add(
            "wiki/index",
            "Wiki Index",
            "\n".join(parts).strip() + "\n",
            category=WIKI_CATEGORY,
            metadata={"type": "index"},
        )

    def _append_log(self, operation: str, source_path: str, pages: list[str]) -> None:
        existing = self._tree.get("wiki/log")
        content = existing.content if existing else "# Wiki Log\n"
        entry = [
            f"## {operation} | {source_path}",
            f"Source: {source_path}",
            "Pages touched:",
        ]
        entry.extend(f"- {self._clean_touched_path(page)}" for page in pages)
        content = content.rstrip() + "\n\n" + "\n".join(entry) + "\n"
        self._tree.add("wiki/log", "Wiki Log", content, category=WIKI_CATEGORY, metadata={"type": "log"})

    @staticmethod
    def _record_touch(result: WikiCompilationResult, touched_path: str) -> None:
        target = result.pages_created if touched_path.startswith("+") else result.pages_updated
        path = touched_path[1:] if touched_path.startswith("+") else touched_path
        if path not in target:
            target.append(path)

    @staticmethod
    def _clean_touched_path(path: str) -> str:
        return path[1:] if path.startswith("+") else path

    @staticmethod
    def _page_header(title: str, page_type: str) -> list[str]:
        return [f"# {title}", "", f"Type: {page_type}", ""]

    @staticmethod
    def _ensure_section(lines: list[str], heading: str) -> None:
        if heading not in lines:
            if lines and lines[-1] != "":
                lines.append("")
            lines.append(heading)

    @staticmethod
    def _slug(value: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
        return slug or "untitled"

    def _extract_entities(self, content: str) -> list[str]:
        seen: list[str] = []
        for match in _ENTITY_RE.finditer(content):
            value = match.group(0).strip()
            if value in _ENTITY_STOP_WORDS:
                continue
            if value.lower() in {"source", "category", "summary"}:
                continue
            if value not in seen:
                seen.append(value)
            if len(seen) >= 20:
                break
        return seen

    @staticmethod
    def _extract_concepts(content: str, title: str) -> list[str]:
        concepts: list[str] = []
        for keyword in extract_keywords(f"{title} {content}", top_k=20):
            if keyword.isdigit():
                continue
            if keyword not in concepts:
                concepts.append(keyword)
        return concepts

    def _sentences_for_terms(self, content: str, terms: list[str], limit: int) -> list[str]:
        lower_terms = [term.lower() for term in terms]
        matches: list[str] = []
        for sentence in self._sentences(content):
            lower = sentence.lower()
            if any(term in lower for term in lower_terms):
                matches.append(sentence)
            if len(matches) >= limit:
                break
        return matches or self._top_sentences(content, limit=1)

    def _decision_facts(self, content: str) -> list[str]:
        return [
            sentence for sentence in self._sentences(content)
            if any(word in sentence.lower() for word in _DECISION_WORDS)
        ][:12]

    def _negative_facts(self, content: str) -> list[str]:
        return [
            sentence for sentence in self._sentences(content)
            if any(word in sentence.lower() for word in _NEGATIVE_WORDS)
        ][:12]

    def _constraint_facts(self, content: str) -> list[str]:
        return [
            f"Constraint: {sentence}"
            for sentence in self._sentences(content)
            if any(word in sentence.lower() for word in _CONSTRAINT_WORDS)
        ][:12]

    def _approval_exception_facts(self, content: str) -> list[str]:
        return [
            f"Approval/Exception: {sentence}"
            for sentence in self._sentences(content)
            if any(word in sentence.lower() for word in _APPROVAL_EXCEPTION_WORDS)
        ][:12]

    def _change_facts(self, source_path: str, title: str, content: str, metadata: Optional[dict] = None) -> list[str]:
        dates = self._extract_dates_and_days(source_path, title, content, metadata)
        time_label = ", ".join(dates[:2]) if dates else "unspecified-time"
        return [
            f"Time: {time_label} | Change: {sentence}"
            for sentence in self._sentences(content)
            if any(word in sentence.lower() for word in _CHANGE_WORDS)
        ][:12]

    def _temporal_facts(self, source_path: str, title: str, content: str, metadata: Optional[dict] = None) -> list[str]:
        dates = self._extract_dates_and_days(source_path, title, content, metadata)
        status_by_sentence = self._status_by_sentence(content)
        facts: list[str] = []
        for sentence in self._sentences(content):
            sentence_dates = self._extract_dates_and_days("", "", sentence) or dates[:2]
            sentence_statuses = status_by_sentence.get(sentence, [])
            if not sentence_dates and not sentence_statuses:
                continue
            time_label = ", ".join(sentence_dates) if sentence_dates else "unspecified-time"
            status_label = ", ".join(sentence_statuses) if sentence_statuses else "observed"
            facts.append(f"Time: {time_label} | Status: {status_label} | Fact: {sentence}")
            if len(facts) >= 16:
                break
        return facts

    def _status_facts(self, content: str) -> dict[str, list[str]]:
        by_status: dict[str, list[str]] = {}
        for sentence, statuses in self._status_by_sentence(content).items():
            for status in statuses:
                by_status.setdefault(status, []).append(f"Status: {status} | Fact: {sentence}")
        return {status: facts[:12] for status, facts in by_status.items()}

    def _status_by_sentence(self, content: str) -> dict[str, list[str]]:
        by_sentence: dict[str, list[str]] = {}
        for sentence in self._sentences(content):
            lower = sentence.lower()
            statuses = [
                status for status, words in _STATUS_WORDS.items()
                if any(word in lower for word in words)
            ]
            if statuses:
                by_sentence[sentence] = statuses
        return by_sentence

    def _extract_threads(self, content: str, title: str) -> list[str]:
        entities = self._extract_entities(content)
        concepts = self._extract_concepts(content, title)
        threads: list[str] = []
        seen: set[str] = set()

        for entity in entities[:6]:
            if entity.lower() not in seen:
                threads.append(entity)
                seen.add(entity.lower())

        for concept in concepts[:8]:
            if concept in {"source", "date", "day"}:
                continue
            concept_title = concept.replace("_", " ").title()
            if concept_title.lower() in seen:
                continue
            threads.append(concept_title)
            seen.add(concept_title.lower())
            if len(threads) >= 10:
                break

        return threads

    def _extract_dates_and_days(
        self,
        source_path: str,
        title: str,
        content: str,
        metadata: Optional[dict] = None,
    ) -> list[str]:
        text = f"{source_path} {title} {content}"
        values: list[str] = []
        if metadata:
            source_date = str(metadata.get("source_date") or metadata.get("date") or "").strip()
            if source_date and source_date not in values:
                values.append(source_date)
            for anchor in metadata.get("temporal_anchors", []) or []:
                if not isinstance(anchor, dict):
                    continue
                kind = str(anchor.get("kind") or "").strip().lower()
                unit = str(anchor.get("unit") or "").strip().lower()
                value = anchor.get("value")
                if kind in {"sequence", "ordinal"} and unit == "day" and value is not None:
                    try:
                        label = f"day-{int(value)}"
                    except (TypeError, ValueError):
                        continue
                    if label not in values:
                        values.append(label)
        for value in _DATE_RE.findall(text):
            if value not in values:
                values.append(value)
        for value in _DAY_RE.findall(text):
            day = f"day-{int(value)}"
            if day not in values:
                values.append(day)
        return values[:20]

    @staticmethod
    def _sentences(content: str) -> list[str]:
        normalized = re.sub(r"\s+", " ", content).strip()
        if not normalized:
            return []
        pieces = re.split(r"(?<=[.!?])\s+|\n+", normalized)
        return [piece.strip(" -\t") for piece in pieces if len(piece.strip()) > 10]

    def _top_sentences(self, content: str, limit: int) -> list[str]:
        sentences = self._sentences(content)
        if not sentences:
            return []
        keywords = set(extract_keywords(content, top_k=12))
        scored = []
        for index, sentence in enumerate(sentences):
            words = set(extract_keywords(sentence, top_k=20))
            score = len(words & keywords) + max(0, 3 - index) * 0.25
            scored.append((score, index, sentence))
        scored.sort(key=lambda item: (-item[0], item[1]))
        return [sentence for _, _, sentence in scored[:limit]]

    @staticmethod
    def _first_fact_or_line(content: str) -> str:
        for line in content.splitlines():
            stripped = line.strip(" -")
            if stripped and not stripped.startswith("#") and not stripped.startswith("Type:"):
                return stripped[:160]
        return "No summary available"
