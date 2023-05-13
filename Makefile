ROOT_DIR=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
SOURCEDIRS=$(ROOT_DIR)/syslog_ng_cfg_helper $(ROOT_DIR)/tests

venv:
	poetry install

pytest:
	poetry run pytest $(SOURCEDIRS)

black-check:
	poetry run black --check $(SOURCEDIRS)

pylint:
	poetry run pylint --rcfile=$(ROOT_DIR)/.pylintrc $(SOURCEDIRS)

pycodestyle:
	poetry run pycodestyle --ignore=E501,E121,E123,E126,E203,E226,E24,E704,W503,W504 $(SOURCEDIRS)

style-check: black-check pylint pycodestyle

mypy:
	poetry run mypy $(SOURCEDIRS)

linters: mypy style-check

check: pytest linters

format:
	poetry run black $(SOURCEDIRS)

db:
	poetry run python $(ROOT_DIR)/syslog_ng_cfg_helper/build_db.py \
		--source-dir=$(or $(SOURCE_DIR),$(ROOT_DIR)/syslog-ng) \
		--output=$(or $(OUTPUT),$(ROOT_DIR)/syslog_ng_cfg_helper/syslog-ng-cfg-helper.db)
