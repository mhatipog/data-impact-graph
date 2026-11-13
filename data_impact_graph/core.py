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
    # Reject dependency cycles without recursive DFS depth failures on long
    # lineage chains. The embedded Cypher traversal is deliberately bounded.
    adjacent = {asset_id: [] for asset_id in ids}
    indegree = {asset_id: 0 for asset_id in ids}
    for edge in edges:
        adjacent[edge["from"]].append(edge["to"])
        indegree[edge["to"]] += 1
    queue = [asset_id for asset_id in ids if indegree[asset_id] == 0]
    cursor = 0
    while cursor < len(queue):
        asset_id = queue[cursor]
        cursor += 1
        for target in adjacent[asset_id]:
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
    if cursor != len(ids):
        raise ValueError("Dependency cycle detected in imported graph")


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
                    "CREATE (a)-[:FLOWS_TO {why: $why, mode: $mode, provenance: $provenance}]->(b)",
                    {"a": edge["from"], "b": edge["to"],
                     "why": edge["why"], "mode": edge["mode"], "provenance": edge.get("provenance", "")},
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
        assets = [_asset(r["n"]) for r in db.execute("MATCH (n:Asset) RETURN n ORDER BY n.id LIMIT 2000")]
        flows = [dict(r) for r in db.execute(
            "MATCH (a:Asset)-[r:FLOWS_TO]->(b:Asset) "
            "RETURN a.id AS source, b.id AS target, r.why AS why, r.mode AS mode, "
            "r.provenance AS provenance LIMIT 4000"
        )]
    return {"assets": assets, "flows": flows, "store": str(store_path),
            "source": "openlineage" if any(a["id"].startswith("ol:") for a in assets) else "sample",
            "truncated": len(assets) == 2000 or len(flows) == 4000}


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
                "edges": [{"why": r.properties.get("why", ""), "mode": r.properties.get("mode", ""),
                           "provenance": r.properties.get("provenance", "")}
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
    upstream_inputs = [asset for asset in evidence["affected"] if asset["kind"] in {"Column", "Rule"}]
    targets = evidence["outputs"] if direction == "downstream" else upstream_inputs
    is_openlineage = source["id"].startswith("ol:")
    if direction == "downstream" and is_openlineage:
        targets = [asset for asset in evidence["affected"] if asset["kind"] in {"Table", "Column"}]
    section = ("Downstream datasets and fields requiring review" if is_openlineage else "Affected business outputs") if direction == "downstream" else "Upstream source fields and business rules"
    lines += [
        "",
        "> Potential impact, not a prediction of failure. Only documented metadata dependencies",
        "> are traversed; missing lineage can hide additional impacts.",
        "", f"## {section}", "",
    ]
    if not targets:
        lines += [(("No downstream datasets or fields are documented." if is_openlineage else "No connected business outputs were found in this direction.") if direction == "downstream"
                   else "No source fields or rules were found in the documented upstream graph."), ""]
    for target in targets:
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
