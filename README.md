# syslog-ng CFG Helper

This tool makes configuring [syslog-ng](https://github.com/syslog-ng/syslog-ng) a bit easier by listing the options of each available driver.

The options are generated from [syslog-ng v4.3.0](https://github.com/syslog-ng/syslog-ng/releases/tag/syslog-ng-4.3.0).

## Quickstart

### Install with pipx
```
pipx install syslog-ng-cfg-helper
```

### List the contexts
```
syslog-ng-cfg-helper
```

### List the drivers in a context
```
syslog-ng-cfg-helper --context parser
```

### List the options of a driver
```
syslog-ng-cfg-helper --context parser --driver csv-parser
```

### Example
[![Example](https://github.com/alltilla/syslog-ng-cfg-helper/blob/assets/example.gif)]()

## Development
The tool is still in development, but most of the drivers are supported.

Missing features are:
  * Proper `rewrite` support.
  * Proper `filter` support.
  * Drivers defined in `SCL`s.
  * Drivers defined with confgen.

Any contribution is welcome :)

### Local setup
The project uses [poetry](https://python-poetry.org/) as a dependency management system.

Building of the option database needs the [neologism](https://github.com/alltilla/neologism) pip package, which gets installed by poetry, however it has another dependency, which is [bison](https://www.gnu.org/software/bison/). Make sure to install bison (at least 3.7.6) on you system if you wan't to develop locally. `make bison` can help with that.

The [Makefile](https://github.com/alltilla/syslog-ng-cfg-helper/blob/master/Makefile) consists of some useful commands:
  * `make venv` prepares the venv.
  * `make bison` downloads bison 3.7.6, builds it and installs it under `/usr/local`.
    * You can change the install path with `make bison BISON_INSTALL_PATH=...`
  * `make check` runs the unit tests, style-checkers and linters.
  * `make format` formats the code.
  * `make db` downloads the syslog-ng release tarball and generates the option database.
  * `make package` creates the pip package.

## Community
You can reach out to the syslog-ng community on Discord:

[![Axoflow Discord Server](https://discordapp.com/api/guilds/1082023686028148877/widget.png?style=banner2)](https://discord.gg/E65kP9aZGm)
