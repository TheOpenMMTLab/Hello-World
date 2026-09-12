"""Parsen der Capella-Szenarien inklusive aller Pfade durch CombinedFragment/ALT."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from itertools import product
from pathlib import Path

from .capella_model import local_type


@dataclass(frozen=True)
class ScenarioStep:
    """Ein Schritt eines Pfads: eine gesendete/empfangene Nachricht oder ein interner Punkt."""

    order: int
    fragment_id: str
    kind: str  # "EventSentOperation" | "EventReceiptOperation" | "Silent"
    operation_id: str
    operation_name: str
    internal: bool


@dataclass(frozen=True)
class PathConstraint:
    """Eine für einen Pfad geltende Zeitbedingung (Capella ``ConstraintDuration``)."""

    seconds: int
    operator: str
    description: str
    start_fragment_id: str
    finish_fragment_id: str


@dataclass(frozen=True)
class ScenarioPath:
    """Ein konkreter, ausführbarer Ablauf durch ein Capella-Szenario.

    Jedes CombinedFragment/ALT ist bereits auf genau einen Zweig je Alternative
    aufgelöst, sodass ein ``ScenarioPath`` linear und direkt in ein
    UPPAAL-Template übersetzbar ist.
    """

    scenario_name: str
    path_name: str
    steps: tuple[ScenarioStep, ...]
    constraints: tuple[PathConstraint, ...]


@dataclass(frozen=True)
class _CombinedFragment:
    start_pos: int
    finish_pos: int
    operand_ranges: tuple[tuple[str, int, int], ...]  # (Name, erste Position, letzte Position)


def _parse_duration(text: str) -> tuple[int | None, str | None]:
    """Wandelt Freitext-Zeitangaben wie ``1 mn max`` oder ``> 1 min`` in Sekunden/Operator um."""

    match = re.search(r"(>=|<=|>|<|==)?\s*(\d+)\s*(?:mn|min|minute)s?", text, re.IGNORECASE)
    if not match:
        return None, None
    seconds = int(match.group(2)) * 60
    operator = match.group(1) or "<="
    return seconds, operator


def parse_scenario_paths(model_path: Path) -> tuple[ScenarioPath, ...]:
    """Ermittelt für jedes Szenario alle Pfade, die seine ALT-Alternativen ergeben."""

    root = ET.parse(model_path).getroot()
    elements_by_id = {element.attrib["id"]: element for element in root.iter() if "id" in element.attrib}
    paths: list[ScenarioPath] = []
    for scenario in (element for element in root.iter() if local_type(element) == "Scenario"):
        paths.extend(_parse_single_scenario(scenario, elements_by_id))
    return tuple(paths)


def _parse_single_scenario(scenario: ET.Element, elements_by_id: dict[str, ET.Element]) -> list[ScenarioPath]:
    scenario_name = scenario.attrib.get("name", "Scenario")
    position = {element.attrib["id"]: index for index, element in enumerate(scenario.iter()) if "id" in element.attrib}
    roles = {
        element.attrib["id"]: element.attrib.get("name", "role")
        for element in scenario.iter()
        if local_type(element) == "InstanceRole" and "id" in element.attrib
    }

    def role_of(fragment_id: str) -> str | None:
        fragment = elements_by_id.get(fragment_id)
        if fragment is None:
            return None
        covered = fragment.attrib.get("coveredInstanceRoles", "").split()
        return roles.get(covered[0].lstrip("#")) if covered else None

    # Selbstnachrichten (Sender == Empfänger) dürfen später keinen Kanal zu einem anderen Automaten bilden.
    internal_fragment_ids: set[str] = set()
    for message in scenario.iter():
        if local_type(message) != "SequenceMessage":
            continue
        sending_end = message.attrib.get("sendingEnd", "").lstrip("#")
        receiving_end = message.attrib.get("receivingEnd", "").lstrip("#")
        if sending_end and receiving_end and role_of(sending_end) == role_of(receiving_end):
            internal_fragment_ids.update({sending_end, receiving_end})

    message_steps: dict[str, ScenarioStep] = {}
    for fragment in scenario.iter():
        if local_type(fragment) != "MessageEnd":
            continue
        event = elements_by_id.get(fragment.attrib.get("event", "").lstrip("#"))
        if event is None or local_type(event) not in {"EventSentOperation", "EventReceiptOperation"}:
            continue
        operation_id = event.attrib.get("operation", "").lstrip("#")
        operation = elements_by_id.get(operation_id)
        fragment_id = fragment.attrib["id"]
        message_steps[fragment_id] = ScenarioStep(
            order=position[fragment_id],
            fragment_id=fragment_id,
            kind=local_type(event),
            operation_id=operation_id,
            operation_name=operation.attrib.get("name", "event") if operation is not None else "event",
            internal=fragment_id in internal_fragment_ids,
        )

    constraints_raw: list[PathConstraint] = []
    for element in scenario.iter():
        if local_type(element) != "ConstraintDuration":
            continue
        seconds, operator = _parse_duration(element.attrib.get("duration", ""))
        start = element.attrib.get("start", "").lstrip("#")
        finish = element.attrib.get("finish", "").lstrip("#")
        if seconds is None or start not in position or finish not in position:
            continue
        constraints_raw.append(PathConstraint(seconds, operator, element.attrib.get("duration", ""), start, finish))

    combined_fragments: list[_CombinedFragment] = []
    for element in scenario.iter():
        if local_type(element) != "CombinedFragment":
            continue
        start_id = element.attrib.get("start", "").lstrip("#")
        finish_id = element.attrib.get("finish", "").lstrip("#")
        if start_id not in position or finish_id not in position:
            continue
        operand_ids = [reference.lstrip("#") for reference in element.attrib.get("referencedOperands", "").split()]
        operand_positions = sorted((position[operand_id], operand_id) for operand_id in operand_ids if operand_id in position)
        ranges = []
        for index, (operand_pos, operand_id) in enumerate(operand_positions):
            next_pos = operand_positions[index + 1][0] if index + 1 < len(operand_positions) else position[finish_id]
            operand_name = elements_by_id[operand_id].attrib.get("name", f"operand_{index}")
            ranges.append((operand_name, operand_pos, next_pos - 1))
        combined_fragments.append(_CombinedFragment(position[start_id], position[finish_id], tuple(ranges)))

    # Nur oberste CombinedFragments berücksichtigen; verschachtelte ALTs werden nicht unterstützt.
    top_level = [
        fragment
        for fragment in combined_fragments
        if not any(
            other is not fragment and other.start_pos < fragment.start_pos and fragment.finish_pos < other.finish_pos
            for other in combined_fragments
        )
    ]
    top_level.sort(key=lambda fragment: fragment.start_pos)

    max_position = max(position.values(), default=0)
    fixed_ranges: list[tuple[int, int]] = []
    previous_end = -1
    for fragment in top_level:
        fixed_ranges.append((previous_end + 1, fragment.start_pos - 1))
        previous_end = fragment.finish_pos
    fixed_ranges.append((previous_end + 1, max_position))

    def in_ranges(pos: int, ranges: list[tuple[int, int]]) -> bool:
        return any(start <= pos <= end for start, end in ranges)

    choice_options = [fragment.operand_ranges for fragment in top_level] or [(("default", 0, max_position),)]
    step_positions = {step.order for step in message_steps.values()}
    anchor_positions = {position[c.start_fragment_id] for c in constraints_raw} | {position[c.finish_fragment_id] for c in constraints_raw}
    all_positions = sorted(step_positions | anchor_positions)
    fragment_id_by_position = {pos: fragment_id for fragment_id, pos in position.items()}

    paths: list[ScenarioPath] = []
    for combination in product(*choice_options):
        used_ranges = list(fixed_ranges) + [(first_pos, last_pos) for _, first_pos, last_pos in combination]
        path_name = "__".join(name for name, _, _ in combination) if top_level else "default"
        steps: list[ScenarioStep] = []
        for pos in all_positions:
            if not in_ranges(pos, used_ranges):
                continue
            fragment_id = fragment_id_by_position[pos]
            step = message_steps.get(fragment_id)
            if step is None:
                step = ScenarioStep(order=pos, fragment_id=fragment_id, kind="Silent", operation_id="", operation_name="", internal=True)
            steps.append(step)
        steps.sort(key=lambda step: step.order)
        path_constraints = tuple(
            constraint
            for constraint in constraints_raw
            if in_ranges(position[constraint.start_fragment_id], used_ranges) and in_ranges(position[constraint.finish_fragment_id], used_ranges)
        )
        paths.append(ScenarioPath(scenario_name, path_name, tuple(steps), path_constraints))
    return paths
