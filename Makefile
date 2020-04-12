SHELL = /bin/bash
.SILENT:

install:
	echo Creating virtualenv
	virtualenv .venv

	echo Installing requirements
	. .venv/bin/activate && pip install -r requirements.txt

	echo Done.

migrate:
	echo Executing migration script.
	. .venv/bin/activate && python migrate.py

automigrate:
	echo Executing migration script.
	. .venv/bin/activate && python migrate.py --auto

update:
	echo pull, stop, install, migrate, run
	git pull && make stop && make install && make migrate && make run prod

run:
	if [ "$(filter-out $@,$(MAKECMDGOALS))" == "dev" ] ; then \
		. .venv/bin/activate && python wsgi.py; \
	elif [ "$(filter-out $@,$(MAKECMDGOALS))" == "prod" ] ; then \
		echo "Running app with gunicorn on 127.0.0.1:8000 (logs: gunicorn.log)"; \
		. .venv/bin/activate && \
		gunicorn --bind 127.0.0.1:8000 --workers=4 wsgi:app --daemon --access-logfile ./gunicorn.log --pid gunicorn.pid; \
	elif [ "$(filter-out $@,$(MAKECMDGOALS))" == "devprod" ] ; then \
		echo "Running app with gunicorn on 127.0.0.1:8001 (logs: gunicorn.log)"; \
		. .venv/bin/activate && \
		gunicorn --bind 127.0.0.1:8001 --workers=4 wsgi:app --daemon --access-logfile ./gunicorn.log --pid gunicorn.pid; \
	fi;

stop:
	echo Stopping app
	-kill `grep -hs ^ gunicorn.pid` 2>/dev/null

restart:
	@make stop
	@make run prod

shell:
	. .venv/bin/activate && python

logs:
	tail -f debug.log

%:
	@:
