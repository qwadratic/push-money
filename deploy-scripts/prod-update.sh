#!/bin/bash
source .venv/bin/activate
make stop
git pull
pip install -r requirements.txt
make automigrate
make run prod
