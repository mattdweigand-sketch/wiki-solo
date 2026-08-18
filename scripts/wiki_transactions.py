#!/usr/bin/env python3
"""Inspect or deterministically recover repository-local file transactions."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from _file_transactions import TransactionError, diagnose_transaction, recover_all, transaction_status


REPO_ROOT = Path(__file__).resolve().parents[1]


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    sub = p.add_subparsers(dest="command", required=True)
    status = sub.add_parser("status")
    status.add_argument("--quiet", action="store_true")
    sub.add_parser("recover")
    diagnose = sub.add_parser("diagnose")
    diagnose.add_argument("transaction_id")
    return p


def main() -> int:
    args = parser().parse_args()
    root = args.repo_root.resolve()
    try:
        if args.command == "status":
            clean, reports = transaction_status(root)
            if not args.quiet:
                print("Transaction state: clean" if clean else "Transaction state: nonclean")
                for report in reports:
                    print(f"- {report}")
            return 0 if clean else 1
        if args.command == "recover":
            messages = recover_all(root)
            print("No transaction recovery needed." if not messages else "Recovered transaction state:")
            for message in messages:
                print(f"- {message}")
            return 0
        report = diagnose_transaction(root, args.transaction_id)
        print(json.dumps(report, sort_keys=True, indent=2))
        return 0
    except TransactionError as exc:
        print(f"wiki_transactions.py: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
