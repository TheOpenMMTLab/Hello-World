# uppaal

UPPAAL-Validierung fuer das aus dem POC uebernommene Modell und die Queries.

## install

Voraussetzung: verifyta-Binary ist verfuegbar.

## usage

```bash
VERIFYTA_PATH=/opt/uppaal/bin/verifyta bash run.sh
```

## tests

```bash
bash run.sh --help
```

## docker image

```bash
docker build -t frittenburger/uppaal:dev .
```

Containerlauf:

```bash
source data/licence.env
MSYS_NO_PATHCONV=1 docker run --rm -v $(pwd)/data:/share/models frittenburger/uppaal:dev ./run.sh $UPPAAL_LICENCE_KEY /share/models/block_signal_model.xml /share/models/block_signal_model_output.log
```
