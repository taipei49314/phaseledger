"""Table-driven measure boundaries from fixtures/boundaries/*.json (CYCLE-008)."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from phaseledger.measure import measure

BOUNDARIES = Path(__file__).resolve().parents[1] / "fixtures" / "boundaries"


class TestBoundaryFixtures(unittest.TestCase):
    def test_all_boundary_fixtures(self) -> None:
        files = sorted(BOUNDARIES.glob("*.json"))
        self.assertGreaterEqual(len(files), 6, "expected boundary fixtures")
        for path in files:
            with self.subTest(fixture=path.name):
                raw = json.loads(path.read_text(encoding="utf-8"))
                expect = raw.pop("_expect")
                strict = bool(raw.pop("_strict", False))
                # strip any other meta keys
                obs = {k: v for k, v in raw.items() if not k.startswith("_")}
                result = measure(obs, strict=strict)
                self.assertEqual(
                    result.verdict,
                    expect,
                    msg=f"{path.name}: got {result.verdict} reason={result.reason}",
                )


if __name__ == "__main__":
    unittest.main()
