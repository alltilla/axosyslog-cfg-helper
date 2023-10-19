ROOT_DIR=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
SOURCEDIRS=$(ROOT_DIR)/syslog_ng_cfg_helper $(ROOT_DIR)/tests

BISON_INSTALL_PATH := /usr/local

SYSLOG_NG_VERSION := 4.4.0
SYSLOG_NG_RELEASE_URL := https://github.com/syslog-ng/syslog-ng/releases/tag/syslog-ng-$(SYSLOG_NG_VERSION)
SYSLOG_NG_TARBALL_URL := https://github.com/syslog-ng/syslog-ng/releases/download/syslog-ng-$(SYSLOG_NG_VERSION)/syslog-ng-$(SYSLOG_NG_VERSION).tar.gz

DATABASE_FILE := $(ROOT_DIR)/syslog_ng_cfg_helper/syslog-ng-cfg-helper.db
WORKING_DIR := $(ROOT_DIR)/working-dir
SYSLOG_NG_WORKING_DIR := $(WORKING_DIR)/syslog-ng-source
SYSLOG_NG_TARBALL := $(WORKING_DIR)/syslog-ng.tar.gz

bison:
	wget https://ftp.gnu.org/gnu/bison/bison-3.7.6.tar.gz -O /tmp/bison.tar.gz
	tar -xzf /tmp/bison.tar.gz -C /tmp
	cd /tmp/bison-3.7.6 && ./configure --prefix=$(BISON_INSTALL_PATH) --disable-nls && make -j && make install

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

pyright:
	poetry run pyright $(SOURCEDIRS)

linters: mypy pyright style-check

check: pytest linters

format:
	poetry run black $(SOURCEDIRS)

$(SYSLOG_NG_TARBALL):
	@mkdir -p $(WORKING_DIR)
	@if [ -n "$(SYSLOG_NG_SOURCE_DIR)" ]; then \
		echo "Generating tarball from syslog-ng source at: $(SYSLOG_NG_SOURCE_DIR)"; \
		cd $(SYSLOG_NG_SOURCE_DIR) && \
		$(SYSLOG_NG_SOURCE_DIR)/dbld/rules tarball; \
		cp `ls -1t $(SYSLOG_NG_SOURCE_DIR)/dbld/build/syslog-ng-* | head -1` $(SYSLOG_NG_TARBALL); \
	else \
		echo "Downloading tarball from: $(SYSLOG_NG_TARBALL_URL)"; \
		wget $(SYSLOG_NG_TARBALL_URL) -O $(SYSLOG_NG_TARBALL); \
	fi

$(SYSLOG_NG_WORKING_DIR): $(SYSLOG_NG_TARBALL)
	@mkdir -p $(SYSLOG_NG_WORKING_DIR)
	tar --strip-components=1 -C $(SYSLOG_NG_WORKING_DIR) -xzf $(SYSLOG_NG_TARBALL)

db: $(SYSLOG_NG_WORKING_DIR)
	poetry run python $(ROOT_DIR)/syslog_ng_cfg_helper/build_db.py \
		--source-dir=$(SYSLOG_NG_WORKING_DIR) \
		--output=$(DATABASE_FILE)

package: db
	poetry build

print-syslog-ng-version:
	@echo $(SYSLOG_NG_VERSION)

print-syslog-ng-release-url:
	@echo $(SYSLOG_NG_RELEASE_URL)

clean:
	rm -rf $(WORKING_DIR) $(DATABASE_FILE)
