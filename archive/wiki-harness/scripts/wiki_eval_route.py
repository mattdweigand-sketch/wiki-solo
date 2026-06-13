#!/usr/bin/env python3
"""Run deterministic route-policy fixtures for wiki work clusters."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from wiki_diff_policy import evaluate as evaluate_diff_policy
from wiki_route_policy import route_packet


FIXTURE_DIR = Path("tests/fixtures/wiki-route")


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        value = json.load(f)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def run_fixture(path: Path) -> list[str]:
    fixture = load_json(path)
    packet = fixture.get("packet")
    if not isinstance(packet, dict):
        return ["packet must be an object"]

    policy = evaluate_diff_policy(
        packet,
        max_wiki_pages=int(fixture.get("max_wiki_pages", 8)),
        allow_core_edits=bool(fixture.get("allow_core_edits", False)),
    )
    route = route_packet(packet, policy)

    errors: list[str] = []
    expected_route = fixture.get("expected_route")
    if route.get("route") != expected_route:
        errors.append(f"route: expected {expected_route!r}, got {route.get('route')!r}")

    expected_policy_status = fixture.get("expected_policy_status")
    if expected_policy_status and route.get("policy_status") != expected_policy_status:
        errors.append(
            f"policy_status: expected {expected_policy_status!r}, got {route.get('policy_status')!r}",
        )

    triggers = "\n".join(str(trigger) for trigger in route.get("triggers", []))
    for expected in fixture.get("expected_trigger_contains", []):
        if str(expected) not in triggers:
            errors.append(f"missing expected trigger: {expected}")

    return errors


def main() -> int:
    if not FIXTURE_DIR.exists():
        print(f"missing route fixture dir: {FIXTURE_DIR}", file=sys.stderr)
        return 2

    fixture_paths = sorted(FIXTURE_DIR.glob("*.json"))
    if not fixture_paths:
        print(f"no route fixtures found in {FIXTURE_DIR}", file=sys.stderr)
        return 2

    failures = 0
    for path in fixture_paths:
        fixture_id = path.stem
        try:
            fixture = load_json(path)
            fixture_id = str(fixture.get("id", path.stem))
            errors = run_fixture(path)
        except Exception as exc:
            errors = [str(exc)]

        if errors:
            failures += 1
            print(f"FAIL {fixture_id}")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"PASS {fixture_id}")

    print(f"\nSummary: {len(fixture_paths) - failures} passed, {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
