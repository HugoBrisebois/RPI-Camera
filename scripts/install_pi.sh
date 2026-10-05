#!/bin/sh
set -eu

if [ "$(id -u)" -eq 0 ]; then
	APT=""
else
	APT="sudo"
fi

$APT apt-get update
$APT apt-get install -y \
	python3-picamera2 \
	python3-pyqt6 \
	python3-pip \
	python3-setuptools \
	python3-wheel

printf '%s\n' "Dependencies installed. From the project directory run: sh run.sh"
