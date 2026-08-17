#!/bin/bash
set -e

if [ ! -d ".venv" ]; then
	python3 -m venv .venv
	.venv/bin/python -m pip install -r requirements.txt
fi

exec .venv/bin/python main.py "$@"