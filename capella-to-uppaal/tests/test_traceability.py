import sys
import unittest
from pathlib import Path
from src.capella_model import find_traced_scenario_names


MODEL = (Path(__file__) / ".." / ".." / ".." / "capella-model" / "Level Crossing Traffic Control.capella").resolve()


class TraceabilityTests(unittest.TestCase):
    def test_generic_trace_resolves_to_scenario_name(self):
        names = find_traced_scenario_names(MODEL, "Safety command control")

        self.assertEqual(names, ("Vehicle blocked on the track",))

    def test_unknown_component_has_no_traced_scenarios(self):
        names = find_traced_scenario_names(MODEL, "Does not exist")

        self.assertEqual(names, ())


if __name__ == "__main__":
    unittest.main()
