#!/bin/bash
set -euo pipefail

get_latest_version() {
  local api_response
  api_response=$(curl -s -H "Accept: application/vnd.github.v3+json" "https://api.github.com/repos/axoflow/axosyslog/releases/latest")

  if [ $? -ne 0 ]; then
    echo "Failed to fetch latest release from GitHub API" >&2
    return 1
  fi

  echo "$api_response" | grep -o '"tag_name": *"[^"]*"' | sed 's/"tag_name": *"axosyslog-\([0-9.]*\)"/\1/'
}

get_current_version() {
  grep "AXOSYSLOG_VERSION := " Makefile | sed 's/AXOSYSLOG_VERSION := \(.*\)/\1/'
}

update_makefile() {
  local old_version="$1"
  local new_version="$2"

  sed -i "s/AXOSYSLOG_VERSION := ${old_version}/AXOSYSLOG_VERSION := ${new_version}/g" Makefile
}

update_readme() {
  local old_version="$1"
  local new_version="$2"

  sed -i "s/AxoSyslog v${old_version}/AxoSyslog v${new_version}/g" README.md
  sed -i "s/axosyslog-${old_version}/axosyslog-${new_version}/g" README.md
}

main() {
  current_version=$(get_current_version)
  if [ $? -ne 0 ] || [ -z "$current_version" ]; then
    echo "Failed to get current axosyslog version" >&2
    exit 1
  fi

  latest_version=$(get_latest_version)
  if [ $? -ne 0 ] || [ -z "$latest_version" ]; then
    echo "Failed to get latest axosyslog version" >&2
    exit 1
  fi

  if [ "$current_version" = "$latest_version" ]; then
    echo "Already using the latest version"
    exit 0
  fi

  git switch -c axosyslog-upgrade-"${latest_version}"

  update_makefile "$current_version" "$latest_version"
  update_readme "$current_version" "$latest_version"
  git commit -asm "axosyslog: generate from ${latest_version}"

  poetry version minor
  git commit -asm "version: bump to $(poetry version -s)"
}

main "$@"
