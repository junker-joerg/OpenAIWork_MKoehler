from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .core import Transformer, load_config


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ever2obsidian")
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--config")
    p.add_argument("--attachments-dir", default="attachments")
    p.add_argument("--resources-dir-name", default="_resources")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--verbose", action="store_true")
    p.add_argument("--stats", action="store_true")
    p.add_argument("--no-linking", action="store_true")
    p.add_argument("--no-classify", action="store_true")
    p.add_argument("--no-tagging", action="store_true")
    p.add_argument("--link-min-confidence", type=float, default=0.65)
    p.add_argument("--max-links-per-note", type=int, default=200)
    p.add_argument("--exclude", action="append", default=[])
    p.add_argument("--include", action="append", default=[])
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    input_dir = Path(args.input)
    output_dir = Path(args.output)
    if not input_dir.exists() or not input_dir.is_dir():
        print(f"Input directory not found: {input_dir}", file=sys.stderr)
        return 2
    cfg_path = Path(args.config) if args.config else None
    config = load_config(cfg_path, args)
    transformer = Transformer(config, args)
    try:
        return transformer.run(input_dir, output_dir)
    except Exception as exc:  # pragma: no cover
        print(f"Fatal error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
