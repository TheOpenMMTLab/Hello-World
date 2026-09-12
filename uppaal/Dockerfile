FROM ubuntu:22.04

RUN apt-get update && apt-get install -y x11-apps 
RUN apt-get install -y unzip
RUN apt-get install -y default-jre

WORKDIR /root

ENV UPPAAL_VERSION=uppaal-5.1.0-beta5-linux64


COPY ${UPPAAL_VERSION}.zip uppaal.zip
COPY run.sh run.sh

RUN unzip uppaal.zip && rm uppaal.zip

ENV VERIFYTA_PATH=/root/${UPPAAL_VERSION}/bin/verifyta
    