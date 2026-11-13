"""Launch the explorer, import metadata, or execute a reproducible impact query."""
import argparse
import json
from pathlib import Path

from .core import SAMPLE, STORE, impact, overview, seed


def main() -> None:
    parser = argparse.ArgumentParser(description="Column-aware data impact analysis, powered by Relate")
    parser.add_argument("command", nargs="?", choices=("serve", "seed", "impact", "overview"), default="serve")
    parser.add_argument("asset", nargs="?", default="lab.assays.moisture_pct")
    parser.add_argument("--upstream", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--store", type=Path, default=STORE)
    parser.add_argument("--metadata", type=Path, default=SAMPLE)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if args.command == "seed":
        print(json.dumps(seed(args.metadata, args.store, force=args.force), indent=2))
    elif args.command == "impact":
        print(json.dumps(impact(args.asset, "upstream" if args.upstream else "downstream", args.store), indent=2))
    elif args.command == "overview":
        print(json.dumps(overview(args.store), indent=2))
    else:
        if not args.store.exists():
            print("Creating sample Relate store from synthetic metadata...")
            seed(args.metadata, args.store)
        from .server import serve
        serve(args.store, args.port)


if __name__ == "__main__":
    main()
