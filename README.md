# Data Impact Graph

**Before changing a source field, see which business outcomes depend on it—and the exact graph path explaining why.**

A local, dependency-aware lineage explorer for data engineers, built for the [Relate by Neo4j Hackathon](https://relate.devpost.com/). No API keys, graph server, LLM, frontend build or paid services. All data is fictional.

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

## Setup and run

Requirements: Python 3.9+, pip, Linux/macOS (or Windows with Python and `python -m data_impact_graph serve`). Python wheels must be available for your OS/architecture.

```bash
git clone https://github.com/mhatipog/data-impact-graph.git
cd data-impact-graph
./run.sh
```

Open **http://127.0.0.1:8765**. The default selection traces `lab.assays.moisture_pct` downstream. Click a metric to see the chain; click a node to pivot; search for any asset; toggle upstream/downstream or view all assets. The frontend uses native SVG and no CDN.

Useful first query, without the web interface:

```bash
. .venv/bin/activate
python -m data_impact_graph impact lab.assays.moisture_pct
python -m data_impact_graph impact metric.carbon --upstream
```

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

## Demo

See [`DEMO.md`](DEMO.md) for a 90-second screen-recording script.

## License

Apache-2.0. Synthetic metadata; no company systems, data or names are represented.
