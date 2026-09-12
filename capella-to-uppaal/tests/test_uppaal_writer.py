import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from src.capella_model import parse_state_machine
from src.capella_scenarios import parse_scenario_paths
from src.uppaal_writer import write_path_model


MODEL = (Path(__file__) / ".." / ".." / ".." / "capella-model" / "Level Crossing Traffic Control.capella").resolve()


class UppaalWriterTests(unittest.TestCase):
    def _blocked_path(self):
        return next(
            path for path in parse_scenario_paths(MODEL)
            if path.scenario_name == "Vehicle blocked on the track" and path.path_name == "Cas de blocage sur la voie"
        )

    def test_writes_safety_and_path_templates(self):
        machine = parse_state_machine(MODEL, "Safety command control")
        path = self._blocked_path()

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "blocked.xml"
            write_path_model(machine, path, output)
            root = ET.parse(output).getroot()

        templates = [element.findtext("name") for element in root.findall("template")]
        self.assertIn("Safety_command_controlTemplate", templates)
        self.assertTrue(any(name.startswith("Scenario_") for name in templates))
        self.assertIn("system Safety_command_controlTemplate, ", root.findtext("system"))

    def test_path_sends_state_machine_trigger_and_guards_time_constraint(self):
        machine = parse_state_machine(MODEL, "Safety command control")
        path = self._blocked_path()

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "blocked.xml"
            write_path_model(machine, path, output)
            text = output.read_text(encoding="utf-8")

        self.assertIn("event_vehicle_entered_the_crossing_information!", text)
        self.assertIn("event_vehicle_entered_the_crossing_information?", text)
        self.assertIn("path_clock_0 &gt; 60", text)

    def test_internal_self_messages_are_not_sent_as_channel(self):
        machine = parse_state_machine(MODEL, "Safety command control")
        path = self._blocked_path()

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "blocked.xml"
            write_path_model(machine, path, output)
            text = output.read_text(encoding="utf-8")

        self.assertNotIn("event_vehicle_stopped_on_the_track_information!", text)


if __name__ == "__main__":
    unittest.main()
