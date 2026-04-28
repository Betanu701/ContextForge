"""Tests for KnowledgeTree — CRUD, traversal, ingestion."""

from __future__ import annotations

import os
import pytest
from contextforge.tree import KnowledgeTree


@pytest.fixture
def tree():
    t = KnowledgeTree(db_path=":memory:")
    t.open()
    yield t
    t.close()


class TestCRUD:
    def test_add_and_get(self, tree: KnowledgeTree):
        node = tree.add("finance/q3", "Q3 Report", "Revenue was $10M in Q3.")
        assert node.id is not None
        assert node.path == "finance/q3"
        assert node.title == "Q3 Report"

        retrieved = tree.get("finance/q3")
        assert retrieved is not None
        assert retrieved.content == "Revenue was $10M in Q3."

    def test_get_nonexistent(self, tree: KnowledgeTree):
        assert tree.get("nonexistent") is None

    def test_update_existing(self, tree: KnowledgeTree):
        tree.add("docs/readme", "README", "Version 1")
        tree.add("docs/readme", "README v2", "Version 2")
        node = tree.get("docs/readme")
        assert node is not None
        assert node.title == "README v2"
        assert node.content == "Version 2"

    def test_remove(self, tree: KnowledgeTree):
        tree.add("temp/node", "Temp", "Will be deleted")
        assert tree.remove("temp/node") is True
        assert tree.get("temp/node") is None

    def test_remove_nonexistent(self, tree: KnowledgeTree):
        assert tree.remove("nope") is False

    def test_total_nodes(self, tree: KnowledgeTree):
        assert tree.total_nodes() == 0
        tree.add("a", "A", "Content A")
        tree.add("b", "B", "Content B")
        assert tree.total_nodes() == 2


class TestTraversal:
    def test_list_paths(self, tree: KnowledgeTree):
        tree.add("finance/q1", "Q1", "Q1 data")
        tree.add("finance/q2", "Q2", "Q2 data")
        tree.add("engineering/arch", "Arch", "Architecture doc")
        paths = tree.list_paths("finance/")
        assert len(paths) == 2
        assert "finance/q1" in paths

    def test_list_categories(self, tree: KnowledgeTree):
        tree.add("a", "A", "Content", category="finance")
        tree.add("b", "B", "Content", category="engineering")
        tree.add("c", "C", "Content", category="finance")
        cats = tree.list_categories()
        assert set(cats) == {"finance", "engineering"}

    def test_parent_child(self, tree: KnowledgeTree):
        tree.add("company", "Company", "Root node")
        tree.add("company/finance", "Finance", "Finance dept", parent_path="company")
        tree.add("company/engineering", "Engineering", "Eng dept", parent_path="company")

        children = tree.get_children("company")
        assert len(children) == 2
        names = {c.title for c in children}
        assert names == {"Finance", "Engineering"}

    def test_get_branch(self, tree: KnowledgeTree):
        tree.add("root", "Root", "Root node")
        tree.add("root/child1", "Child 1", "C1", parent_path="root")
        tree.add("root/child2", "Child 2", "C2", parent_path="root")
        tree.add("root/child1/grandchild", "GC", "GC1", parent_path="root/child1")

        branch = tree.get_branch("root")
        assert len(branch) == 4
        paths = {n.path for n in branch}
        assert "root/child1/grandchild" in paths

    def test_get_branch_nonexistent(self, tree: KnowledgeTree):
        assert tree.get_branch("nope") == []


class TestChunks:
    def test_chunks_created(self, tree: KnowledgeTree):
        long_content = "This is a test sentence. " * 200
        node = tree.add("doc", "Doc", long_content, chunk_size=128)
        chunks = tree.get_chunks(node.id)
        assert len(chunks) > 1

    def test_chunks_single_short(self, tree: KnowledgeTree):
        node = tree.add("short", "Short", "Hello world")
        chunks = tree.get_chunks(node.id)
        assert len(chunks) == 1


class TestSearch:
    def test_search_by_category(self, tree: KnowledgeTree):
        tree.add("a", "Financial Report", "Revenue data", category="finance")
        tree.add("b", "Code Review", "Pull request", category="engineering")
        results = tree.search(category="finance")
        assert len(results) == 1
        assert results[0].category == "finance"

    def test_search_by_keyword(self, tree: KnowledgeTree):
        tree.add("a", "Q3 Report", "Revenue was $10M in Q3", category="finance")
        tree.add("b", "Q2 Report", "Revenue was $8M in Q2", category="finance")
        results = tree.search(keyword="Q3")
        assert len(results) == 1

    def test_search_combined(self, tree: KnowledgeTree):
        tree.add("a", "Q3 Finance", "Revenue $10M", category="finance")
        tree.add("b", "Q3 Eng", "Shipped 5 features", category="engineering")
        results = tree.search(category="finance", keyword="Revenue")
        assert len(results) == 1


class TestIngestion:
    def test_ingest_directory(self, tree: KnowledgeTree):
        # Create a temp structure using the tree's own test data
        test_dir = os.path.join(os.path.dirname(__file__), "_test_ingest_data")
        os.makedirs(os.path.join(test_dir, "sub"), exist_ok=True)
        try:
            with open(os.path.join(test_dir, "file1.txt"), "w") as f:
                f.write("Hello from file 1")
            with open(os.path.join(test_dir, "sub", "file2.md"), "w") as f:
                f.write("Hello from file 2")

            count = tree.ingest_directory(test_dir, category="test")
            assert count == 2
            assert tree.total_nodes() >= 2

            paths = tree.list_paths("test/")
            assert any("file1" in p for p in paths)
            assert any("file2" in p for p in paths)
        finally:
            import shutil
            shutil.rmtree(test_dir, ignore_errors=True)

    def test_ingest_nonexistent_raises(self, tree: KnowledgeTree):
        with pytest.raises(FileNotFoundError):
            tree.ingest_directory("/nonexistent/path")
