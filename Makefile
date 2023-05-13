SOURCEDIRS=syslog_ng_cfg_helper tests

.venv:
	poetry install

pytest: .venv
	poetry run pytest $(SOURCEDIRS)

black-check: .venv
	poetry run black --check $(SOURCEDIRS)

pylint: .venv
	poetry run pylint --rcfile=$(PWD)/.pylintrc $(SOURCEDIRS)

pycodestyle: .venv
	poetry run pycodestyle --ignore=E501,E121,E123,E126,E203,E226,E24,E704,W503,W504 $(SOURCEDIRS)

style-check: black-check pylint pycodestyle

mypy: .venv
	poetry run mypy $(SOURCEDIRS)

linters: mypy style-check

check: pytest linters

format: .venv
	poetry run black $(SOURCEDIRS)
