"""CLI for native Relate impact queries and OpenLineage ingestion."""
import argparse
import json
from pathlib import Path

from .core import SAMPLE, STORE, impact, overview, receipt, seed


def main() -> None:
    parser = argparse.ArgumentParser(description="Column-aware change impact analysis, powered by Relate")
    parser.add_argument("command", nargs="?",
                        choices=("serve", "seed", "impact", "overview", "report",
                                 "import", "import-openlineage"), default="serve")
    parser.add_argument("asset", nargs="?", default="lab.assays.moisture_pct",
                        help="Asset ID, or event path when using import-openlineage")
    parser.add_argument("extra", nargs="?", help="Event file in 'import openlineage events.jsonl'")
    parser.add_argument("--upstream", action="store_true")
    parser.add_argument("--change", default="", help="Optional reviewer-supplied change note")
    parser.add_argument("--force", action="store_true", help="Overwrite a seeded example")
    parser.add_argument("--replace", action="store_true",
                        help="Replace an existing OpenLineage import instead of incrementally updating it")
    parser.add_argument("--store", type=Path, default=None, help="Relate database file")
    parser.add_argument("--metadata", type=Path, default=SAMPLE)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    store = args.store or STORE
    if args.command in ("import", "import-openlineage"):
        from .openlineage import DEFAULT_STORE, import_openlineage
        if args.command == "import":
            if args.asset != "openlineage" or not args.extra:
                parser.error("Use: import openlineage events.jsonl [--store graph.rl]")
            source = args.extra
        else:
            if args.asset == "lab.assays.moisture_pct":
                parser.error("Use: import-openlineage events.jsonl [--store graph.rl]")
            source = args.asset
        result = import_openlineage(source, args.store or DEFAULT_STORE, replace=args.replace)
        print(json.dumps(result, indent=2))
    elif args.command == "seed":
        print(json.dumps(seed(args.metadata, store, force=args.force), indent=2))
    elif args.command == "impact":
        print(json.dumps(impact(args.asset, "upstream" if args.upstream else "downstream", store), indent=2))
    elif args.command == "report":
        print(receipt(args.asset, "upstream" if args.upstream else "downstream", store, args.change))
    elif args.command == "overview":
        print(json.dumps(overview(store), indent=2))
    else:
        if not store.exists():
            if args.store is not None:
                parser.error("Requested Relate store does not exist. Import events first.")
            print("Creating sample Relate store from synthetic metadata...")
            seed(args.metadata, store)
        from .server import serve
        serve(store, args.port)


if __name__ == "__main__":
    main()
