SHELL = /bin/bash

install:
	@echo Creating virtualenv
	@virtualenv .venv

	@echo Installing requirements
	@. .venv/bin/activate && pip install -r requirements.txt

	@echo Done.

migrate:
	@echo Executing migration script.
	@. .venv/bin/activate && python migrate.py

update:
	@echo checkout, pull, stop, run
	@git checkout && git pull && make stop && make run prod

run:
	@if [ "$(filter-out $@,$(MAKECMDGOALS))" == "dev" ] ; then \
		. .venv/bin/activate && python wsgi.py; \
	elif [ "$(filter-out $@,$(MAKECMDGOALS))" == "prod" ] ; then \
		echo "Running app with gunicorn on 127.0.0.1:8000 (logs: gunicorn.log)"; \
		. .venv/bin/activate && \
		gunicorn --bind 127.0.0.1:8000 wsgi:app --daemon --access-logfile ./gunicorn.log --pid gunicorn.pid; \
	fi;

stop:
	@echo Stopping app
	@kill `grep -hs ^ gunicorn.pid` 2>/dev/null

%:
	@:
