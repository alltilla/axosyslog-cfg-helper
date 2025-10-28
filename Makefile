ROOT_DIR=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
SOURCEDIRS=$(ROOT_DIR)/axosyslog_cfg_helper $(ROOT_DIR)/tests

BISON_INSTALL_PATH := /usr/local

AXOSYSLOG_VERSION := 4.19.1
AXOSYSLOG_RELEASE_URL := https://github.com/axoflow/axosyslog/releases/tag/axosyslog-$(AXOSYSLOG_VERSION)
AXOSYSLOG_TARBALL_URL := https://github.com/axoflow/axosyslog/releases/download/axosyslog-$(AXOSYSLOG_VERSION)/axosyslog-$(AXOSYSLOG_VERSION).tar.gz

DATABASE_FILE := $(ROOT_DIR)/axosyslog_cfg_helper/axosyslog-cfg-helper.db
WORKING_DIR := $(ROOT_DIR)/working-dir
AXOSYSLOG_WORKING_DIR := $(WORKING_DIR)/axosyslog-source
AXOSYSLOG_TARBALL := $(WORKING_DIR)/axosyslog.tar.gz

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

$(AXOSYSLOG_TARBALL):
	@mkdir -p $(WORKING_DIR)
	@if [ -n "$(AXOSYSLOG_SOURCE_DIR)" ]; then \
		echo "Generating tarball from axosyslog source at: $(AXOSYSLOG_SOURCE_DIR)"; \
		cd $(AXOSYSLOG_SOURCE_DIR) && \
		$(AXOSYSLOG_SOURCE_DIR)/dbld/rules tarball; \
		cp `ls -1t $(AXOSYSLOG_SOURCE_DIR)/dbld/build/axosyslog-* | head -1` $(AXOSYSLOG_TARBALL); \
	else \
		echo "Downloading tarball from: $(AXOSYSLOG_TARBALL_URL)"; \
		wget $(AXOSYSLOG_TARBALL_URL) -O $(AXOSYSLOG_TARBALL); \
	fi

$(AXOSYSLOG_WORKING_DIR): $(AXOSYSLOG_TARBALL)
	@mkdir -p $(AXOSYSLOG_WORKING_DIR)
	tar --strip-components=1 -C $(AXOSYSLOG_WORKING_DIR) -xzf $(AXOSYSLOG_TARBALL)

db: $(AXOSYSLOG_WORKING_DIR)
	poetry run python $(ROOT_DIR)/axosyslog_cfg_helper/build_db.py \
		--source-dir=$(AXOSYSLOG_WORKING_DIR) \
		--output=$(DATABASE_FILE)

diff:
	@if [ -z "$(OUTPUT)" ]; then \
		echo "OUTPUT must be set"; \
		false; \
	fi
	@mkdir -p $(WORKING_DIR)
	rm -rf $(WORKING_DIR)/axosyslog-cfg-helper-latest $(WORKING_DIR)/axosyslog-cfg-helper-latest.tar.gz
	wget -q \
		$(shell gh api repos/alltilla/axosyslog-cfg-helper/releases/latest | jq -r '.assets[] | select(.name | contains ("tar.gz")) | .browser_download_url') \
		-O $(WORKING_DIR)/axosyslog-cfg-helper-latest.tar.gz
	mkdir -p $(WORKING_DIR)/axosyslog-cfg-helper-latest
	tar -xz \
		-f $(WORKING_DIR)/axosyslog-cfg-helper-latest.tar.gz \
		-C $(WORKING_DIR)/axosyslog-cfg-helper-latest \
		--strip-components=1
	poetry run python axosyslog_cfg_helper/generate_diff.py \
		-o $(WORKING_DIR)/axosyslog-cfg-helper-latest/axosyslog_cfg_helper/axosyslog-cfg-helper.db \
		-n $(DATABASE_FILE) > $(OUTPUT)

package: db
	poetry build

print-axosyslog-version:
	@echo $(AXOSYSLOG_VERSION)

print-axosyslog-release-url:
	@echo $(AXOSYSLOG_RELEASE_URL)

clean:
	rm -rf $(WORKING_DIR) $(DATABASE_FILE)
