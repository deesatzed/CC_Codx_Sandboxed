from pathlib import Path

from graph_context import compact_subgraph


def test_missing_graph_is_empty(tmp_path: Path):
    assert compact_subgraph(tmp_path / "nope.json", "auth") == ""


def test_compact_picks_query_neighbors(tmp_path: Path):
    graph = {
        "nodes": [
            {"id": "Ledger", "label": "Ledger", "source_file": "ledger.py"},
            {"id": "cliPC2chat", "label": "cliPC2chat", "source_file": "cliPC2chat.py"},
            {"id": "unrelated", "label": "unrelated", "source_file": "other.py"},
        ],
        "edges": [
            {
                "source": "cliPC2chat",
                "target": "Ledger",
                "rel": "imports",
                "confidence": "EXTRACTED",
            }
        ],
    }
    path = tmp_path / "graph.json"
    path.write_text(__import__("json").dumps(graph))
    text = compact_subgraph(path, "How does Ledger get written?")
    assert "Ledger" in text
    assert "cliPC2chat" in text
    assert "imports" in text
    assert len(text) < 2500
