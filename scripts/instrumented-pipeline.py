#!/usr/bin/env python3
"""Run an actual local SQL pipeline and emit its OpenLineage with the official SDK.

The SQL is executed on SQLite; column-lineage facets are derived from the SELECT
expressions with sqlglot, not typed into a stand-in JSON fixture. The use case and
records are deliberately fictional. This is a real *instrumented local pipeline*,
not a claim of a connected customer warehouse.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from uuid import uuid4

from openlineage.client import OpenLineageClient
from openlineage.client.event_v2 import InputDataset, Job, OutputDataset, Run, RunEvent, RunState
from openlineage.client.generated.column_lineage_dataset import (
    ColumnLineageDatasetFacet, Fields, InputField, Transformation,
)
from openlineage.client.generated.schema_dataset import (
    SchemaDatasetFacet, SchemaDatasetFacetFields,
)
from openlineage.client.transport.file import FileConfig, FileTransport
import sqlglot
from sqlglot import exp

PRODUCER="https://github.com/mhatipog/data-impact-graph/blob/main/scripts/instrumented-pipeline.py"
NS="sqlite://data-impact-graph/instrumented-local-etl"
JOBS="local-sql-etl://data-impact-graph"
STEPS=[
 ("normalize_assay",
  "stage_assays",
  """SELECT a.lot_id AS lot_id,
       a.moisture_pct / 100.0 AS moisture_ratio
     FROM raw_assays AS a"""),
 ("calculate_dry_mass",
  "core_dry_mass",
  """SELECT a.lot_id AS lot_id,
       h.gross_kg * (1.0 - a.moisture_ratio) AS dry_kg
     FROM stage_assays AS a JOIN raw_harvests AS h ON a.lot_id = h.lot_id"""),
 ("supplier_payouts",
  "marts_supplier_settlements",
  """SELECT d.lot_id AS lot_id,
       d.dry_kg * c.price_per_dry_kg AS payout_eur
     FROM core_dry_mass AS d JOIN raw_contracts AS c ON d.lot_id = c.lot_id"""),
 ("scope3_intensity",
  "marts_scope3_intensity",
  """SELECT d.lot_id AS lot_id,
       f.kg_co2e / (d.dry_kg / 1000.0) AS co2e_per_dry_tonne
     FROM core_dry_mass AS d JOIN raw_fleet AS f ON d.lot_id = f.lot_id"""),
 ("field_yield",
  "marts_field_yield",
  """SELECT h.field_id AS field_id,
       SUM(h.gross_kg) AS yield_kg
     FROM raw_harvests AS h GROUP BY h.field_id"""),
]

def utc():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")

def schema(conn, table):
    rows = conn.execute("PRAGMA table_info('%s')" % table.replace("'","''")).fetchall()
    assert rows, ("Schema missing: "+table)
    return SchemaDatasetFacet(fields=[
        SchemaDatasetFacetFields(name=row[1],type=row[2] or "TEXT",ordinal_position=row[0]+1)
        for row in rows
    ],producer=PRODUCER)

def source_maps(sql):
    select=sqlglot.parse_one(sql,read="sqlite")
    if not isinstance(select, exp.Select):raise ValueError("Only SELECT steps are accepted")
    aliases={t.alias_or_name:t.name for t in select.find_all(exp.Table)}
    if not aliases:raise ValueError("SQL must name input tables")
    return select,aliases

def lineage(sql):
    select,aliases=source_maps(sql)
    fields={}
    for expression in select.expressions:
        out_name=expression.alias_or_name
        if not out_name:raise ValueError("Output must have a resolvable alias")
        refs={}
        for field in expression.find_all(exp.Column):
            if not field.table or field.table not in aliases:
                raise ValueError("Ambiguous or unresolved SQL source column: "+field.sql())
            source=aliases[field.table]
            subtype="IDENTITY" if isinstance(expression, exp.Alias) and isinstance(expression.this,exp.Column) else "TRANSFORMATION"
            refs[(source,field.name)]=InputField(
                namespace=NS,name=source,field=field.name,
                transformations=[Transformation(type="DIRECT",subtype=subtype,
                                                description=expression.sql(dialect="sqlite")[:240])])
        fields[out_name]=Fields(inputFields=list(refs.values()))
    # Only inputs genuinely present in ON/WHERE/GROUP BY are tagged as INDIRECT,
    # not every field on every table. They influence membership/aggregation.
    indirect={}
    for join in select.find_all(exp.Join):
        condition=join.args.get("on")
        if condition:
            for col in condition.find_all(exp.Column):
                if col.table not in aliases:raise ValueError("Unresolved join key")
                table=aliases[col.table]
                indirect[(table,col.name,"JOIN")]=InputField(namespace=NS,name=table,field=col.name,
                    transformations=[Transformation(type="INDIRECT",subtype="JOIN",
                                                    description=condition.sql(dialect="sqlite")[:220])])
    for attr,subtype in [("where","FILTER"),("group","GROUP_BY")]:
        value=select.args.get(attr)
        if value:
            for col in value.find_all(exp.Column):
                if col.table not in aliases: raise ValueError("Unresolved "+subtype+" key")
                table=aliases[col.table]
                indirect[(table,col.name,subtype)]=InputField(namespace=NS,name=table,field=col.name,
                    transformations=[Transformation(type="INDIRECT",subtype=subtype,
                                                    description=value.sql(dialect="sqlite")[:220])])
    return list(dict.fromkeys(aliases.values())),ColumnLineageDatasetFacet(
        fields=fields,dataset=list(indirect.values()),producer=PRODUCER,
    )

def initialize(conn):
    conn.executescript("""
    CREATE TABLE raw_assays(lot_id TEXT PRIMARY KEY, moisture_pct REAL NOT NULL);
    CREATE TABLE raw_harvests(lot_id TEXT PRIMARY KEY, field_id TEXT, gross_kg REAL);
    CREATE TABLE raw_contracts(lot_id TEXT PRIMARY KEY, price_per_dry_kg REAL);
    CREATE TABLE raw_fleet(lot_id TEXT PRIMARY KEY, kg_co2e REAL);
    INSERT INTO raw_assays VALUES ('LOT-001',20),('LOT-002',15),('LOT-003',32);
    INSERT INTO raw_harvests VALUES ('LOT-001','FIELD-A',10000),('LOT-002','FIELD-A',12000),
        ('LOT-003','FIELD-B',7500);
    INSERT INTO raw_contracts VALUES ('LOT-001',0.42),('LOT-002',0.47),('LOT-003',0.45);
    INSERT INTO raw_fleet VALUES ('LOT-001',1200),('LOT-002',1420),('LOT-003',870);
    """)

def execute(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    eventfile=out/"instrumented-openlineage.jsonl"
    if eventfile.exists(): eventfile.unlink()
    conn=sqlite3.connect(str(out/"instrumented-sqlite.db"))
    initialize(conn)
    client=OpenLineageClient(transport=FileTransport(
        FileConfig(log_file_path=str(eventfile),append=True)))
    report=[]
    for index,(job_name,target,sql) in enumerate(STEPS):
        inputs,facet=lineage(sql)
        run=Run(runId=str(uuid4()))
        job=Job(namespace=JOBS,name=job_name)
        inp=[InputDataset(namespace=NS,name=name,facets={"schema":schema(conn,name)})
             for name in inputs]
        # START denotes the actual execution point; only COMPLETE adds confirmed
        # lineage in Data Impact Graph. Output schema requires the executed table.
        start=RunEvent(eventType=RunState.START,eventTime=utc(),run=run,job=job,
                       producer=PRODUCER,inputs=inp,outputs=[])
        client.emit(start)
        conn.execute(f"CREATE TABLE {target} AS {sql}")
        conn.commit()
        rowcount=conn.execute(f"SELECT COUNT(*) FROM {target}").fetchone()[0]
        assert rowcount>0
        output=OutputDataset(namespace=NS,name=target,
                             facets={"schema":schema(conn,target),"columnLineage":facet})
        completed=RunEvent(eventType=RunState.COMPLETE,eventTime=utc(),run=run,job=job,
                           producer=PRODUCER,inputs=inp,outputs=[output])
        client.emit(completed)
        report.append({"step":job_name,"target":target,"rows":rowcount,"sql":sql.strip(),
                       "inputs":inputs,"lineage_columns":list(facet.fields.keys())})
    results={
      "producer":"official openlineage-python SDK",
      "pipeline":"real local SQLite SQL transformations, with SQLGlot-derived field lineage",
      "source_data":"synthetic fictional records",
      "events":str(eventfile),"events_count":len(eventfile.read_text().splitlines()),
      "jobs":report,
      "sample_finance":conn.execute(
          "SELECT lot_id, ROUND(payout_eur,2) FROM marts_supplier_settlements ORDER BY lot_id").fetchall(),
      "sample_climate":conn.execute(
          "SELECT lot_id, ROUND(co2e_per_dry_tonne,2) FROM marts_scope3_intensity ORDER BY lot_id").fetchall(),
    }
    assert results["events_count"]==len(STEPS)*2
    assert results["sample_finance"][0][1]==3360.0
    # Verify the emitted *SDK-serialized* JSON, not the Python object alone.
    rows=[json.loads(row) for row in eventfile.read_text().splitlines()]
    for row in rows:
        assert row["producer"]==PRODUCER
    complete=[row for row in rows if row["eventType"]=="COMPLETE"]
    assert len(complete)==len(STEPS)
    assert all("columnLineage" in row["outputs"][0]["facets"] for row in complete)
    (out/"instrumented-run.json").write_text(json.dumps(results,indent=2)+"\n")
    (out/"executed-sql.sql").write_text("\n\n".join(
        f"-- {x['step']} [executed, {x['rows']} rows]\nCREATE TABLE {x['target']} AS\n{x['sql']};"
        for x in report)+"\n")
    print("SDK_OPENLINEAGE_SQL_PIPELINE_VERIFIED "+json.dumps(
        {"events":results["events_count"],"jobs":len(STEPS),
         "actual_finance_eur":results["sample_finance"][0][1]}),flush=True)

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",default="demo/film-working")
    execute(parser.parse_args().out)
