import re

from pathlib import Path
from typing import Optional

from .driver_db import Block, DriverDB, Option

TYPES = (
    ("nonnegative_integer", "<nonnegative-integer>"),
    ("optional_arrow", "=>"),
    ("python_yesno", "<python-yesno>"),
    ("path", "<path>"),
    ("positive_integer", "<positive-integer>"),
    ("string", "<string>"),
    ("string_list", "<string-list>"),
    ("string_or_number", "<string-or-number>"),
    ("template_content", "<template-content>"),
    ("yesno", "<yesno>"),
    ("yesnoauto", "<yesnoauto>"),
    ("yesnostrict", "<yesno>"),
    ("LL_ARROW", "=>"),
    ("LL_NUMBER", "<number>"),
    ("LL_FLOAT", "<float>"),
    ("LL_IDENTIFIER", "<identifier>"),
    ("LL_PLUGIN", "<plugin>"),
    ("LL_TEMPLATE_REF", "<template-reference>"),
)

PLUGIN_CONTEXTS = {
    "inner-src": "source",
    "inner-dest": "destination",
}

EXCLUSIVE_PLUGINS = {
    "python-http-header": {"http"},
    "azure-auth-header": {"http"},
    "http-test-slots": {"http"},
    "tls-test-validation": {"network", "tcp", "tcp6", "syslog"},
    "ebpf": {"udp", "udp6"},
    "cloud-auth": {"http"},
}


def set_string_param_choices(driver_db: DriverDB, modules_dir: Path) -> None:
    def parse_strcasecmp_choice(block: Block, option_name: Optional[str], source_path: Path, func_pattern: str) -> None:
        with source_path.open("r", encoding="utf-8") as file:
            func = re.findall(func_pattern, file.read().replace("\n", ""))[0]
            choice_regex = re.compile(r'strcasecmp\([^,]+, "([^"]+)"\)')
            for choice in choice_regex.finditer(func):
                block.add_option(Option(option_name, {(choice.group(1).replace("_", "-"),)}))

    def amqp() -> None:
        parse_strcasecmp_choice(
            block=driver_db.get_driver("destination", "amqp"),
            option_name="auth-method",
            source_path=Path(modules_dir, "afamqp", "afamqp.c"),
            func_pattern=r"gbooleanafamqp_dd_set_auth_method(.*?)}",
        )

    def db_parser() -> None:
        parse_strcasecmp_choice(
            block=driver_db.get_driver("parser", "db-parser"),
            option_name="inject-mode",
            source_path=Path(modules_dir, "correlation", "stateful-parser.c"),
            func_pattern=r"intstateful_parser_lookup_inject_mode(.*?)}",
        )

    def example_random_generator() -> None:
        parse_strcasecmp_choice(
            block=driver_db.get_driver("source", "example-random-generator"),
            option_name="type",
            source_path=Path(
                modules_dir, "examples", "sources", "threaded-random-generator", "threaded-random-generator.c"
            ),
            func_pattern=r"gbooleanthreaded_random_generator_sd_set_type(.*?)}",
        )

    def grouping_by() -> None:
        driver = driver_db.get_driver("parser", "grouping-by")
        parse_strcasecmp_choice(
            block=driver,
            option_name="inject-mode",
            source_path=Path(modules_dir, "correlation", "stateful-parser.c"),
            func_pattern=r"intstateful_parser_lookup_inject_mode(.*?)}",
        )
        parse_strcasecmp_choice(
            block=driver.get_block("aggregate"),
            option_name="inherit-mode",
            source_path=Path(modules_dir, "correlation", "synthetic-message.c"),
            func_pattern=r"intsynthetic_message_lookup_inherit_mode(.*?)}",
        )
        parse_strcasecmp_choice(
            block=driver,
            option_name="scope",
            source_path=Path(modules_dir, "correlation", "correlation-key.c"),
            func_pattern=r"gintcorrelation_key_lookup_scope(.*?)}",
        )

    def loki() -> None:
        parse_strcasecmp_choice(
            block=driver_db.get_driver("destination", "loki"),
            option_name="timestamp",
            source_path=Path(modules_dir, "grpc", "loki", "loki-dest.hpp"),
            func_pattern=r"  bool set_timestamp(.*?)  }",
        )

    def riemann() -> None:
        parse_strcasecmp_choice(
            block=driver_db.get_driver("destination", "riemann").get_block("type"),
            option_name=None,
            source_path=Path(modules_dir, "riemann", "riemann.c"),
            func_pattern=r"gbooleanriemann_dd_set_connection_type(.*?)}",
        )

    def snmp() -> None:
        driver = driver_db.get_driver("destination", "snmp")
        driver.add_option(Option("version", {("v2c",), ("v3",)}))
        driver.add_option(Option("auth-algorithm", {("SHA",)}))
        driver.add_option(Option("enc-algorithm", {("AES",)}))

    def wildcard_file() -> None:
        parse_strcasecmp_choice(
            block=driver_db.get_driver("source", "wildcard-file"),
            option_name="monitor-method",
            source_path=Path(modules_dir, "affile", "directory-monitor-factory.c"),
            func_pattern=r"MonitorMethoddirectory_monitor_factory_get_monitor_method(.*?)}DirectoryMonitorConstructor",
        )

    amqp()
    db_parser()
    example_random_generator()
    grouping_by()
    loki()
    riemann()
    snmp()
    wildcard_file()
