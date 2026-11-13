# Data impact review: moisture_pct

- Asset: `lab.assays.moisture_pct` (Column, LabTrack)
- Direction: downstream
- Connected assets requiring review: 19
- Business outputs requiring review: 7
- Impacted systems: BoardBI, ClimateMart, FinanceMart, LabTrack
- Proposed change (user-supplied): moisture_pct: percentage 0–100 becomes fraction 0–1

> Potential impact, not a prediction of failure. Only documented metadata dependencies
> are traversed; missing lineage can hide additional impacts.

## Affected business outputs

### Assay rejection rate — Metric in LabTrack
Shortest documented route: 3 hops

**Shortest Relate path:**

`lab.assays.moisture_pct` → `tx.quality` → `model.quality` → `metric.quality`

1. `lab.assays.moisture_pct` → `tx.quality` — Moisture measurement controls quality acceptance (`derive`)
2. `tx.quality` → `model.quality` — Acceptance flags are aggregated into exceptions (`publish`)
3. `model.quality` → `metric.quality` — Calculates acceptance and rejection rate (`aggregate`)

### Executive cockpit — Dashboard in BoardBI
Shortest documented route: 4 hops

**Shortest Relate path:**

`lab.assays.moisture_pct` → `tx.quality` → `model.quality` → `metric.quality` → `dash.exec`

1. `lab.assays.moisture_pct` → `tx.quality` — Moisture measurement controls quality acceptance (`derive`)
2. `tx.quality` → `model.quality` — Acceptance flags are aggregated into exceptions (`publish`)
3. `model.quality` → `metric.quality` — Calculates acceptance and rejection rate (`aggregate`)
4. `metric.quality` → `dash.exec` — Executive board renders quality exceptions (`publish`)

**Alternative Relate path:**

`lab.assays.moisture_pct` → `tx.normalize_assay` → `tx.dry_mass` → `climate.emissions.dry_tonnes` → `tx.emissions` → `model.scope3` → `metric.carbon` → `dash.exec`

1. `lab.assays.moisture_pct` → `tx.normalize_assay` — Assay ratio is read as the dry-mass adjustment input (`derive`)
2. `tx.normalize_assay` → `tx.dry_mass` — Normalized moisture ratio changes dry mass (`derive`)
3. `tx.dry_mass` → `climate.emissions.dry_tonnes` — Same dry-mass calculation also feeds climate accounting (`derive`)
4. `climate.emissions.dry_tonnes` → `tx.emissions` — Dry tonnes form the emissions-intensity denominator (`derive`)
5. `tx.emissions` → `model.scope3` — Carbon intensity transformation feeds scope 3 model (`publish`)
6. `model.scope3` → `metric.carbon` — Calculates emissions intensity by period (`aggregate`)
7. `metric.carbon` → `dash.exec` — Executive board renders Scope 3 intensity (`publish`)

### Supplier payout forecast — Metric in FinanceMart
Shortest documented route: 5 hops

**Shortest Relate path:**

`lab.assays.moisture_pct` → `tx.normalize_assay` → `tx.dry_mass` → `finance.settlement.payable_kg` → `model.settlement` → `metric.payout`

1. `lab.assays.moisture_pct` → `tx.normalize_assay` — Assay ratio is read as the dry-mass adjustment input (`derive`)
2. `tx.normalize_assay` → `tx.dry_mass` — Normalized moisture ratio changes dry mass (`derive`)
3. `tx.dry_mass` → `finance.settlement.payable_kg` — Computed payable dry kilograms are materialized (`derive`)
4. `finance.settlement.payable_kg` → `model.settlement` — Settlement model exposes payable dry kilograms (`publish`)
5. `model.settlement` → `metric.payout` — Aggregates payables per settlement period (`aggregate`)

**Alternative Relate path:**

`lab.assays.moisture_pct` → `tx.normalize_assay` → `tx.dry_mass` → `finance.settlement.payable_kg` → `tx.payout` → `finance.settlement.payout_eur` → `model.settlement` → `metric.payout`

1. `lab.assays.moisture_pct` → `tx.normalize_assay` — Assay ratio is read as the dry-mass adjustment input (`derive`)
2. `tx.normalize_assay` → `tx.dry_mass` — Normalized moisture ratio changes dry mass (`derive`)
3. `tx.dry_mass` → `finance.settlement.payable_kg` — Computed payable dry kilograms are materialized (`derive`)
4. `finance.settlement.payable_kg` → `tx.payout` — Dry kilograms set the supplier settlement volume (`derive`)
5. `tx.payout` → `finance.settlement.payout_eur` — Settlement transaction stores computed payout (`derive`)
6. `finance.settlement.payout_eur` → `model.settlement` — Settlement model includes payout amounts (`publish`)
7. `model.settlement` → `metric.payout` — Aggregates payables per settlement period (`aggregate`)

### CO2e per dry tonne — Metric in ClimateMart
Shortest documented route: 6 hops

**Shortest Relate path:**

`lab.assays.moisture_pct` → `tx.normalize_assay` → `tx.dry_mass` → `climate.emissions.dry_tonnes` → `tx.emissions` → `model.scope3` → `metric.carbon`

1. `lab.assays.moisture_pct` → `tx.normalize_assay` — Assay ratio is read as the dry-mass adjustment input (`derive`)
2. `tx.normalize_assay` → `tx.dry_mass` — Normalized moisture ratio changes dry mass (`derive`)
3. `tx.dry_mass` → `climate.emissions.dry_tonnes` — Same dry-mass calculation also feeds climate accounting (`derive`)
4. `climate.emissions.dry_tonnes` → `tx.emissions` — Dry tonnes form the emissions-intensity denominator (`derive`)
5. `tx.emissions` → `model.scope3` — Carbon intensity transformation feeds scope 3 model (`publish`)
6. `model.scope3` → `metric.carbon` — Calculates emissions intensity by period (`aggregate`)

### Supplier 360 — Dashboard in BoardBI
Shortest documented route: 6 hops

**Shortest Relate path:**

`lab.assays.moisture_pct` → `tx.normalize_assay` → `tx.dry_mass` → `finance.settlement.payable_kg` → `model.settlement` → `metric.payout` → `dash.supplier`

1. `lab.assays.moisture_pct` → `tx.normalize_assay` — Assay ratio is read as the dry-mass adjustment input (`derive`)
2. `tx.normalize_assay` → `tx.dry_mass` — Normalized moisture ratio changes dry mass (`derive`)
3. `tx.dry_mass` → `finance.settlement.payable_kg` — Computed payable dry kilograms are materialized (`derive`)
4. `finance.settlement.payable_kg` → `model.settlement` — Settlement model exposes payable dry kilograms (`publish`)
5. `model.settlement` → `metric.payout` — Aggregates payables per settlement period (`aggregate`)
6. `metric.payout` → `dash.supplier` — Supplier dashboard renders payout forecast (`publish`)

**Alternative Relate path:**

`lab.assays.moisture_pct` → `tx.normalize_assay` → `tx.dry_mass` → `finance.settlement.payable_kg` → `tx.payout` → `finance.settlement.payout_eur` → `model.settlement` → `metric.payout` → `dash.supplier`

1. `lab.assays.moisture_pct` → `tx.normalize_assay` — Assay ratio is read as the dry-mass adjustment input (`derive`)
2. `tx.normalize_assay` → `tx.dry_mass` — Normalized moisture ratio changes dry mass (`derive`)
3. `tx.dry_mass` → `finance.settlement.payable_kg` — Computed payable dry kilograms are materialized (`derive`)
4. `finance.settlement.payable_kg` → `tx.payout` — Dry kilograms set the supplier settlement volume (`derive`)
5. `tx.payout` → `finance.settlement.payout_eur` — Settlement transaction stores computed payout (`derive`)
6. `finance.settlement.payout_eur` → `model.settlement` — Settlement model includes payout amounts (`publish`)
7. `model.settlement` → `metric.payout` — Aggregates payables per settlement period (`aggregate`)
8. `metric.payout` → `dash.supplier` — Supplier dashboard renders payout forecast (`publish`)

### Contribution margin — Metric in BoardBI
Shortest documented route: 7 hops

**Shortest Relate path:**

`lab.assays.moisture_pct` → `tx.normalize_assay` → `tx.dry_mass` → `finance.settlement.payable_kg` → `tx.payout` → `finance.settlement.payout_eur` → `model.margin` → `metric.margin`

1. `lab.assays.moisture_pct` → `tx.normalize_assay` — Assay ratio is read as the dry-mass adjustment input (`derive`)
2. `tx.normalize_assay` → `tx.dry_mass` — Normalized moisture ratio changes dry mass (`derive`)
3. `tx.dry_mass` → `finance.settlement.payable_kg` — Computed payable dry kilograms are materialized (`derive`)
4. `finance.settlement.payable_kg` → `tx.payout` — Dry kilograms set the supplier settlement volume (`derive`)
5. `tx.payout` → `finance.settlement.payout_eur` — Settlement transaction stores computed payout (`derive`)
6. `finance.settlement.payout_eur` → `model.margin` — Supplier payout is included as cost in the margin model (`publish`)
7. `model.margin` → `metric.margin` — Calculates contribution after supplier payouts (`aggregate`)

### Scope 3 assurance — Dashboard in BoardBI
Shortest documented route: 7 hops

**Shortest Relate path:**

`lab.assays.moisture_pct` → `tx.normalize_assay` → `tx.dry_mass` → `climate.emissions.dry_tonnes` → `tx.emissions` → `model.scope3` → `metric.carbon` → `dash.esg`

1. `lab.assays.moisture_pct` → `tx.normalize_assay` — Assay ratio is read as the dry-mass adjustment input (`derive`)
2. `tx.normalize_assay` → `tx.dry_mass` — Normalized moisture ratio changes dry mass (`derive`)
3. `tx.dry_mass` → `climate.emissions.dry_tonnes` — Same dry-mass calculation also feeds climate accounting (`derive`)
4. `climate.emissions.dry_tonnes` → `tx.emissions` — Dry tonnes form the emissions-intensity denominator (`derive`)
5. `tx.emissions` → `model.scope3` — Carbon intensity transformation feeds scope 3 model (`publish`)
6. `model.scope3` → `metric.carbon` — Calculates emissions intensity by period (`aggregate`)
7. `metric.carbon` → `dash.esg` — ESG dashboard renders carbon intensity (`publish`)

## Verification

Results come from bounded, parameterized Cypher path traversals over the
persistent embedded Relate store `data/sample.rl`; no LLM guesses or SQL execution.
The source metadata is synthetic. Review the actual transformation and rule
implementations before approving a production change.
