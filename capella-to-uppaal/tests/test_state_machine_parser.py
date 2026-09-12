import sys
import unittest
from pathlib import Path
from src.capella_model import parse_state_machine

MODEL = (Path(__file__) / ".." / ".." / ".." / "capella-model" / "Level Crossing Traffic Control.capella").resolve()


class StateMachineParserTests(unittest.TestCase):
    def test_parses_safety_states_and_transitions(self):
        machine = parse_state_machine(MODEL, "Safety command control")

        self.assertEqual(machine.name, "Logical Component State Machine")
        self.assertEqual(
            [state.name for state in machine.states],
            ["Nominal mode", "Vehicle stopped on the track", "Ongoing conflict"],
        )
        self.assertEqual(len(machine.transitions), 4)

    def test_resolves_functional_and_time_triggers(self):
        machine = parse_state_machine(MODEL, "Safety command control")
        transition = next(
            item for item in machine.transitions
            if machine.states[0].element_id == item.source
            and machine.states[1].element_id == item.target
        )

        self.assertIn("Vehicle entered the crossing information", [trigger.name for trigger in transition.triggers])
        time_trigger = next(trigger for trigger in transition.triggers if trigger.is_time_event)
        self.assertEqual(time_trigger.seconds, 60)


if __name__ == "__main__":
    unittest.main()
