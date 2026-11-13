# 90-second demo script

**0:00–0:12 — The question.** “A lab changes `moisture_pct` from percent to fraction. You would expect a quality-report impact. But who else depends on it?” Show the left-hand search and default scenario.

**0:12–0:30 — The graph.** “This isn't a mocked network diagram. Relate is an embedded, persistent Cypher graph. Nodes cover source fields, rules, transformations, models and dashboards. These edges represent real metadata dependencies.” Pan through the default highlighted path.

**0:30–0:57 — The reveal.** Select **Supplier payout forecast**, then **CO2e per dry tonne** and **Scope 3 assurance**. “The same dry-mass adjustment changes payable kilograms *and* the carbon-intensity denominator. One lab field crosses FinanceMart and ClimateMart.” Show the right-side step-by-step evidence.

**0:57–1:12 — Precision.** Search `gross_kg` or switch to upstream from **CO2e per dry tonne**. “Column-level propagation avoids false positives from unrelated sibling columns. Reverse traversal identifies the exact source fields and policy rules.”

**1:12–1:30 — Reproducibility.** Show terminal:

```bash
python -m data_impact_graph impact lab.assays.moisture_pct
relate --database data/sample.rl --read-only "MATCH (n:Asset) RETURN count(n) AS nodes"
```

“Clone, run one command, and inspect the graph file. No account or server needed.” End on the graph and GitHub URL.
