"""Lesen der für UPPAAL relevanten Capella-XMI-Elemente."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


XSI_TYPE = "{http://www.w3.org/2001/XMLSchema-instance}type"


@dataclass(frozen=True)
class Trigger:
    """Ein auf einer Capella-State-Transition referenzierter Trigger."""

    element_id: str
    name: str
    kind: str

    @property
    def is_time_event(self) -> bool:
        """Gibt an, ob der Trigger ein zeitliches Ereignis ist."""

        return "TimeEvent" in self.kind or self.name.lower().endswith(("mn", "min", "minute"))

    @property
    def seconds(self) -> int | None:
        """Liest einfache Zeitangaben wie ``1 mn`` in Sekunden um."""

        match = re.search(r"(\d+)\s*(?:mn|min|minute)", self.name.lower())
        return int(match.group(1)) * 60 if match else None


@dataclass(frozen=True)
class State:
    """Ein Capella-Mode oder Zustand."""

    element_id: str
    name: str
    kind: str


@dataclass(frozen=True)
class Transition:
    """Eine State-Transition mit aufgelösten Triggern."""

    element_id: str
    source: str
    target: str
    triggers: tuple[Trigger, ...]
    guard: str | None = None


@dataclass(frozen=True)
class StateMachine:
    """Eine aus Capella gelesene State Machine."""

    component_name: str
    name: str
    states: tuple[State, ...]
    transitions: tuple[Transition, ...]

    @property
    def initial_state(self) -> State:
        """Verwendet den ersten Capella-Zustand als Fallback-Initialzustand."""

        if not self.states:
            raise ValueError(f"State machine {self.name!r} has no states")
        return self.states[0]


def local_type(element: ET.Element) -> str:
    """Gibt den lokalen xsi:type ohne Namespace-Präfix zurück."""

    return element.attrib.get(XSI_TYPE, "").rsplit(":", 1)[-1]


def _id(element: ET.Element, attribute: str) -> str:
    return element.attrib.get(attribute, "").lstrip("#")


def _component_candidates(root: ET.Element) -> list[tuple[ET.Element, ET.Element]]:
    return [
        (component, machine)
        for component in root.iter()
        if local_type(component) in {"LogicalComponent", "SystemComponent", "PhysicalComponent"}
        for machine in component
        if local_type(machine) == "StateMachine"
    ]


def parse_state_machine(model_path: Path, component_name: str) -> StateMachine:
    """Parst eine State Machine inklusive Zuständen, Transitionen und Triggern.

    Functional Exchanges bleiben als Trigger typisiert und TimeEvents werden
    später als Clock-Guards behandelt.
    """

    root = ET.parse(model_path).getroot()
    elements = {element.attrib["id"]: element for element in root.iter() if "id" in element.attrib}
    candidates = [pair for pair in _component_candidates(root) if pair[0].attrib.get("name", "").strip() == component_name.strip()]
    if not candidates:
        available = sorted({component.attrib.get("name", "").strip() for component, _ in _component_candidates(root)})
        raise ValueError(f"Component {component_name!r} not found; available: {', '.join(available)}")
    component, machine = candidates[0]
    states = tuple(
        State(element.attrib["id"], element.attrib.get("name", "Unnamed"), local_type(element))
        for element in machine.iter()
        if local_type(element) in {"Mode", "State"} and "id" in element.attrib
    )
    transitions: list[Transition] = []
    for element in machine.iter():
        if local_type(element) != "StateTransition":
            continue
        triggers = tuple(
            Trigger(trigger_id, elements[trigger_id].attrib.get("name", "event"), local_type(elements[trigger_id]))
            for trigger_id in (reference.lstrip("#") for reference in element.attrib.get("triggers", "").split())
            if trigger_id in elements
        )
        guard = elements.get(element.attrib.get("guard", "").lstrip("#"))
        transitions.append(Transition(element.attrib.get("id", ""), _id(element, "source"), _id(element, "target"), triggers, guard.attrib.get("name") if guard is not None else None))
    return StateMachine(component.attrib.get("name", "Unnamed"), machine.attrib.get("name", "State Machine"), states, tuple(transitions))


def find_traced_scenario_names(model_path: Path, component_name: str) -> tuple[str, ...]:
    """Liest die per ``GenericTrace`` mit der Komponente verknüpften Szenarionamen.

    Ein ``GenericTrace`` ist ein rein dokumentarischer Nachvollziehbarkeitslink;
    zeigt er auf ein ``Scenario``, gilt dieses als Testszenario der Komponente.
    """

    root = ET.parse(model_path).getroot()
    elements = {element.attrib["id"]: element for element in root.iter() if "id" in element.attrib}
    components = [
        component
        for component in root.iter()
        if local_type(component) in {"LogicalComponent", "SystemComponent", "PhysicalComponent"}
        and component.attrib.get("name", "").strip() == component_name.strip()
    ]
    names: list[str] = []
    for component in components:
        for child in component:
            if local_type(child) != "GenericTrace":
                continue
            target = elements.get(child.attrib.get("targetElement", "").lstrip("#"))
            if target is not None and local_type(target) == "Scenario":
                names.append(target.attrib.get("name", "Scenario"))
    return tuple(dict.fromkeys(names))
