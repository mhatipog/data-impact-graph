# Before the Merge — OpenLineage-to-Relate hackathon film

**Watch:** [1:46 MP4](demo/data-impact-graph-openlineage-film.mp4) · [10-scene preview](demo/openlineage-film-contact-sheet.png) · [Narration captions](demo/data-impact-graph-openlineage-film.srt) · [Verified media manifest](demo/openlineage-film-manifest.json).

The hook is **when**, not how many nodes: a developer is reviewing a proposed laboratory-column change. Existing OpenLineage metadata becomes a local, persistent Relate graph; native Cypher paths reveal documented downstream financial and carbon-intensity fields **before** the proposed change is merged. A narrower unrelated field is contrasted, and a Markdown impact receipt carries the evidence into code review.

## Authentic source material

1. [Instrumented SQLite pipeline](scripts/instrumented-pipeline.py) executes five real SQL transformations over **fictional** lot records. SQLGlot reads the actual SELECT expressions to identify input-field → output-field dependencies. This is not presented as a connected corporate Fabric, Airflow, Spark or Databricks instance.
2. The **official OpenLineage Python SDK** emits ten events (START and COMPLETE) through its FileTransport, including schema and columnLineage facets. See the [SDK-written JSONL](examples/openlineage-sdk-emitted.jsonl) and [execution proof](demo/openlineage-sdk-run-proof.json).
3. The OpenLineage CLI import writes a **native, persistent Relate .rl graph**. Replaying the same event batch verifies that imports are idempotent.
4. [Playwright](scripts/capture-openlineage-film.mjs) loads the actual local explorer and verifies downstream routes from moisture_pct to payout_eur and co2e_per_dry_tonne, plus the unrelated field_id contrast. It **downloads the actual Markdown receipt** from the application. See [unedited browser-capture contact sheet](demo/openlineage-browser-contact-sheet.png).
5. The [film editor](scripts/render-openlineage-film.py) combines these real browser captures with overtly editorial graphics, English neural narration and an [original procedurally composed soundtrack](scripts/original-story-score.py). No stock clips, sample loops or third-party recordings are used.

Neither the product nor the video claims that every dependency is known, that a proposed change will necessarily fail, or that a missing path guarantees safety.

## Reproduce from source

On Linux with Python 3.12, Node.js, FFmpeg and system fonts, run:

    python -m pip install -r requirements.txt -r requirements-video.txt -r requirements-hackathon-video.txt
    npm install --no-save playwright@1.56.1
    npx playwright install chromium

    python scripts/instrumented-pipeline.py --out demo/film-working
    python -m data_impact_graph import openlineage demo/film-working/instrumented-openlineage.jsonl --store demo/film-working/imported.rl
    python -m data_impact_graph serve --store demo/film-working/imported.rl --port 8765 &
    SERVER_PID=$!
    node scripts/capture-openlineage-film.mjs demo/film-working
    kill "$SERVER_PID"
    python scripts/render-openlineage-film.py --work demo/film-working

Neural voice synthesis requires network access; it fails rather than silently degrading voice quality. Music synthesis uses local NumPy and code-owned instruments. The [public GitHub Actions workflow](.github/workflows/produce-hackathon-film.yml) executes this chain and verifies the MP4 without uploading Actions artifacts.

The final manifest records duration, H.264/AAC stream checks, decoded frames, audio-volume checks, source-event checksum, and output SHA-256. The ten-frame preview is extracted from the finished film, not a pre-rendered mockup.

Earlier technical recordings and cuts are preserved. This video is intended as the primary submission demo; Devpost submission is a separate action.
