"""CLI für die Capella-zu-UPPAAL-Transformation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.capella_model import find_traced_scenario_names, parse_state_machine
from src.capella_scenarios import parse_scenario_paths
from src.uppaal_writer import write_path_model


def main() -> int:
    """Erzeugt für jeden Pfad des per GenericTrace verknüpften Szenarios ein UPPAAL-Modell."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-m", "--model", required=True, type=Path, help="Pfad zur .capella-Datei")
    parser.add_argument("--component", required=True, help="Name der Logical Component, z. B. 'Safety command control'")
    parser.add_argument("--config", type=Path, help="JSON mit optionalen UPPAAL-Deklarationen")
    parser.add_argument("--output", type=Path, default=Path("tmp"))
    args = parser.parse_args()
    model = args.model
    config = json.loads(args.config.read_text(encoding="utf-8")) if args.config else {}

    machine = parse_state_machine(model, args.component)
    scenario_names = find_traced_scenario_names(model, args.component)
    if not scenario_names:
        parser.error(f"Keine per GenericTrace verknüpften Szenarien für Komponente {args.component!r} gefunden")

    selected = [path for path in parse_scenario_paths(model) if path.scenario_name in scenario_names]
    if not selected:
        parser.error(f"Keine Pfade für die verknüpften Szenarien {scenario_names!r} gefunden")

    for path in selected:
        filename = "_".join(path.scenario_name.lower().split()) + "__" + "_".join(path.path_name.lower().split()) + ".xml"
        write_path_model(machine, path, args.output / filename, tuple(config.get("declarations", [])))
    print(f"Generated {len(selected)} path model(s) in {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
