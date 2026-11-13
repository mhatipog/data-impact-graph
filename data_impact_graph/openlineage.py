"""Conservative OpenLineage import into the *same embedded Relate engine*.

Run inputs/outputs are inventory, not a Cartesian-product dependency.
Only explicit OpenLineage lineage facets become FLOWS_TO edges.
The latest observation per owner/target replaces its earlier snapshot.
"""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import tempfile

import relate

from .core import ROOT, seed, validate

DEFAULT_STORE = ROOT / "data" / "openlineage.rl"
MAX_BYTES = 32 * 1024 * 1024
MAX_EVENTS = 20000
MAX_ASSETS = 30000
MAX_FLOWS = 60000
STATE_VERSION = 1


def _required(value, name):
    if not isinstance(value, str) or not value or len(value) > 2048:
        raise ValueError("%s must be a nonempty string (at most 2048 characters)" % name)
    return value


def _mapping(value, name):
    if not isinstance(value, dict):
        raise ValueError("%s must be an object" % name)
    return value


def _sequence(value, name):
    if not isinstance(value, list):
        raise ValueError("%s must be an array" % name)
    return value


def _ident(kind, namespace, name, field=None):
    namespace = _required(namespace, "namespace")
    name = _required(name, "name")
    identity = "\x00".join((namespace, name) if field is None else (namespace, name, _required(field, "field")))
    return "ol:%s:%s" % (kind, hashlib.sha256(identity.encode("utf-8")).hexdigest()[:32])


def _identity(node, name="entity"):
    node = _mapping(node, name)
    return (_required(node.get("namespace"), name + ".namespace"),
            _required(node.get("name"), name + ".name"))


def _time(event):
    stamp = _required(event.get("eventTime"), "eventTime")
    try:
        parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("eventTime must be an ISO-8601 timestamp with an offset")
    return parsed.timestamp()


def _fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


class _Graph:
    def __init__(self):
        self.assets = {}
        self.flows = {}

    def asset(self, kind, namespace, name, field=None):
        entity = "job" if kind == "JOB" else "ds"
        if kind not in ("JOB", "DATASET"):
            raise ValueError("Unsupported OpenLineage entity type: %s" % kind)
        ident = _ident(entity if field is None else "col", namespace, name, field)
        if field is not None:
            self.asset("DATASET", namespace, name)
            display = field
            node_kind = "Column"
            detail = "%s / %s #%s (OpenLineage)" % (namespace, name, field)
        else:
            display = name
            node_kind = "Transformation" if kind == "JOB" else "Table"
            detail = "%s / %s (OpenLineage)" % (namespace, name)
        self.assets[ident] = {"id": ident, "name": display[:240], "kind": node_kind,
                              "system": namespace[:240], "detail": detail[:1000], "risk": ""}
        if field is not None:
            self.flow(_ident("ds", namespace, name), ident,
                      "Dataset schema or field reference includes this column", "scope", "OpenLineage schema")
        return ident

    def flow(self, source, target, why, mode="derive", provenance=""):
        if source == target:
            return
        key = (source, target)
        self.flows[key] = {"from": source, "to": target, "why": why[:1000],
                           "mode": mode, "provenance": provenance[:1000]}

    def schema(self, dataset):
        namespace, name = _identity(dataset, "dataset")
        self.asset("DATASET", namespace, name)
        facets = dataset.get("facets") or {}
        _mapping(facets, "dataset.facets")
        schema = facets.get("schema")
        if schema is None:
            return None
        _mapping(schema, "dataset.facets.schema")
        for field in _sequence(schema.get("fields", []), "schema.fields"):
            self.asset("DATASET", namespace, name, _required(_mapping(field, "schema.field").get("name"), "schema.field.name"))
        return self.snapshot()

    def reference(self, source, default_type="DATASET"):
        source = _mapping(source, "lineage input")
        kind = source.get("type", default_type)
        if kind not in ("JOB", "DATASET"):
            raise ValueError("Unsupported lineage input type")
        namespace, name = _identity(source, "lineage input")
        field = source.get("field")
        if field is not None and kind != "DATASET":
            raise ValueError("Job fields are not supported")
        ident = self.asset(kind, namespace, name, field)
        return ident, namespace, name, field

    def _reason(self, source, label):
        transformations = source.get("transformations") or []
        if not isinstance(transformations, list):
            raise ValueError("transformations must be an array")
        descriptions = []
        for transform in transformations[:4]:
            transform = _mapping(transform, "transformation")
            text = " ".join(str(transform.get(k, "")) for k in ("type", "subtype", "description")).strip()
            if text:
                descriptions.append(text.replace("\n", " ")[:200])
        return (label + (": " + "; ".join(descriptions) if descriptions else ""))[:1000]

    def exact_lineage(self, target, inputs, fields, origin):
        target_id, ns, name, field = self.reference(target)
        if field is not None:
            raise ValueError("Lineage target must be a dataset or job, not a field")
        for item in _sequence(inputs, "lineage.inputs"):
            source_id, _, _, _ = self.reference(item)
            self.flow(source_id, target_id, self._reason(item, "Explicit dataset lineage"),
                      "derive", origin)
        for out_name, spec in _mapping(fields, "lineage.fields").items():
            if target.get("type", "DATASET") != "DATASET":
                raise ValueError("Field-level lineage requires a dataset target")
            output_id = self.asset("DATASET", ns, name, _required(out_name, "output field"))
            for item in _sequence(_mapping(spec, "lineage field").get("inputs", []), "lineage.fields.inputs"):
                source_id, _, _, _ = self.reference(item)
                self.flow(source_id, output_id, self._reason(item, "Explicit field lineage"),
                          "derive", origin)

    def column_lineage(self, dataset, facet, origin):
        namespace, name = _identity(dataset, "output")
        target = self.asset("DATASET", namespace, name)
        facet = _mapping(facet, "columnLineage")
        for col, rule in _mapping(facet.get("fields", {}), "columnLineage.fields").items():
            output_id = self.asset("DATASET", namespace, name, _required(col, "columnLineage output field"))
            for inp in _sequence(_mapping(rule, "columnLineage field").get("inputFields", []), "inputFields"):
                source_id, _, _, source_field = self.reference(inp)
                if source_field is None:
                    raise ValueError("columnLineage.inputFields requires a field")
                self.flow(source_id, output_id, self._reason(inp, "OpenLineage columnLineage"),
                          "derive", origin)
        for inp in _sequence(facet.get("dataset", []), "columnLineage.dataset"):
            source_id, _, _, source_field = self.reference(inp)
            if source_field is None:
                raise ValueError("columnLineage.dataset requires an input field")
            self.flow(source_id, target, self._reason(inp, "Dataset-wide dependency (filter/join/grouping)"),
                      "derive", origin)

    def snapshot(self):
        return {"assets": list(self.assets.values()), "flows": list(self.flows.values())}


def _events(path):
    path = Path(path)
    if not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise ValueError("OpenLineage input must be a file of at most 32 MiB")
    data = path.read_text(encoding="utf-8-sig")
    try:
        obj = json.loads(data)
    except json.JSONDecodeError:
        result = []
        for lineno, row in enumerate(data.splitlines(), 1):
            if not row.strip():
                continue
            try:
                result.append(json.loads(row))
            except json.JSONDecodeError as err:
                raise ValueError("Invalid JSONL at line %d: %s" % (lineno, err))
        obj = result
    if isinstance(obj, dict):
        obj = obj.get("events", [obj])
    result = _sequence(obj, "OpenLineage events")
    if not result or len(result) > MAX_EVENTS:
        raise ValueError("OpenLineage input must contain 1 to %d events" % MAX_EVENTS)
    return [_mapping(event, "OpenLineage event") for event in result]


def _record(state, key, timestamp, graph, digest):
    before = state["snapshots"].get(key)
    if before and (timestamp, digest) <= (before["timestamp"], before["digest"]):
        return False
    state["snapshots"][key] = {"timestamp": timestamp, "digest": digest, **graph.snapshot()}
    return True


def _normalize(event, state):
    timestamp = _time(event)
    if "run" in event:
        _mapping(event["run"], "run")
        _required(event["run"].get("runId"), "run.runId")
        if event.get("eventType") != "COMPLETE":
            return False, 0
        namespace, name = _identity(event.get("job"), "job")
        job_id = _ident("job", namespace, name)
        origin = "OpenLineage job %s/%s" % (namespace, name)
        inputs = _sequence(event.get("inputs", []), "inputs")
        outputs = _sequence(event.get("outputs", []), "outputs")
    elif "job" in event and "dataset" not in event:
        namespace, name = _identity(event.get("job"), "job")
        job_id = _ident("job", namespace, name)
        origin = "OpenLineage job %s/%s" % (namespace, name)
        inputs, outputs = [], []
    elif "dataset" in event:
        dataset = _mapping(event["dataset"], "dataset")
        namespace, name = _identity(dataset, "dataset")
        job_id, origin = None, "OpenLineage DatasetEvent %s/%s" % (namespace, name)
        inputs, outputs = [], [dataset]
    else:
        raise ValueError("OpenLineage event must be RunEvent, JobEvent or DatasetEvent")
    digest = _fingerprint(event)
    changed = 0
    for ds in inputs + outputs:
        _identity(ds, "dataset")
        facets = ds.get("facets") or {}
        if "schema" in _mapping(facets, "dataset.facets"):
            graph = _Graph()
            graph.schema(ds)
            key = "schema:" + _ident("ds", ds["namespace"], ds["name"])
            changed += int(_record(state, key, timestamp, graph, digest))
    if job_id is not None:
        # Only authoritative mappings are recorded. Bare inputs/outputs do not
        # establish pairwise flow dependencies, even for a single output.
        facet = _mapping(event["job"], "job").get("facets") or {}
        lineage = _mapping(facet, "job.facets").get("lineage")
        if lineage is not None:
            entries = _sequence(_mapping(lineage, "job.facets.lineage").get("entries", []), "lineage.entries")
            for entry in entries:
                entry = _mapping(entry, "lineage entry")
                type_name = entry.get("type", "DATASET")
                if type_name not in ("JOB", "DATASET"):
                    raise ValueError("Invalid lineage entry type")
                target = {"type": type_name, "namespace": entry.get("namespace"), "name": entry.get("name")}
                if type_name == "JOB" and not target["namespace"] and not target["name"]:
                    target = {"type": "JOB", "namespace": namespace, "name": name}
                graph = _Graph()
                graph.exact_lineage(target, entry.get("inputs", []), entry.get("fields", {}), origin + " (lineage facet)")
                target_id, _, _, _ = graph.reference(target)
                changed += int(_record(state, "flow:%s:%s" % (job_id, target_id),
                                       timestamp, graph, digest))
        # Legacy facet is per-output; modern job lineage supersedes it for
        # targets explicitly mentioned above.
        targets = set()
        if lineage is not None:
            for entry in lineage.get("entries", []):
                typ = entry.get("type", "DATASET")
                e_ns = entry.get("namespace") or namespace
                e_name = entry.get("name") or name
                targets.add(_ident("job" if typ == "JOB" else "ds", e_ns, e_name))
        for ds in outputs:
            ns, dsname = _identity(ds, "output")
            target_id = _ident("ds", ns, dsname)
            if target_id in targets:
                continue
            facets = _mapping(ds.get("facets") or {}, "output.facets")
            if "columnLineage" in facets:
                graph = _Graph()
                graph.column_lineage(ds, facets["columnLineage"], origin + " (columnLineage facet)")
                changed += int(_record(state, "flow:%s:%s" % (job_id, target_id),
                                       timestamp, graph, digest))
    # Standalone lineage is explicitly declared on the dataset, independent
    # of a producing job. It may coexist with job-owned lineage snapshots.
    if job_id is None:
        facets = _mapping(outputs[0].get("facets") or {}, "dataset.facets")
        lineage = facets.get("lineage")
        if lineage is not None:
            lineage = _mapping(lineage, "dataset.facets.lineage")
            graph = _Graph()
            graph.exact_lineage({"type": "DATASET", "namespace": namespace, "name": name},
                                lineage.get("inputs", []), lineage.get("fields", {}), origin)
            changed += int(_record(state, "datasetflow:" + _ident("ds", namespace, name),
                                   timestamp, graph, digest))
        elif "columnLineage" in facets:
            graph = _Graph()
            graph.column_lineage(outputs[0], facets["columnLineage"], origin)
            changed += int(_record(state, "datasetflow:" + _ident("ds", namespace, name),
                                   timestamp, graph, digest))
    return True, changed


def _materialize(state):
    assets, flows = {}, {}
    for snapshot in state["snapshots"].values():
        for asset in snapshot["assets"]:
            assets[asset["id"]] = asset
        for flow in snapshot["flows"]:
            key = (flow["from"], flow["to"])
            if key not in flows:
                flows[key] = flow.copy()
            elif flows[key]["provenance"] != flow["provenance"]:
                # Same dependency confirmed by multiple producers. Never
                # multiply edges or discard that independent provenance.
                original = flows[key]
                original["provenance"] = (original["provenance"] + "; " + flow["provenance"])[:1000]
    if len(assets) > MAX_ASSETS or len(flows) > MAX_FLOWS:
        raise ValueError("OpenLineage graph exceeds bounded import limits")
    meta = {"dataset": "Imported OpenLineage metadata",
            "assets": sorted(assets.values(), key=lambda a: a["id"]),
            "flows": sorted(flows.values(), key=lambda f: (f["from"], f["to"]))}
    validate(meta)
    return meta


def _read_state(store):
    with relate.connect(str(store), read_only=True) as db:
        row = db.execute("MATCH (s:OpenLineageState) RETURN s.payload AS payload").fetchone()
        if row is None:
            raise ValueError("Target graph is not an OpenLineage import; use another --store (do not overwrite the demo)")
        state = json.loads(row["payload"])
    if state.get("version") != STATE_VERSION or not isinstance(state.get("snapshots"), dict):
        raise ValueError("Unsupported OpenLineage store state version")
    return state


def import_openlineage(source, store_path=DEFAULT_STORE, *, replace=False):
    """Atomic snapshot import: no partially imported Relate graph is exposed.

    Existing snapshots are retained and replaced by timestamp per owner;
    repeated event batches are idempotent. Offline, no metadata service needed.
    """
    source, store = Path(source), Path(store_path)
    if store.resolve() == (ROOT / "data" / "sample.rl").resolve():
        raise ValueError("Refusing to replace the bundled synthetic example graph")
    events = _events(source)
    store.parent.mkdir(parents=True, exist_ok=True)
    # The lock serializes concurrent importers, so their state snapshots cannot
    # race. Readers continue using the previous fully committed graph.
    import fcntl
    with (store.parent / (store.name + ".lock")).open("a+b") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if store.exists() and not replace:
            state = _read_state(store)
        else:
            state = {"version": STATE_VERSION, "snapshots": {}}
        seen, skipped, updates = 0, 0, 0
        for event in sorted(events, key=_time):
            accepted, changed = _normalize(event, state)
            seen += int(accepted)
            skipped += int(not accepted)
            updates += changed
        if updates == 0 and store.exists() and not replace:
            meta = _materialize(state)
            return {"store": str(store), "events": len(events), "accepted": seen,
                    "ignored": skipped, "updated_snapshots": 0,
                    "assets": len(meta["assets"]), "flows": len(meta["flows"]),
                    "unchanged": True}
        meta = _materialize(state)
        with tempfile.TemporaryDirectory(prefix=".openlineage-", dir=store.parent) as temp:
            temp = Path(temp)
            metadata_file = temp / "metadata.json"
            candidate = temp / "candidate.rl"
            metadata_file.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
            seed(metadata_file, candidate)
            with relate.connect(str(candidate)) as db:
                db.execute("CREATE (:OpenLineageState {payload: $payload})",
                           {"payload": json.dumps(state, separators=(",", ":"), ensure_ascii=False)})
            os.replace(candidate, store)
        return {"store": str(store), "events": len(events), "accepted": seen,
                "ignored": skipped, "updated_snapshots": updates,
                "assets": len(meta["assets"]), "flows": len(meta["flows"]),
                "unchanged": False}
