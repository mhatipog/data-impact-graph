# Data Impact Graph — demo films and evidence

**Primary hackathon film:** [1:46 Before the Merge — OpenLineage → Relate → impact review](demo/data-impact-graph-openlineage-film.mp4) · [10-scene frame review](demo/openlineage-film-contact-sheet.png) · [captions](demo/data-impact-graph-openlineage-film.srt) · [render manifest](demo/openlineage-film-manifest.json).

This is an edited mini-film from **real executed SQL**, OpenLineage events emitted by the **official SDK**, a **native embedded Relate graph**, **real Playwright screenshots** and the **actual exported Markdown impact receipt**. Original procedural music and English neural narration accompany the story. Fictional sample lots are used; no corporate platform is claimed.

Read [FILM.md](FILM.md) to reproduce all events, UI captures and the final video. The [executed producer proof](demo/openlineage-sdk-run-proof.json) and [SDK-generated event file](examples/openlineage-sdk-emitted.jsonl) support the technical claims.

**Previous 83-second story cut:** [MP4](demo/data-impact-graph-story.mp4) · [preview](demo/story-contact-sheet.png) · [manifest](demo/story-manifest.json). Retained for comparison; it predates OpenLineage ingestion.

## Original continuous technical capture and storyboard

**Recorded MP4:** [demo/data-impact-graph-demo.mp4](demo/data-impact-graph-demo.mp4) · [Capture manifest](demo/manifest.json) · [Automated Playwright source](scripts/record-demo.mjs).

The verified 99.29-second capture was made on an Oracle ARM64 self-hosted runner against the real Relate graph; captions replace narration. The timings below are approximate scene targets, not proof of exact cut times.

Film a **real local run** after cloning (Relate is the backend). A screen capture with narration is enough; no proprietary data, logins or cloud services. Use a 1440px-wide browser and keep the evidence panel visible.

**0:00–0:12 — The engineering question.** “A lab changes `moisture_pct` from 0–100 to 0–1. The obvious risk is a quality report. But a column can quietly change what your business pays and reports to regulators.” Show the preset scenario.

**0:12–0:32 — The surprising route.** “This eight-node chain comes from a real, embedded Relate Cypher traversal, not a drawn demo graph.” Follow the **Selected route** from *moisture_pct* through assay normalization and dry-mass calculation to *Scope 3 assurance*. Pause on the explicit `dry_tonnes` denominator and explain why it matters.

**0:32–0:49 — Business consequences.** Click *Supplier payout forecast*, *CO2e per dry tonne*, then *Scope 3 assurance*. “One moisture ratio crosses FinanceMart and ClimateMart. Click any output to see the exact chain and the reason behind every dependency.” Switch briefly to **Impact map** to demonstrate the larger blast radius.

**0:49–1:02 — Fewer false positives.** Choose the **A narrower field change** scenario. “A change to the field identifier affects field productivity, but it should not falsely implicate supplier payout. Column dependencies keep this precise.”

**1:02–1:17 — Produce an engineer’s artifact.** Return to the moisture scenario; type `percent 0-100 to fraction 0-1` in the proposed-change box and click **Download impact receipt**. Open the Markdown receipt with the source-to-output route, annotated with the `why` recorded on each native Relate relationship.

**1:17–1:30 — Persisted graph + agent access.** Show `data/sample.rl` in the GitHub repo and a terminal:

```bash
python -m data_impact_graph impact lab.assays.moisture_pct
relate --database data/sample.rl --read-only "MATCH (n:Asset) RETURN count(n) AS nodes"
```

“Clone once, run locally, inspect one file. Agents can ask the same graph through Relate’s read-only MCP server.” Finish on the application and public repository URL.

Do not claim the sample is a production catalog, that these dependencies prove runtime failure, or that the optional MCP mode was tested unless separately verified. The actual MP4 is committed publicly under `demo/`. Devpost may still require uploading it to a supported video host and adding its URL to the submission.
