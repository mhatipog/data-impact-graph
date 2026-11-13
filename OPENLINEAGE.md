# Connect existing lineage with OpenLineage

Data Impact Graph does **not** inspect your warehouse or invent dependencies. It consumes lineage metadata already emitted by your platform's OpenLineage instrumentation, stores documented links in a local, persistent **Relate graph**, and makes them useful **before a schema or transformation change is merged**.

No Marquez, graph server, hosted account, AI service, or database credentials are necessary for this file-based integration.

## Getting events out of your data platform

For an OpenLineage **Python** producer configured for local file output, one supported transport configuration is:

```bash
export OPENLINEAGE__TRANSPORT='{"type":"file","log_file_path":"./lineage-events.jsonl","append":true}'
```

For a **Java/Spark** producer using the Java client, the corresponding `openlineage.yml` transport is:

```yaml
transport:
  type: file
  location: /tmp/lineage-events.jsonl
```

The OpenLineage Java file transport is mainly intended for local/testing environments; executor-local files on distributed Spark/YARN/Kubernetes workers may disappear or be inconsistent. For hosted or distributed jobs, collect the JSON events from your existing OpenLineage backend/transport and export a JSONL batch for this importer. Do not mount a shared append-only file across concurrent workers.

See the [Python transport configuration](https://openlineage.io/docs/client/python/configuration/) and [Java/Spark transport configuration](https://openlineage.io/docs/client/java/configuration/) for producer-specific options.

## Five-minute walkthrough

Install the project's normal Python dependencies, then ingest the included **fictional but real-format** OpenLineage events. They represent five completed transformations: lab normalization, dry mass, supplier settlements, Scope 3 intensity, and field yield.

```bash
./run.sh --help    # optional: creates a virtualenv
. .venv/bin/activate
python -m data_impact_graph import openlineage examples/openlineage-events.jsonl \
  --store data/openlineage.rl
python -m data_impact_graph serve --store data/openlineage.rl
```

Visit <http://127.0.0.1:8765>. The imported graph opens on a connected source field, not the hard-coded synthetic presets. Search for `moisture_pct`, click the dependency route to either settlement or carbon intensity, and export the Markdown review receipt. Your unmodified sample remains available in `data/sample.rl`.

**Real events:** configure an existing OpenLineage producer (for example Spark, Airflow or dbt, where supported) to write JSON events to a file or collect its emitted JSON payloads, then import that file in the same way. Files may contain a single RunEvent / DatasetEvent / JobEvent, a JSON array, `{"events":[...]}`, or one JSON object per line (JSONL). The importer is **offline**; it does not reach into Fabric, Databricks or any production system. There is no live OpenLineage HTTP collector in this release.

## Incremental updates and CLI

```bash
python -m data_impact_graph import-openlineage runs-2026-11-13.jsonl \
  --store data/openlineage.rl

# Repeat with tomorrow's events. Latest observations per job/output win.
python -m data_impact_graph import-openlineage runs-2026-11-14.jsonl \
  --store data/openlineage.rl

# Restart cleanly only if you explicitly intend to discard prior observations.
python -m data_impact_graph import-openlineage events.jsonl \
  --store data/openlineage.rl --replace

python -m data_impact_graph overview --store data/openlineage.rl
python -m data_impact_graph report ASSET_ID --store data/openlineage.rl \
  --change "change this source column's units"
```

On repeated imports, a duplicate batch is a no-op and an older observation cannot replace a newer one. Each completed job/output or DatasetEvent lineage snapshot is independently versioned by `eventTime`, so a later run can replace outdated edges without accumulating obsolete mappings. A persistent `OpenLineageState` node inside the **same Relate file** records the minimal normalized snapshot, avoiding a separately coordinated sidecar. New graphs are assembled in a temporary Relate file and atomically replaced, while readers continue to see the previous valid graph. Parallel importers are serialized with a local file lock.

## Exact mappings only, no false confidence

OpenLineage `inputs[]` and `outputs[]` identify datasets at a job boundary. A job that reads inputs A and B and writes outputs X and Y **does not** prove four A/B → X/Y dependencies. In Data Impact Graph, these entities appear in the inventory, but no `FLOWS_TO` edge is asserted without explicit lineage.

Supported sources of **explicit** edges:

- **Column Lineage Dataset Facet:** `output.facets.columnLineage.fields[outputColumn].inputFields[]`; preserves DIRECT/INDIRECT transformation notes. `columnLineage.dataset[]` adds dataset-wide impacts such as filters and joins when supplied.
- **Lineage Job Facet:** `job.facets.lineage.entries[]`, where each target names its real inputs and optionally its output-field sources. These per-target mappings take precedence over legacy `columnLineage` for the same target.
- **Lineage Dataset Facet:** `dataset.facets.lineage.inputs[]` and `fields` for declared catalog/view dependencies in DatasetEvents.

Schema Dataset Facets become dataset → field **scope** edges (one-way). This allows a table-level change to include its fields while preventing an individual column from contaminating unrelated sibling columns. Unknown mappings remain unknown; they are **not** treated as proof that an asset is unaffected.

Only successful `COMPLETE` RunEvents change job-observed lineage; `START`, `RUNNING`, `FAIL`, and `ABORT` do not overwrite confirmed paths. Declared lineage on standalone DatasetEvents and JobEvents is supported. Job identities, dataset namespaces and column names are maintained distinctly, including when different platforms use the same short table name. The exact producer/job and transformation details are carried in edge explanations and provenance.

## What the import cannot establish

This is a **data lineage** integration. OpenLineage does not by itself give us complete Power BI semantic models, Fabric relationships, business ownership or a full enterprise metadata catalog. A downstream table or field is not automatically a dashboard or business KPI. The explorer calls such outputs *connected data assets*, rather than inventing dashboards.

The importer cannot prove a code change will actually fail, infer dependencies omitted by producers, or know the meaning of every field transformation. An OpenLineage job that emits dataset-only boundary metadata will display unconnected inventory until richer lineage is supplied.

**Current limits:** one local store per import collection; 32 MiB per input file, 20,000 events per batch, 30,000 assets and 60,000 unique edges per graph. Native impact queries remain bounded to 12 hops and 600 paths; graph overview is a preview limited to 2,000 assets and 4,000 edges. Import rejects cycles rather than returning misleading traversal results. The importer is intended for controlled local/event-batch use, not an always-on enterprise lineage backend.

For sensitive internal metadata, keep the `.rl` file private. It can contain object names, schemas, producer identities and transformation descriptions. Do not commit your company's lineage to a public repository.

## Format reference

- [OpenLineage core specification](https://openlineage.io/docs/spec/object-model/)
- [Column Lineage Dataset Facet](https://openlineage.io/docs/spec/facets/dataset-facets/column_lineage_facet/)
- [Lineage Job Facet](https://openlineage.io/docs/spec/facets/job-facets/lineage/)
- [Lineage Dataset Facet](https://openlineage.io/docs/spec/facets/dataset-facets/lineage/)

The importer intentionally validates the subset it supports, rather than claiming to validate the entire OpenLineage JSON Schema. It never evaluates embedded SQL or other producer-supplied code.
