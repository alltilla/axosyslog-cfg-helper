# syslog-ng CFG Helper

This tool makes configuring [syslog-ng](https://github.com/syslog-ng/syslog-ng) a bit easier by listing the options of each available driver.

The options are generated from [syslog-ng v4.2.0](https://github.com/syslog-ng/syslog-ng/releases/tag/syslog-ng-4.2.0).

## Quickstart

### Install with pipx
```
pipx install syslog-ng-cfg-helper
```

### List the contexts
```
syslog-ng-cfg-helper
```
```
Valid contexts:
  destination
  filter
  options
  parser
  rewrite
  source
Print the drivers of CONTEXT with `--context CONTEXT`.
```

### List the drivers in a context
```
syslog-ng-cfg-helper -c destination
```
```
Drivers of context 'destination':
  amqp
  example-destination
  fifo
  file
  http
  java
...
Print the options of DRIVER with `--context destination --driver DRIVER`.
```

### List the options of a driver
```
syslog-ng-cfg-helper -c destination -d http
```
```
http(
    accept-redirects(<yesno>)
    azure-auth-header(
        <path>(<string>)
        content-type(<string>)
        method(<string>)
        secret(<string>)
        workspace-id(<string>)
    )
    batch-bytes(<nonnegative-integer>)
    batch-lines(<nonnegative-integer>)
    batch-timeout(<positive-integer>)
    body(<template-content>)
    body-prefix(<string>)
    body-suffix(<string>)
    ca-dir(<string>)
    ca-file(<path>)
    cert-file(<path>)
...
```

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

The [`Makefile`](https://github.com/alltilla/syslog-ng-cfg-helper/blob/master/Makefile) consists of some useful commands:
  * `make venv` prepares the venv.
  * `make check` runs the unit tests, style-checkers and linters.
  * `make format` formats the code.
  * `make db` download the syslog-ng release tarball and generates the option database.
  * `make package` creates the pip package.

## Community
You can reach out to the syslog-ng community on Discord:

[![Axoflow Discord Server](https://discordapp.com/api/guilds/1082023686028148877/widget.png?style=banner2)](https://discord.gg/E65kP9aZGm)
