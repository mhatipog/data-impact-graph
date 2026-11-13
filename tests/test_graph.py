"""Small integration suite. Requires the native Relate engine, not a mock."""
import json
import tempfile
import unittest
from pathlib import Path

from data_impact_graph.core import SAMPLE, impact, overview, receipt, seed, validate


class GraphTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Path(self.tmp.name) / "test.rl"
        seed(SAMPLE, self.store)

    def tearDown(self):
        self.tmp.cleanup()

    def test_persists_across_connections(self):
        one = overview(self.store)
        two = overview(self.store)
        self.assertEqual(len(one["assets"]), 49)
        self.assertEqual(len(one["flows"]), 60)
        self.assertEqual(one["assets"], two["assets"])
        self.assertGreater(self.store.stat().st_size, 0)

    def test_moisture_crosses_business_boundaries(self):
        result = impact("lab.assays.moisture_pct", store_path=self.store)
        outputs = {x["id"] for x in result["outputs"]}
        self.assertIn("metric.payout", outputs)
        self.assertIn("metric.carbon", outputs)
        self.assertIn("dash.exec", outputs)
        self.assertIn("dash.esg", outputs)
        carbon = next(x for x in result["outputs"] if x["id"] == "metric.carbon")
        self.assertTrue(any("climate.emissions.dry_tonnes" in p["ids"] for p in carbon["paths"]))
        self.assertGreaterEqual(len(result["systems"]), 3)

    def test_column_scope_does_not_leak_to_siblings(self):
        result = impact("lab.assays.moisture_pct", store_path=self.store)
        impacted = {x["id"] for x in result["affected"]}
        self.assertNotIn("lab.assays.lot_id", impacted)
        self.assertNotIn("metric.yield", impacted)
        self.assertNotIn("dash.field", impacted)

    def test_reverse_lineage_identifies_rules_and_sources(self):
        result = impact("metric.carbon", "upstream", self.store)
        assets = {x["id"] for x in result["affected"]}
        self.assertIn("rule.dry_mass", assets)
        self.assertIn("lab.assays.moisture_pct", assets)
        self.assertIn("fleet.shipments.distance_km", assets)

    def test_unknown_asset_is_explicit(self):
        with self.assertRaises(KeyError):
            impact("no.such.asset", store_path=self.store)

    def test_review_receipt_uses_real_edge_reasons(self):
        text = receipt("lab.assays.moisture_pct", store_path=self.store,
                       change="percentage to fraction")
        self.assertIn("Supplier payout forecast", text)
        self.assertIn("CO2e per dry tonne", text)
        self.assertIn("Scope 3 assurance", text)
        self.assertIn("Normalized moisture ratio changes dry mass", text)
        self.assertIn("percentage to fraction", text)
        self.assertNotIn("Harvest tonnes per hectare", text)
        self.assertIn("Potential impact, not a prediction of failure", text)

    def test_upstream_receipt_and_empty_output(self):
        reverse = receipt("metric.carbon", "upstream", self.store)
        self.assertIn(" ← ", reverse)
        self.assertIn("lab.assays.moisture_pct", reverse)
        empty = receipt("dash.field", store_path=self.store)
        self.assertIn("No connected business outputs were found", empty)
        with self.assertRaisesRegex(ValueError, "too long"):
            receipt("metric.carbon", store_path=self.store, change="x" * 241)

    def test_import_rejects_cycles(self):
        metadata = json.loads(SAMPLE.read_text())
        metadata["flows"].append({"from": "dash.exec", "to": "lab.assays.moisture_pct", "why": "invalid", "mode": "derive"})
        with self.assertRaisesRegex(ValueError, "cycle"):
            validate(metadata)


if __name__ == "__main__":
    unittest.main()
