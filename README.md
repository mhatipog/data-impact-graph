# Data Impact Graph

**Before changing a source field, see which business outcomes depend on it—and the exact graph path explaining why.**

A local, dependency-aware lineage explorer for data engineers, built for the [Relate by Neo4j Hackathon](https://relate.devpost.com/). No API keys, graph server, LLM, frontend build or paid services. The bundled example is fictional; you can also import lineage from your own OpenLineage events.

**Watch the current 1:46 hackathon film:** [Before the Merge — OpenLineage → Relate → impact review](demo/data-impact-graph-openlineage-film.mp4) · [10-frame preview](demo/openlineage-film-contact-sheet.png) · [Captions](demo/data-impact-graph-openlineage-film.srt). The video uses SDK-emitted events from actual executed SQLite SQL, a native Relate graph, and real Playwright UI captures. The underlying data is synthetic.

## Use case

You discover that `LabTrack.lot_assays.moisture_pct` is changing from a percentage to a fraction. What will break? A keyword search might find a quality check, but miss **supplier payout** and **Scope 3 carbon intensity**. Both secretly share a dry-mass adjustment.

This demo models 49 assets and 60 documented impact edges across FieldOps, LabTrack, CoreERP, FleetTrack, FinanceMart, ClimateMart and BoardBI. The graph contains source systems, tables, columns, transformations, business rules, models, metrics and dashboards.

**Why the edge semantics matter:** `FLOWS_TO` means *a change or outage at the start may affect the end*. Each edge records a specific `why` and a `mode` (`scope`, `derive`, `aggregate`, `publish`). System → table → column `scope` edges are deliberately one-way: changing the whole table can affect its columns; changing one column does **not** automatically affect its siblings. Field-level edges model explicit reads and calculations. This is dependency blast radius, not an assertion of observed breakage.

## How it uses Relate

- **Mode: single file.** `data/sample.rl` is a native, persistent Relate store, not an exported JSON adjacency list.
- **Why this mode:** judges can clone one graph file, inspect it via the Relate CLI and reopen it after restarting. No database server, credentials or service configuration.
- **What the graph models:** `(:Asset {id, name, kind, system, detail, risk})-[:FLOWS_TO {why, mode}]->(:Asset)`. Nodes and relationships are inserted with parameterized Cypher. Impact and reverse lineage are executed as **bounded variable-length path queries inside Relate**; Python only groups the returned paths for display.

An actual downstream query in `data_impact_graph/core.py`:

```cypher
MATCH p = (root:Asset {id: $id})-[:FLOWS_TO*1..12]->(target:Asset)
RETURN p ORDER BY length(p) ASC LIMIT 600
```

The reverse traversal uses `<-[:FLOWS_TO*1..12]-`. The JSON API includes the returned path nodes and each relationship's explanation, not fabricated links. See [Relate Python API](https://relatedb.ai/docs/reference/api/python/) and [Relate repo](https://github.com/relatedb/relate).

## Use real lineage from OpenLineage

**Your existing instrumentation is the source of truth.** Import standard OpenLineage JSON or JSONL events from Spark, Airflow, dbt, or another producer into a separate embedded Relate graph, then explore real dataset and field dependencies without running a metadata server.

```bash
python -m data_impact_graph import openlineage examples/openlineage-events.jsonl \
  --store data/openlineage.rl
python -m data_impact_graph serve --store data/openlineage.rl
```

The importer recognizes explicit Column Lineage, newer Job Lineage and Dataset Lineage facets. It retains schema inventory but **does not invent** input-to-output relationships from bare job boundaries, and it incrementally replaces older known mappings on later successful runs. Repeat an import safely: unchanged events are idempotent. The included events are synthetic and intended to test the OpenLineage-compatible workflow; point it at your own producer exports for real lineage.

Read [**OpenLineage ingestion, producer setup, limitations and provenance**](OPENLINEAGE.md). No live OpenLineage HTTP receiver or automatic Fabric/Power BI catalog connector is included yet.

## Setup and run

Requirements: Python 3.9+, pip, Linux/macOS (or Windows with Python and `python -m data_impact_graph serve`). Python wheels must be available for your OS/architecture.

```bash
git clone https://github.com/mhatipog/data-impact-graph.git
cd data-impact-graph
./run.sh
```

Open **http://127.0.0.1:8765**. The default selection traces `lab.assays.moisture_pct` all the way to the less-obvious **Scope 3 assurance** dashboard. The graph begins with a readable, two-row **shortest verified route**; click another business output to change the route. Switch to **Impact map** for all reachable assets or **All assets** for the full catalog. Click a node to pivot, search by column name, or toggle upstream/downstream. The frontend uses native SVG and no CDN.

For a useful precision contrast, choose **A narrower field change** in the sidebar: changing `field_id` affects the field-yield calculation but not payout or carbon intensity. Those unaffected outputs are excluded because the graph records column-specific read dependencies; these are not heuristic guesses.

Useful first query, without the web interface:

```bash
. .venv/bin/activate
python -m data_impact_graph impact lab.assays.moisture_pct
python -m data_impact_graph impact metric.carbon --upstream

# Markdown change-review receipt for a pull request or change advisory
python -m data_impact_graph report lab.assays.moisture_pct \
  --change "percent 0-100 to ratio 0-1" > impact-review.md
```

You can also enter the proposed change in the interface and click **Download impact receipt**. It lists affected business outputs with the exact traced IDs and each `why` explanation. The optional change description is recorded as a user-supplied note; it does not alter traversal or claim the change will cause failures. The read-only API endpoint is `GET /api/report?id=lab.assays.moisture_pct&change=percent-to-ratio`.

### Connect a coding agent directly to Relate (optional)

The repository includes a project-scoped [`.mcp.json`](.mcp.json) with the **native Relate MCP server**, not a custom or simulated agent integration. Install the official [Relate CLI](https://relatedb.ai/docs/get-started/install/) and open this project in an MCP-capable IDE (for example Claude Code, which requests approval for project MCP configurations). The config invokes:

```bash
relate serve --mcp stdio --database ./data/sample.rl --read-only
```

This exposes Relate's `get_schema` and `read_cypher` tools directly to your coding agent. Ask: **"Before changing LabTrack moisture_pct from percent to fraction, trace every downstream metric and dashboard in Relate, show why the Scope 3 dashboard is involved, and flag which sibling columns are *not* affected."** The optional `AGENTS.md` documents the semantics and a safe review protocol. The Python application and one-command setup do **not** require installing the CLI or any agent.

Run the integration tests:

```bash
. .venv/bin/activate
python -m unittest discover -s tests -v
```

Reimport the example (this **overwrites** the local store):

```bash
python -m data_impact_graph seed --force
```

To import another dataset, provide a metadata JSON with `assets` and `flows`, and use `python -m data_impact_graph seed --metadata /path/to/metadata.json --store /path/to/demo.rl`. The metadata importer checks unique IDs, missing endpoints, duplicate relationships and cycles.

## Where the data lives

- `data/sample.rl`: actual inspectable Relate **single-file** graph (not just generated at runtime).
- `data/metadata.json`: deterministic synthetic import source.
- `data_impact_graph/core.py`: native `relate.connect()` persistence, Cypher import and real path traversals.
- `static/`: lightweight frontend.

Independent CLI inspection (optional, after [installing Relate CLI](https://relatedb.ai/docs/get-started/install/)):

```bash
relate --database ./data/sample.rl --read-only \
  "MATCH (n:Asset) RETURN n.kind AS kind, count(n) AS assets ORDER BY assets DESC"
relate --database ./data/sample.rl --read-only \
  "MATCH p=(a:Asset {id:'lab.assays.moisture_pct'})-[:FLOWS_TO*1..12]->(d:Asset {id:'dash.esg'}) RETURN p LIMIT 3"
```

**Boundary:** synthetic, illustrative dependency metadata. The demo does not ingest production catalog APIs, predict the probability of breakage or execute arbitrary Cypher supplied by visitors. The server binds only `127.0.0.1` and exposes read-only graph queries. Paths are capped at 12 hops / 600 matches to bound work.

## Recorded demo — real OpenLineage workflow

**Primary film (1 min 46 sec):** [Watch / download MP4](demo/data-impact-graph-openlineage-film.mp4) · [Scene preview](demo/openlineage-film-contact-sheet.png) · [Subtitle file](demo/data-impact-graph-openlineage-film.srt) · [verified media manifest](demo/openlineage-film-manifest.json).

The film starts when a developer is reviewing a data-contract change, not with a fabricated network diagram. An instrumented local SQL pipeline **actually executes** its transformations. The official OpenLineage Python SDK emits schema and column-lineage facets from those SQL expressions. Data Impact Graph imports the resulting events into a local embedded Relate store and traverses the finance and carbon-intensity dependencies with real Cypher. A second field demonstrates how missing links should not become invented impacts. Finally, the live app exports a review receipt.

**Evidence and reproducibility:** [Film production guide](FILM.md) · [SDK-emitted events](examples/openlineage-sdk-emitted.jsonl) · [actual local SQL producer](scripts/instrumented-pipeline.py) · [real browser capture](demo/openlineage-browser-contact-sheet.png) · [native tests](tests/test_openlineage.py). The producer uses fictional input records; it is not a direct Fabric, Databricks or Airflow connection. The music is original, and the video includes a neural voiceover.

**Earlier technical material:** [83-second narrated story](demo/data-impact-graph-story.mp4) · [99-second uninterrupted real-app Playwright recording](demo/data-impact-graph-demo.mp4) · [original screenshot](demo/poster.png). These remain available for verification, but the new OpenLineage film is the recommended hackathon demo.

## AI-assisted development

ChatGPT assisted with code, synthetic metadata, tests and documentation. The production app does **not** call an LLM, an AI API or a remote graph service; dependency answers come from native Relate Cypher. All examples are fictional and any agent-facing MCP configuration is optional.

## License

Apache-2.0. Synthetic metadata; no company systems, data or names are represented.
