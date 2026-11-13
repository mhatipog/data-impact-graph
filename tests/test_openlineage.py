"""Native Relate integration tests for OpenLineage ingestion. No mocked graph."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from data_impact_graph.core import impact, overview, receipt
from data_impact_graph.openlineage import _ident, import_openlineage

NS = "postgresql://warehouse"
JOB = "airflow://orchestrator"


def dataset(name, fields=None, column_lineage=None, lineage=None):
    facets = {}
    if fields is not None:
        facets["schema"] = {"fields": [{"name": x, "type": "string"} for x in fields]}
    if column_lineage is not None:
        facets["columnLineage"] = column_lineage
    if lineage is not None:
        facets["lineage"] = lineage
    return {"namespace": NS, "name": name, "facets": facets}


def field(source, name):
    return {"namespace": NS, "name": source, "field": name,
            "transformations": [{"type": "DIRECT", "subtype": "TRANSFORMATION"}]}


def event(name, inputs, outputs, day="2026-11-01T00:00:00Z", kind="COMPLETE"):
    return {"eventType": kind, "eventTime": day,
            "run": {"runId": "caf09518-5050-408c-b733-5c18c8452e52"},
            "job": {"namespace": JOB, "name": name},
            "inputs": inputs, "outputs": outputs}


def mapped(name, inp, output, col, source_col, day="2026-11-01T00:00:00Z"):
    return event(name,
                 [dataset(inp, [source_col, "unrelated"])],
                 [dataset(output, [col, "other"],
                          {"fields": {col: {"inputFields": [field(inp, source_col)]}}})],
                 day=day)


class OpenLineageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Path(self.tmp.name) / "imported.rl"
        self.file = Path(self.tmp.name) / "events.json"

    def tearDown(self):
        self.tmp.cleanup()

    def ingest(self, events, path=None, **kwargs):
        file = path or self.file
        file.write_text(json.dumps(events), encoding="utf-8")
        return import_openlineage(file, self.store, **kwargs)

    def test_native_column_paths_and_report(self):
        events = [
            mapped("normalize", "raw.assays", "stage.assays", "ratio", "moisture_pct"),
            mapped("dry_mass", "stage.assays", "core.mass", "dry_kg", "ratio"),
            mapped("payouts", "core.mass", "marts.payouts", "payable_kg", "dry_kg"),
            mapped("carbon", "core.mass", "marts.scope3", "intensity", "dry_kg"),
        ]
        result = self.ingest(events)
        self.assertEqual(result["accepted"], 4)
        self.assertGreater(result["flows"], 8)
        graph = overview(self.store)
        self.assertEqual(graph["source"], "openlineage")
        src = _ident("col", NS, "raw.assays", "moisture_pct")
        payouts = _ident("col", NS, "marts.payouts", "payable_kg")
        carbon = _ident("col", NS, "marts.scope3", "intensity")
        other = _ident("col", NS, "raw.assays", "unrelated")
        view = impact(src, store_path=self.store)
        ids = {x["id"] for x in view["affected"]}
        self.assertIn(payouts, ids)
        self.assertIn(carbon, ids)
        self.assertNotIn(other, ids)
        self.assertEqual(view["output_count"], 0)  # dataset fields, not BI metrics
        reverse = {x["id"] for x in impact(carbon, "upstream", self.store)["affected"]}
        self.assertIn(src, reverse)
        report = receipt(src, store_path=self.store, change="percent -> ratio")
        self.assertIn("Downstream datasets and fields", report)
        self.assertIn("OpenLineage columnLineage", report)
        self.assertIn("percent -> ratio", report)
        self.assertIn("Potential impact", report)

    def test_ambiguous_job_io_never_creates_cartesian_edges(self):
        explicitly = mapped("declared", "raw.a", "marts.a", "out", "a")
        ambiguous = event("ambiguous", [dataset("raw.a"), dataset("raw.b")],
                          [dataset("marts.x"), dataset("marts.y")])
        self.ingest([explicitly, ambiguous])
        view = impact(_ident("col", NS, "raw.a", "a"), store_path=self.store)
        ids = {x["id"] for x in view["affected"]}
        self.assertIn(_ident("col", NS, "marts.a", "out"), ids)
        self.assertNotIn(_ident("ds", NS, "marts.x"), ids)
        self.assertNotIn(_ident("ds", NS, "marts.y"), ids)

    def test_explicit_job_lineage_is_target_scoped(self):
        fact = event("multioutput",
                     [dataset("raw.customer"), dataset("raw.order")],
                     [dataset("marts.customers"), dataset("marts.orders")])
        fact["job"]["facets"] = {"lineage": {"entries": [
            {"type": "DATASET", "namespace": NS, "name": "marts.customers",
             "inputs": [{"type": "DATASET", "namespace": NS, "name": "raw.customer"}]},
            {"type": "DATASET", "namespace": NS, "name": "marts.orders",
             "inputs": [{"type": "DATASET", "namespace": NS, "name": "raw.order"}]}
        ]}}
        self.ingest([fact])
        source = _ident("ds", NS, "raw.customer")
        ids = {a["id"] for a in impact(source, store_path=self.store)["affected"]}
        self.assertIn(_ident("ds", NS, "marts.customers"), ids)
        self.assertNotIn(_ident("ds", NS, "marts.orders"), ids)
        self.assertIn("Explicit dataset lineage", receipt(source, store_path=self.store))

    def test_dataset_event_lineage_and_schema(self):
        ev = {"eventTime": "2026-11-01T00:00:00Z",
              "dataset": dataset("view.customer_summary", ["id", "score"],
                                 lineage={"inputs": [{"type": "DATASET", "namespace": NS,
                                                     "name": "raw.customers"}],
                                          "fields": {"id": {"inputs": [
                                              {"type": "DATASET", "namespace": NS,
                                               "name": "raw.customers", "field": "customer_id"}
                                          ]}}})}
        self.ingest([ev])
        s = _ident("col", NS, "raw.customers", "customer_id")
        d = _ident("col", NS, "view.customer_summary", "id")
        self.assertIn(d, {x["id"] for x in impact(s, store_path=self.store)["affected"]})
        self.assertIn(_ident("ds", NS, "view.customer_summary"),
                      {x["id"] for x in impact(_ident("ds", NS, "raw.customers"),
                                               store_path=self.store)["affected"]})

    def test_latest_snapshot_replaces_old_edges_and_replay_is_idempotent(self):
        initial = mapped("job1", "raw.one", "marts.result", "value", "first")
        state = self.ingest([initial])
        self.assertFalse(state["unchanged"])
        second = mapped("job1", "raw.two", "marts.result", "value", "second",
                        day="2026-11-02T00:00:00Z")
        state = self.ingest([second])
        self.assertGreaterEqual(state["updated_snapshots"], 3)  # source, output and lineage
        self.assertTrue(state["flows"] >= 2)
        old = impact(_ident("col", NS, "raw.one", "first"), store_path=self.store)
        self.assertNotIn(_ident("col", NS, "marts.result", "value"),
                         {x["id"] for x in old["affected"]})
        new = impact(_ident("col", NS, "raw.two", "second"), store_path=self.store)
        self.assertIn(_ident("col", NS, "marts.result", "value"),
                      {x["id"] for x in new["affected"]})
        before = self.store.stat().st_mtime_ns
        same = self.ingest([second])
        self.assertTrue(same["unchanged"])
        self.assertEqual(before, self.store.stat().st_mtime_ns)
        stale = self.ingest([initial])
        self.assertTrue(stale["unchanged"])

    def test_failed_and_start_runs_do_not_replace_confirmed_lineage(self):
        original = mapped("source", "raw.known", "marts.result", "value", "source")
        self.ingest([original])
        bad = mapped("source", "raw.wrong", "marts.result", "value", "wrong",
                     day="2026-11-03T00:00:00Z")
        for kind in ("START", "FAIL", "ABORT"):
            bad["eventType"] = kind
            status = self.ingest([bad])
            self.assertEqual(status["ignored"], 1)
            self.assertTrue(status["unchanged"])
        view = impact(_ident("col", NS, "raw.known", "source"), store_path=self.store)
        self.assertIn(_ident("col", NS, "marts.result", "value"),
                      {x["id"] for x in view["affected"]})

    def test_jsonl_namespace_isolation_and_invalid_batch_is_atomic(self):
        first = mapped("jobs", "raw.one", "marts.report", "out", "id")
        other = copy.deepcopy(first)
        other["eventTime"] = "2026-11-02T00:00:00Z"
        other["job"]["namespace"] = "airflow://second-instance"
        other["inputs"][0]["namespace"] = "postgresql://other-server"
        other["outputs"][0]["facets"]["columnLineage"]["fields"]["out"]["inputFields"][0]["namespace"] = "postgresql://other-server"
        self.file.write_text("\n".join(json.dumps(x) for x in [first, other]) + "\n")
        status = import_openlineage(self.file, self.store)
        self.assertEqual(status["accepted"], 2)
        other_id = _ident("col", "postgresql://other-server", "raw.one", "id")
        self.assertIn(_ident("col", NS, "marts.report", "out"),
                      {x["id"] for x in impact(other_id, store_path=self.store)["affected"]})
        before = self.store.read_bytes()
        invalid = copy.deepcopy(first)
        invalid["eventTime"] = "tomorrow"
        with self.assertRaisesRegex(ValueError, "eventTime"):
            self.ingest([invalid])
        self.assertEqual(before, self.store.read_bytes())

    def test_cycles_rejected_without_destroying_previous_store(self):
        one = {"eventTime": "2026-11-01T00:00:00Z",
               "dataset": dataset("b", lineage={"inputs": [{"namespace": NS, "name": "a"}]})}
        two = {"eventTime": "2026-11-02T00:00:00Z",
               "dataset": dataset("a", lineage={"inputs": [{"namespace": NS, "name": "b"}]})}
        self.ingest([one])
        before = self.store.read_bytes()
        with self.assertRaisesRegex(ValueError, "cycle"):
            self.ingest([two])
        self.assertEqual(before, self.store.read_bytes())

    def test_does_not_overwrite_bundled_sample(self):
        from data_impact_graph.core import STORE
        self.file.write_text(json.dumps([mapped("one","raw","out","x","a")]))
        with self.assertRaisesRegex(ValueError, "synthetic"):
            import_openlineage(self.file, STORE, replace=True)


if __name__ == "__main__":
    unittest.main()
