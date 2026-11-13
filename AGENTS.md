# Relate-backed impact review — instructions for coding agents

This repository provides a **native, persistent Relate graph** of synthetic data lineage. Before editing an asset, check its documented downstream dependencies and reverse lineage. Treat results as *potential* impacts, not proven failures; the catalog is illustrative, not exhaustive.

- No inference service or API key is involved. Run `python -m data_impact_graph impact lab.assays.moisture_pct` or `python -m data_impact_graph report lab.assays.moisture_pct --change "percent to fraction"` from the project virtualenv.
- If the `relate` CLI is installed, `.mcp.json` exposes the same `data/sample.rl` **read-only** to MCP-capable coding agents. Ask the MCP host to approve this project configuration; it exposes native Relate `get_schema` and `read_cypher` tools.
- Prefer explicit `MATCH p=(source:Asset {id: '...'})-[:FLOWS_TO*1..12]->(target:Asset) RETURN p LIMIT 20` queries and inspect `why` and `mode` on each `FLOWS_TO` relationship. Reverse direction for upstream analysis.
- For code review, name impacted business outputs, show the **exact path and edge explanation**, mention possible missing metadata, and distinguish change scope: changing a column must not contaminate unrelated sibling columns through its parent table.
- Never modify the included `.rl` store while reviewing. Rebuild a separate store with `seed --metadata ... --store ...` if testing an import. Do not claim an actual runtime failure from a metadata dependency.

## Imported lineage

- For real producer metadata, import OpenLineage into a **separate** store: `python -m data_impact_graph import openlineage events.jsonl --store data/openlineage.rl`. Never overwrite or silently substitute the bundled synthetic `data/sample.rl`.
- When answering questions about imported lineage, use `--store data/openlineage.rl` on CLI queries and reports. The committed `.mcp.json` intentionally points to the synthetic sample; an agent intending to inspect imported lineage must explicitly change its local MCP command to use the imported store, in read-only mode.
- A missing path is **not proof of no dependency**. Bare OpenLineage job inputs and outputs establish inventory, not exact field mappings. Check event/facet coverage before drawing conclusions.
- Cite `why` and `provenance` on each graph edge. Do not describe imported dataset columns as business dashboards unless external metadata supports that claim.
