# Data Impact Graph — Relate by Neo4j Hackathon submission draft

**Tagline:** Before you change the data, know what depends on it.

## Problem

A data engineer plans a minor schema or unit change. Their pipeline may continue running, but the engineer still needs to know which downstream transformations, finance fields, or sustainability outputs rely on that column. Existing lineage instrumentation can collect the relationships; it doesn't automatically make them easy to investigate at code-review time.

## What the project does

Data Impact Graph imports OpenLineage event JSON/JSONL from an existing producer into a **persistent single-file Relate graph**. Select a table or column to see documented upstream/downstream dependencies, including actual source-to-output paths and each relationship's recorded explanation. Export a Markdown impact receipt that reviewers can attach to a pull request.

A column-aware graph prevents unrelated sibling fields from automatically being treated as affected. If a producer emits only input/output datasets without explicit mappings, those appear in the inventory, not as invented data-flow edges. Missing lineage is explicitly not proof of safety.

## Meaningful use of Relate

The native Python backend uses relate.connect() to write and reopen the persistent Relate .rl file. Asset nodes and FLOWS_TO relationships are created with parameterized Cypher; bounded variable-length upstream and downstream path traversals execute **inside Relate**, not in a separately reimplemented Python graph. The actual returned relationship properties supply the impact explanations and review receipts.

No remote graph server, Neo4j Aura service, credentials, or LLM API is necessary. The repository also includes the **native read-only Relate MCP server** project configuration so an agent can inspect the same file when explicitly enabled.

## New OpenLineage integration

The importer accepts explicit OpenLineage Column Lineage Dataset, Job Lineage and Dataset Lineage facets. It supports stable namespace-scoped identities, replay-idempotent incremental imports, source provenance, and atomic store replacement. It avoids asserting every job input feeds every job output.

For the film, a **real, instrumented local SQLite pipeline** executes five transformations over fictional lot records. SQLGlot derives the field mappings from the executed queries, and the official OpenLineage Python SDK emits ten events with schema and columnLineage facets. Importing those real-format events into Relate reveals:

- moisture_pct → moisture_ratio → dry_kg → payout_eur
- moisture_pct → moisture_ratio → dry_kg → co2e_per_dry_tonne

The field_id control illustrates a narrower dependency scope. The application exports a genuine Markdown impact receipt from the graph.

This is a live, reproducible local demonstration with **fictional data**, not a claimed automatic connection to a customer's Fabric, Databricks or Spark installation. There is not yet a live OpenLineage HTTP collector or automated GitHub merge blocker.

## Try it

Clone https://github.com/mhatipog/data-impact-graph and run ./run.sh to open the included persistent example graph. The public repository includes a one-command import example in OPENLINEAGE.md, and the instrumented producer plus exact video reproduction steps in FILM.md. Run python -m unittest discover -s tests -v to verify native Relate behavior.

## Demo and source evidence

**Primary video (1:46, with original soundtrack and neural narration):** [Before the Merge](demo/data-impact-graph-openlineage-film.mp4)

[Ten-scene review](demo/openlineage-film-contact-sheet.png) · [Captions](demo/data-impact-graph-openlineage-film.srt) · [Media validation manifest](demo/openlineage-film-manifest.json) · [SDK-emitted source events](examples/openlineage-sdk-emitted.jsonl) · [SQL execution proof](demo/openlineage-sdk-run-proof.json) · [Playwright browser frames](demo/openlineage-browser-contact-sheet.png).

The original 99-second uninterrupted technical capture is retained at demo/data-impact-graph-demo.mp4. The new edited film does not use any third-party music loops, stock footage or downloaded logos.

## Technology and attribution

Apache-2.0 project. Relate 1.0.1, Python, Cypher, OpenLineage Python SDK, SQLGlot, SQLite, HTML/SVG/vanilla JavaScript, Playwright, FFmpeg, Pillow, NumPy and Microsoft Edge neural TTS. The soundtrack is original procedural music generated from code. ChatGPT assisted with product design, software implementation, QA and editing; the running application does not rely on an LLM to answer lineage queries.

**Remaining Devpost steps:** join the challenge, place the public MP4 on an accepted accessible player if required by Devpost, paste the public repository link, add screenshots, and publish the entry. This draft does not itself constitute a submitted entry.
