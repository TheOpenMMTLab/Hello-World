"""Erzeugung von UPPAAL-XML aus Capella-State-Machines und Szenario-Pfaden."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from .capella_model import StateMachine, Trigger
from .capella_scenarios import ScenarioPath


def identifier(value: str) -> str:
    """Erzeugt einen gültigen, stabilen UPPAAL-Bezeichner."""

    result = re.sub(r"[^A-Za-z0-9_]", "_", value).strip("_") or "event"
    return f"s_{result}" if result[0].isdigit() else result


def channel_name(operation_name: str) -> str:
    """Erzeugt den Kanalnamen aus einem Capella-Bezeichner (Trigger- oder Operationsname)."""

    return f"event_{identifier(operation_name).lower()}"


def channel(trigger: Trigger) -> str:
    """Erzeugt den Kanalnamen aus dem Capella-Triggernamen."""

    return channel_name(trigger.name)


def _location(template: ET.Element, state_id: str, name: str, index: int, y: int) -> None:
    location = ET.SubElement(template, "location", {"id": state_id, "x": str(index * 220), "y": str(y)})
    ET.SubElement(location, "name", {"x": "10", "y": "-20"}).text = identifier(name)


def _append_state_machine(root: ET.Element, machine: StateMachine) -> str:
    template = ET.SubElement(root, "template")
    template_name = f"{identifier(machine.component_name)}Template"
    ET.SubElement(template, "name").text = template_name
    ET.SubElement(template, "parameter")
    ET.SubElement(template, "declaration").text = "clock response;"
    location_ids = {state.element_id: f"{identifier(machine.component_name)}_{index}" for index, state in enumerate(machine.states)}
    for index, state in enumerate(machine.states):
        _location(template, location_ids[state.element_id], state.name, index, 100)
    ET.SubElement(template, "init", {"ref": location_ids[machine.initial_state.element_id]})
    for transition in machine.transitions:
        if transition.source not in location_ids or transition.target not in location_ids:
            continue
        edge = ET.SubElement(template, "transition")
        ET.SubElement(edge, "source", {"ref": location_ids[transition.source]})
        ET.SubElement(edge, "target", {"ref": location_ids[transition.target]})
        time_triggers = [trigger for trigger in transition.triggers if trigger.is_time_event]
        exchange_triggers = [trigger for trigger in transition.triggers if not trigger.is_time_event]
        if time_triggers and time_triggers[0].seconds is not None:
            ET.SubElement(edge, "label", {"kind": "guard", "x": "0", "y": "0"}).text = f"response >= {time_triggers[0].seconds}"
            ET.SubElement(edge, "label", {"kind": "assignment", "x": "0", "y": "20"}).text = "response = 0"
        if exchange_triggers:
            ET.SubElement(edge, "label", {"kind": "synchronisation", "x": "0", "y": "40"}).text = f"{channel(exchange_triggers[0])}?"
    return template_name


def _append_path(root: ET.Element, path: ScenarioPath, trigger_ids: set[str]) -> str:
    """Erzeugt ein Template, das genau den Ablauf eines ``ScenarioPath`` abspielt.

    Nur Sendeschritte, deren Operation ein bekannter Trigger der Safety-State-Machine
    ist und die keine Selbstnachricht sind, senden über einen Kanal (``!``); alle
    übrigen Schritte (Empfang, interne Selbstnachrichten, stille Constraint-Anker)
    werden nur als Kommentar dargestellt, damit UPPAAL sie ohne Blockade überspringt.
    """

    template = ET.SubElement(root, "template")
    template_name = f"Scenario_{identifier(path.scenario_name)}_{identifier(path.path_name)}"
    ET.SubElement(template, "name").text = template_name
    ET.SubElement(template, "parameter")
    clocks = [f"path_clock_{index}" for index in range(len(path.constraints))]
    ET.SubElement(template, "declaration").text = "\n".join(f"clock {clock};" for clock in clocks)

    location_ids = [f"{identifier(template_name)}_{index}" for index in range(len(path.steps) + 1)]
    for index in range(len(path.steps) + 1):
        _location(template, location_ids[index], f"step_{index}", index, 300)
    ET.SubElement(template, "init", {"ref": location_ids[0]})

    reset_at = {constraint.start_fragment_id: clock for constraint, clock in zip(path.constraints, clocks)}
    guard_at = {constraint.finish_fragment_id: (clock, constraint) for constraint, clock in zip(path.constraints, clocks)}

    for index, step in enumerate(path.steps):
        edge = ET.SubElement(template, "transition")
        ET.SubElement(edge, "source", {"ref": location_ids[index]})
        ET.SubElement(edge, "target", {"ref": location_ids[index + 1]})
        if step.fragment_id in guard_at:
            clock, constraint = guard_at[step.fragment_id]
            ET.SubElement(edge, "label", {"kind": "guard", "x": "0", "y": "0"}).text = f"{clock} {constraint.operator} {constraint.seconds}"
        if step.fragment_id in reset_at:
            ET.SubElement(edge, "label", {"kind": "assignment", "x": "0", "y": "20"}).text = f"{reset_at[step.fragment_id]} = 0"
        if step.kind == "Silent":
            ET.SubElement(edge, "label", {"kind": "comments", "x": "0", "y": "40"}).text = "constraint anchor"
        elif step.internal:
            ET.SubElement(edge, "label", {"kind": "comments", "x": "0", "y": "40"}).text = f"{step.operation_name} (internal)"
        elif step.kind == "EventSentOperation" and step.operation_id in trigger_ids:
            ET.SubElement(edge, "label", {"kind": "synchronisation", "x": "0", "y": "40"}).text = f"{channel_name(step.operation_name)}!"
        else:
            ET.SubElement(edge, "label", {"kind": "comments", "x": "0", "y": "40"}).text = step.operation_name
    return template_name


def write_path_model(machine: StateMachine, path: ScenarioPath, output: Path, declarations: tuple[str, ...] = ()) -> None:
    """Schreibt ein UPPAAL-Modell aus Safety-State-Machine und genau einem Szenariopfad."""

    root = ET.Element("nta")
    trigger_by_id = {trigger.element_id: trigger for transition in machine.transitions for trigger in transition.triggers if not trigger.is_time_event}
    declaration = ET.SubElement(root, "declaration")
    declaration.text = "\n".join([*declarations, *[f"chan {channel(trigger)};" for trigger in trigger_by_id.values()]])
    safety_template = _append_state_machine(root, machine)
    path_template = _append_path(root, path, set(trigger_by_id))
    system = ET.SubElement(root, "system")
    system.text = f"system {safety_template}, {path_template};"
    queries = ET.SubElement(root, "queries")
    query = ET.SubElement(queries, "query")
    ET.SubElement(query, "formula").text = "A[] not deadlock"
    ET.SubElement(query, "comment").text = f"Pfad {path.path_name!r} des Szenarios {path.scenario_name!r} muss deadlockfrei abspielbar sein."
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(output, encoding="utf-8", xml_declaration=True)
