ROOT_DIR=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
SOURCEDIRS=$(ROOT_DIR)/syslog_ng_cfg_helper $(ROOT_DIR)/tests

SYSLOG_NG_TARBALL_URL := https://github.com/syslog-ng/syslog-ng/releases/download/syslog-ng-4.2.0/syslog-ng-4.2.0.tar.gz
SYSLOG_NG_SOURCE_DIR := $(ROOT_DIR)/syslog-ng
DATABASE_FILE := $(ROOT_DIR)/syslog_ng_cfg_helper/syslog-ng-cfg-helper.db

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
ifeq ("$(wildcard $(ROOT_DIR)/syslog-ng.tar.gz)","")
	rm -rf $(SYSLOG_NG_SOURCE_DIR)
	mkdir $(SYSLOG_NG_SOURCE_DIR)
	wget $(SYSLOG_NG_TARBALL_URL) -O $(SYSLOG_NG_SOURCE_DIR).tar.gz
	tar --strip-components=1 -C $(SYSLOG_NG_SOURCE_DIR) -xzf $(ROOT_DIR)/syslog-ng.tar.gz
endif
	poetry run python $(ROOT_DIR)/syslog_ng_cfg_helper/build_db.py \
		--source-dir=$(SYSLOG_NG_SOURCE_DIR) \
		--output=$(DATABASE_FILE)

clean:
	rm -rf $(SYSLOG_NG_SOURCE_DIR)
	rm -f $(SYSLOG_NG_SOURCE_DIR).tar.gz
