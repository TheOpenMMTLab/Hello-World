

Related Work:

Das Paper heißt „Bridging MBSE and MBSA through an Interoperability Framework“ (Makita, Kubic, Trousset, Zacharewicz; Procedia Computer Science, Band 277, 2026, S. 3083–3092).

Zur Capella-zu-UPPAAL-Transformation (Abschnitt 4, S. 6–7):
Mapping-Tabelle „Transformation Rules Capella to Uppaal“ (S. 7), 



Beispiel:
## Sicherheitsanforderungen  Constraints 

```
Operational Analysis → Operational Activities → Root Operational Activity
├── "Start and cross the crossing"
│     └── Constraint: "A train must not start if a road vehicle is stopped on the crossing"
└── "Cross the crossing"
      ├── Constraint: "Simultaneous crossing by a road vehicle and a train must not be possible"
      └── "Cross the crossing" (2. Funktion gleichen Namens)
            └── Constraint: "A road vehicle must not be able to cross if not allowed"
```

```
System Analysis → System Functions → "Cross the railway" → "Cross the crossing"
    └── Constraint: "A road vehicle must not be able to enter the crossing if not allowed"
        (mit TransfoLink zurück auf die Operational-Analysis-Constraint 8779731a)
```

```
Logical Architecture → Logical Functions → "Switch off the arriving train stop signal"
    └── Constraint: "Two different signals for safety reasons"
```

```
Physical Architecture → (Funktion/Komponente id=56b915d9-...)
    └── Constraint: "Secure safety-critical processing by choosing a reliable, high-availability computer board for it."
```

## State Machine
```
Logical Architecture
└── Structure
    └── Control system            (SystemComponent-Ebene)
        └── Control system        (LogicalComponent-Ebene)
            └── Logical Component "Safety command control"
```

```
Logical Component "Safety command control"
├── GenericTrace → Szenario "Vehicle blocked on the track"
├── 3 ComponentFunctionalAllocation
│     ├── Test the proper operation of the system
│     ├── Detect conflicting accesses to the crossing
│     └── Detect and secure a vehicle stopped on the track
├── StateMachine "Logical Component State Machine"
│     └── Nominal mode / Vehicle stopped on the track / Ongoing conflict + 4 Transitions
└── 14 ComponentPorts (CP 1–CP 14) mit PortAllocations zu Functional Exchanges
```

```
StateMachine "Logical Component State Machine"
└── Region "Default Region"  (involvedStates: 3 States)
    ├── Mode "Nominal mode"
    ├── Mode "Vehicle stopped on the track"   ← mit ownedConstraints
    ├── Mode "Ongoing conflict"
    └── 4× StateTransition
          Nominal → Vehicle stopped   (Trigger: Functional Exchange + TimeEvent „1 mn“, + Constraint)
          Nominal → Ongoing conflict  (Trigger: Functional Exchange)
          Ongoing conflict → Nominal  (Trigger: Functional Exchange)
          Vehicle stopped → Nominal   (Trigger: Functional Exchange)
```

## Scenarios
`Logical Architecture/Capabilities`
```
CapabilityRealization "Detect and secure a vehicle stopped on the track" (System-Ebene)
├── Scenario "Vehicle blocked on the track"
│     ├── 4 InstanceRoles (Road vehicle, Control system, Railway facilities, Road facilities)
│     ├── ownedMessages (7 SequenceMessages)
│     ├── ownedInteractionFragments (States, MessageEnds, ExecutionEnds, FragmentEnds)
│     ├── CombinedFragment (ALT)
│     │     ├── Operand "Cas nominal"
│     │     └── Operand "Cas de blocage sur la voie"
│     ├── ownedEvents (EventSentOperation/EventReceiptOperation/ExecutionEvent, je Nachricht/Zustand)
│     └── ownedConstraintDurations
│           ├── "1 mn max"  (zwischen Fahrzeugerkennung und Erkennung "arrêté sur la voie")
│           └── "> 1 min"   (zwischen zwei Detektionszuständen im Blockadefall)
├── includes → "Manage and control train departure traffic"
├── includes → "Manage and control the train arrival traffic"
└── AbstractCapabilityRealization → Operational Capability "Detect and secure a vehicle stopped on the track"
```

Sequenz 2 – Operand „Cas de blocage sur la voie“ (Fahrzeug bleibt stehen)

| Schritt | Sender | Message | Empfänger | State-Fragment | Constraint Duration |
|---|---|---|---|---|---|
| 7 | Railway facilities | Vehicle entered the crossing information | Control system | – | **Start** „> 1 min“ |
| 8 | – | – | Control system | „Détecte et sécurise un véhicule arrêté sur la voie“ | **Ende** „> 1 min“ |
| 9 | Control system | Vehicle stopped on the track information | Control system *(intern)* | – | |
| 10 | – | – | Control system | „Choisit de retarder un départ“ | |
| 11 | Control system | Vehicle stopped on the track information *(2. Vorkommen)* | Control system *(intern)* | – | |
| 12 | – | – | Control system | „Choisit de retarder une arrivée“ | |
| 13 | Control system | Vehicle stopped on the track information *(3. Vorkommen)* | Control system *(intern)* | – | |
| 14 | – | – | Control system | „Détecte des conflits d'accès au passage“ | |

Fachliche Bedeutung: Dauert die Erkennung „Détecte et sécurise un véhicule arrêté sur la voie“ länger als 1 Minute, interpretiert das System dies als Blockade. Danach entscheidet es intern (drei Selbstnachrichten an die eigene Instanz Control system), eine Zugabfahrt zu verzögern, eine Zugankunft zu verzögern und erkennt schließlich einen Zugriffskonflikt am Übergang.

## Implementierung

Grobe Idee, um `Safety command control` vollständig modellgetrieben mit UPPAAL zu testen:

1. **State Machine → UPPAAL-Template** (bereits vorhanden in `capella_model.py`/`uppaal_writer.py`):
   Komponente → Template, `Mode` → `location`, `StateTransition` → `transition`,
   Functional-Exchange-Trigger → Synchronisationskanal (`?`), TimeEvent-Trigger → Clock-Guard.

2. **Szenario automatisch über `GenericTrace` finden** (noch offen):
   Statt eines manuellen `--scenario`-Parameters den `GenericTrace` des betroffenen Zustands
   (`Vehicle stopped on the track` → Szenario `Vehicle blocked on the track`) auswerten und
   daraus automatisch das passende Testszenario ableiten.

3. **`CombinedFragment` (ALT) in zwei Pfade auflösen** (noch offen):
   `capella_scenarios.py` muss `CombinedFragment`/`InteractionOperand` erkennen und je Operand
   einen eigenen Ereignisablauf bilden (gemeinsamer Präfix vor dem Fragment + operandenspezifischer
   Teil), statt aktuell alle `MessageEnd`-Fragmente linear zu verschmelzen.

4. **Je Pfad ein eigenes Szenario-Template** (Erweiterung von `uppaal_writer.py`):
   Aus „Cas nominal“ und „Cas de blocage sur la voie“ je ein Template mit `location`/`transition`
   erzeugen, das über `event_...!` genau die Trigger sendet, die die Safety-State-Machine per
   `event_...?` erwartet. Interne Selbstnachrichten (dreimal `Vehicle stopped on the track
   information` innerhalb von `Control system`) werden dabei nur als interne Übergänge, nicht als
   Kanal zur Safety-State-Machine modelliert.

5. **Zeitconstraints pfadspezifisch zuordnen** (noch offen):
   Die beiden `ConstraintDuration`-Elemente (`1 mn max` im Nominalfall, `> 1 min` im Blockadefall)
   dem jeweils passenden Szenario-Template als Clock-Guard zuordnen, damit UPPAAL den Blockadefall
   (Zeitüberschreitung) tatsächlich erzwingen kann.

6. **Komposition:** `system Safety_command_controlTemplate, Scenario_CasNominal, Scenario_CasDeBlocage;`
   – beide Pfad-Templates parallel zum Safety-Template, damit UPPAAL beide Abläufe gegen dieselbe
   State Machine prüfen kann.