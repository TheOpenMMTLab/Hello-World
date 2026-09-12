import unittest
from pathlib import Path
from src.capella_scenarios import parse_scenario_paths


MODEL = (Path(__file__) / ".." / ".." / ".." / "capella-model" / "Level Crossing Traffic Control.capella").resolve()


class ScenarioPathParserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.paths = [p for p in parse_scenario_paths(MODEL) if p.scenario_name == "Vehicle blocked on the track"]

    def test_alt_operands_produce_two_distinct_paths(self):
        path_names = {path.path_name for path in self.paths}

        self.assertEqual(path_names, {"Cas nominal", "Cas de blocage sur la voie"})

    def test_nominal_path_has_upper_time_bound(self):
        nominal = next(path for path in self.paths if path.path_name == "Cas nominal")

        self.assertEqual(len(nominal.constraints), 1)
        self.assertEqual((nominal.constraints[0].seconds, nominal.constraints[0].operator), (60, "<="))
        self.assertTrue(all(not step.internal for step in nominal.steps))

    def test_blocked_path_has_lower_time_bound_and_internal_self_messages(self):
        blocked = next(path for path in self.paths if path.path_name == "Cas de blocage sur la voie")

        self.assertEqual(len(blocked.constraints), 1)
        self.assertEqual((blocked.constraints[0].seconds, blocked.constraints[0].operator), (60, ">"))
        internal_operations = {step.operation_name for step in blocked.steps if step.internal and step.operation_name}
        self.assertIn("Vehicle stopped on the track information", internal_operations)

    def test_steps_are_ordered_and_reference_operations(self):
        for path in self.paths:
            self.assertGreater(len(path.steps), 0)
            self.assertEqual([step.order for step in path.steps], sorted(step.order for step in path.steps))


if __name__ == "__main__":
    unittest.main()
