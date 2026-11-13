"""Relate-backed metadata graph. Every impact answer is a bounded Cypher traversal."""
from __future__ import annotations

import json
from pathlib import Path

import relate

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data" / "metadata.json"
STORE = ROOT / "data" / "sample.rl"
MAX_HOPS = 12
MAX_PATHS = 600
OUTPUT_KINDS = {"Dashboard", "Metric"}
KINDS = {"System", "Table", "Column", "Transformation", "Rule", "Model", "Metric", "Dashboard"}


def validate(metadata: dict) -> None:
    assets, edges = metadata["assets"], metadata["flows"]
    ids = [a["id"] for a in assets]
    if len(set(ids)) != len(ids) or not ids:
        raise ValueError("Asset ids must be unique and nonempty")
    if any(a["kind"] not in KINDS for a in assets):
        raise ValueError("Unexpected asset kind")
    index = set(ids)
    pairs = set()
    for edge in edges:
        a, b = edge["from"], edge["to"]
        if a not in index or b not in index or a == b:
            raise ValueError(f"Invalid flow: {a} -> {b}")
        if (a, b) in pairs:
            raise ValueError(f"Duplicate flow: {a} -> {b}")
        pairs.add((a, b))
    # Bound path enumeration by requiring a DAG: back-edges are import errors.
    adjacent = {a: [] for a in ids}
    for edge in edges:
        adjacent[edge["from"]].append(edge["to"])
    visiting, visited = set(), set()

    def dfs(node):
        if node in visiting:
            raise ValueError(f"Dependency cycle through {node}")
        if node in visited:
            return
        visiting.add(node)
        for nxt in adjacent[node]:
            dfs(nxt)
        visiting.remove(node)
        visited.add(node)

    for asset_id in ids:
        dfs(asset_id)


def seed(metadata_path: Path = SAMPLE, store_path: Path = STORE, *, force: bool = False) -> dict:
    """Import the synthetic metadata into a real persistent Relate .rl file."""
    metadata = json.loads(Path(metadata_path).read_text(encoding="utf-8"))
    validate(metadata)
    store_path = Path(store_path)
    store_path.parent.mkdir(parents=True, exist_ok=True)
    if store_path.exists():
        if not force:
            raise FileExistsError(f"{store_path} exists; use --force for a fresh import")
        store_path.unlink()
    with relate.connect(str(store_path)) as db:
        db.autocommit = False
        try:
            for a in metadata["assets"]:
                db.execute(
                    "CREATE (:Asset {id: $id, name: $name, kind: $kind, "
                    "system: $system, detail: $detail, risk: $risk})",
                    {key: a.get(key, "") for key in ("id", "name", "kind", "system", "detail", "risk")},
                )
            for edge in metadata["flows"]:
                db.execute(
                    "MATCH (a:Asset {id: $a}), (b:Asset {id: $b}) "
                    "CREATE (a)-[:FLOWS_TO {why: $why, mode: $mode}]->(b)",
                    {"a": edge["from"], "b": edge["to"],
                     "why": edge["why"], "mode": edge["mode"]},
                )
            db.commit()
        except Exception:
            db.rollback()
            raise
    return {"assets": len(metadata["assets"]), "flows": len(metadata["flows"]), "store": str(store_path)}


def _asset(n) -> dict:
    return {k: n.properties.get(k, "") for k in ("id", "name", "kind", "system", "detail", "risk")}


def overview(store_path: Path = STORE) -> dict:
    with relate.connect(str(store_path), read_only=True) as db:
        assets = [_asset(r["n"]) for r in db.execute("MATCH (n:Asset) RETURN n ORDER BY n.id LIMIT 250")]
        flows = [dict(r) for r in db.execute(
            "MATCH (a:Asset)-[r:FLOWS_TO]->(b:Asset) "
            "RETURN a.id AS source, b.id AS target, r.why AS why, r.mode AS mode LIMIT 400"
        )]
    return {"assets": assets, "flows": flows, "store": str(store_path)}


def impact(asset_id: str, direction: str = "downstream", store_path: Path = STORE) -> dict:
    """Return targets with up to two *real Relate paths* per target."""
    if direction not in ("downstream", "upstream"):
        raise ValueError("direction must be downstream or upstream")
    if len(asset_id) > 240:
        raise ValueError("asset id too long")
    if direction == "downstream":
        query = f"MATCH p = (root:Asset {{id: $id}})-[:FLOWS_TO*1..{MAX_HOPS}]->(target:Asset) RETURN p ORDER BY length(p) ASC LIMIT {MAX_PATHS}"
    else:
        query = f"MATCH p = (root:Asset {{id: $id}})<-[:FLOWS_TO*1..{MAX_HOPS}]-(target:Asset) RETURN p ORDER BY length(p) ASC LIMIT {MAX_PATHS}"
    targets: dict[str, dict] = {}
    with relate.connect(str(store_path), read_only=True) as db:
        origin = db.execute("MATCH (a:Asset {id: $id}) RETURN a", {"id": asset_id}).fetchone()
        if origin is None:
            raise KeyError(asset_id)
        source = _asset(origin["a"])
        result = db.execute(query, {"id": asset_id}).fetchall()
        for row in result:
            path = row["p"]
            steps = [_asset(n) for n in path.nodes]
            dst = steps[-1]
            item = targets.setdefault(dst["id"], {**dst, "hops": len(path), "paths": []})
            if len(item["paths"]) >= 2:
                continue
            item["paths"].append({
                "ids": [n["id"] for n in steps],
                "edges": [{"why": r.properties.get("why", ""), "mode": r.properties.get("mode", "")}
                          for r in path.relationships],
            })
    items = sorted(targets.values(), key=lambda a: (a["hops"], a["kind"] not in OUTPUT_KINDS, a["name"]))
    outputs = [a for a in items if a["kind"] in OUTPUT_KINDS]
    return {"source": source, "direction": direction, "affected": items, "outputs": outputs,
            "affected_count": len(items), "output_count": len(outputs),
            "systems": sorted({a["system"] for a in items if a["system"]}),
            "truncated": len(result) >= MAX_PATHS, "query": query}

def receipt(asset_id: str, direction: str = "downstream", store_path: Path = STORE,
            change: str = "") -> str:
    """A reviewer-ready Markdown explanation from native Relate paths, not inferred text."""
    if len(change) > 240:
        raise ValueError("change description too long")
    evidence = impact(asset_id, direction, store_path)
    source = evidence["source"]
    change = " ".join(change.split())
    arrow = " → " if direction == "downstream" else " ← "
    lines = [
        f"# Data impact review: {source['name']}", "",
        f"- Asset: `{source['id']}` ({source['kind']}, {source['system']})",
        f"- Direction: {direction}",
        f"- Connected assets requiring review: {evidence['affected_count']}",
        f"- Business outputs requiring review: {evidence['output_count']}",
        f"- Impacted systems: {', '.join(evidence['systems']) or 'none'}",
    ]
    if change:
        lines.append(f"- Proposed change (user-supplied): {change}")
    lines += [
        "",
        "> Potential impact, not a prediction of failure. Only documented metadata dependencies",
        "> are traversed; missing lineage can hide additional impacts.",
        "", "## Affected business outputs", "",
    ]
    if not evidence["outputs"]:
        lines += ["No connected business outputs were found in this direction.", ""]
    for target in evidence["outputs"]:
        lines += [
            f"### {target['name']} — {target['kind']} in {target['system']}",
            f"Shortest documented route: {target['hops']} hops", "",
        ]
        for number, path in enumerate(target["paths"], 1):
            lines += [
                f"**{'Shortest' if number == 1 else 'Alternative'} Relate path:**", "",
                arrow.join(f"`{id_}`" for id_ in path["ids"]), "",
            ]
            for idx, edge in enumerate(path["edges"]):
                lines.append(
                    f"{idx + 1}. `{path['ids'][idx]}` {arrow.strip()} "
                    f"`{path['ids'][idx + 1]}` — {edge['why']} "
                    f"(`{edge['mode']}`)"
                )
            lines.append("")
    if evidence["truncated"]:
        lines += [
            "**Incomplete enumeration:** the Cypher path cap was reached. "
            "Do not treat this as an exhaustive impact inventory.", "",
        ]
    lines += [
        "## Verification", "",
        "Results come from bounded, parameterized Cypher path traversals over the",
        "persistent embedded Relate store `data/sample.rl`; no LLM guesses or SQL execution.",
        "The source metadata is synthetic. Review the actual transformation and rule",
        "implementations before approving a production change.", "",
    ]
    return "\n".join(lines)
