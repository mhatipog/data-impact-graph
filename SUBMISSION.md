# Data Impact Graph — Devpost draft

**Tagline:** Know which business outcomes a source-data change could disrupt—and exactly why—before you merge it.

**What it does:** Data engineers often recognize that renaming a column breaks a transformation, but cannot easily see the hidden effect on supplier payments, regulatory disclosures and executive reports. Data Impact Graph models source systems, tables, columns, transformations, rules, models, metrics and dashboards as a compact, synthetic dependency graph. A field-level change triggers an actual, bounded Relate Cypher traversal that returns the potentially affected outputs and the path from the changed asset to each output. The explanations come from `why` on the graph relationships, not a text generator.

**The surprise:** A lab changes the representation of `moisture_pct`. The dry-mass calculation feeds both payable kilograms in FinanceMart and the activity denominator of ClimateMart's Scope 3 intensity metric. The same field can therefore affect a supplier settlement and sustainability dashboard. A contrast scenario, changing the unrelated `field_id`, reaches yield reporting but **not** finance or ESG: scope edges are directional, so unrelated siblings are not falsely implicated.

**How Relate is essential:** The backend uses `relate.connect()` to write and reopen a genuine embedded, single-file graph at `data/sample.rl`. Nodes and `FLOWS_TO` relationships are created with parameterized Cypher; shortest-first bounded upstream and downstream path queries execute **inside Relate**, returning path nodes and relationships. The UI renders these returned paths, and an impact receipt can be attached to a PR. The optional `.mcp.json` connects agents via **Relate's own read-only MCP server** to the exact same file. No Neo4j server, API key or hosted database is needed.

**How to try it:** `git clone https://github.com/mhatipog/data-impact-graph && cd data-impact-graph && ./run.sh`, then open `http://127.0.0.1:8765`. Click the preset scenario, compare the ESG and payout routes, and export a Markdown receipt. Run `python -m unittest discover -s tests -v` in `.venv` to verify native Relate integration. All data is fictional.

**Technology:** Python standard-library HTTP server, `relate-db==1.0.1`, Cypher, SVG, vanilla JavaScript/CSS, optional Relate CLI MCP. AI coding assistance from ChatGPT was used during implementation, but inference is not part of the runtime experience. The implementation and data are Apache-2.0 licensed.

**Recorded video:** [99-second Playwright walkthrough](demo/data-impact-graph-demo.mp4) (generated on Oracle OCI from the real application; visual captions, no voiceover). [Live-app poster](demo/poster.png) · [actual downloaded receipt](demo/impact-review.md) · [verified capture manifest](demo/manifest.json).

**Remaining before Devpost submission:** upload/host the MP4 in whatever player Devpost accepts; attach its URL; review the video visually; join and publish the entry. The GitHub MP4 is real and public, but this draft is **not** a submitted Devpost entry.
