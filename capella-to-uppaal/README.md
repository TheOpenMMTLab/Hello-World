# Capella-zu-UPPAAL-Generator

Erzeugt aus dem Capella-Modell `Level Crossing Traffic Control.capella` für eine
Logical Component je erkanntem Szenario-Pfad ein UPPAAL-Modell (`.xml`), das die
zugehörige State Machine gegen den Ereignisablauf prüft.

## Aufbau

- `src/capella_model.py` – liest die State Machine (Zustände, Transitionen, Trigger)
  und löst über `find_traced_scenario_names` die per `GenericTrace` verknüpften
  Testszenarien einer Komponente auf.
- `src/capella_scenarios.py` – löst `CombinedFragment`/`InteractionOperand`
  (ALT-Alternativen) eines Szenarios in eigenständige, lineare Pfade auf; markiert
  Selbstnachrichten (Sender == Empfänger) als intern und ordnet `ConstraintDuration`-
  Zeitbedingungen dem jeweils passenden Pfad zu.
- `src/uppaal_writer.py` – erzeugt daraus das UPPAAL-XML (State-Machine-Template +
  ein Template je Pfad, inklusive Clock-Guards für Zeitbedingungen).
- `capella_to_uppaal.py` – CLI-Einstiegspunkt.
- `src/level_crossing_queries.json` – optionale zusätzliche UPPAAL-Deklarationen.

## Generator aufrufen

```bash
python capella_to_uppaal.py --component "Safety command control" --output tmp -m '../capella-model/Level Crossing Traffic Control.capella'
```

Der Generator ermittelt automatisch (über `GenericTrace`), welches Szenario zur
angegebenen Komponente gehört, löst dessen ALT-Alternativen in einzelne Pfade auf
und schreibt für **jeden Pfad eine eigene `.xml`-Datei** (State Machine + Pfad-Template).

Parameter:

- `model` (optional, positional): Pfad zur `.capella`-Datei; ohne Angabe wird die erste
  `.capella`-Datei im aktuellen Verzeichnis verwendet.
- `--component` (erforderlich): Name der Logical Component mit der zu prüfenden
  State Machine, z. B. `Safety command control`.
- `--config`: JSON-Datei mit zusätzlichen UPPAAL-Deklarationen (siehe
  `src/level_crossing_queries.json`).
- `--output`: Zielverzeichnis für die erzeugten `.xml`-Dateien (Default: `tmp`).

## Unittests

```bash
python -m unittest discover -s tests -v
```

Die Tests laufen direkt gegen `Level Crossing Traffic Control.capella` und prüfen:

- `tests/test_state_machine_parser.py` – Zustände/Transitionen/Trigger der Safety-State-Machine
- `tests/test_traceability.py` – Auflösung des `GenericTrace` zur Szenariofindung
- `tests/test_scenario_parser.py` – Auflösung der ALT-Alternativen in zwei Pfade,
  interne Selbstnachrichten, pfadspezifische Zeitbedingungen
- `tests/test_uppaal_writer.py` – erzeugtes UPPAAL-XML (Templates, System,
  Synchronisationen, Clock-Guards)

## UPPAAL-Modell prüfen (Docker-Image)

Verifikation der erzeugten `.xml` mit dem UPPAAL-Image `frittenburger/uppaal:dev`
(enthält `verifyta` unter `/root/uppaal-5.1.0-beta5-linux64/bin/verifyta`):

```bash
source ../uppaal/data/licence.env 
```

```bash
MSYS_NO_PATHCONV=1 docker run --rm \
  -v ./tmp:/share/models \
  frittenburger/uppaal:dev ./run.sh $UPPAAL_LICENCE_KEY \
  /share/models/vehicle_blocked_on_the_track__cas_de_blocage_sur_la_voie.xml \
  /share/models/vehicle_blocked_on_the_track__cas_de_blocage_sur_la_voie.log
```

```bash
cat tmp/vehicle_blocked_on_the_track__cas_de_blocage_sur_la_voie.log
```

Jede erzeugte Datei enthält bereits eine eingebettete Standard-Query
(`A[] not deadlock`); eine separate `.q`-Datei ist nicht nötig.

Hinweis: Ein leeres `<queries/>`-Element im XML wird von diesem Image nicht akzeptiert;
der Generator lässt das Element deshalb weg, wenn keine Queries vorhanden sind.


## docker image

```bash
docker build -t frittenburger/capella-to-uppaal:dev .
```
