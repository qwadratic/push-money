#!/usr/bin/bash

cd /root/push-dev
source .venv/bin/activate
make stop
git pull
pip install -r requirements.txt
make automigrate
make run devprod
