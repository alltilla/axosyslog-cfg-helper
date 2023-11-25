import re

from pathlib import Path

from .driver_db import DriverDB, Driver, Option

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
    def parse_strcasecmp_choice(driver: Driver, option_name: str, source_path: Path, func_pattern: str) -> None:
        with source_path.open("r", encoding="utf-8") as file:
            func = re.findall(func_pattern, file.read().replace("\n", ""))[0]
            choice_regex = re.compile(r'strcasecmp\([^,]+, "([^"]+)"\)')
            for choice in choice_regex.finditer(func):
                driver.add_option(Option(option_name, {(choice.group(1),)}))

    def amqp() -> None:
        parse_strcasecmp_choice(
            driver=driver_db.get_driver("destination", "amqp"),
            option_name="auth-method",
            source_path=Path(modules_dir, "afamqp", "afamqp.c"),
            func_pattern=r"gbooleanafamqp_dd_set_auth_method(.*?)}",
        )

    def loki() -> None:
        parse_strcasecmp_choice(
            driver=driver_db.get_driver("destination", "loki"),
            option_name="timestamp",
            source_path=Path(modules_dir, "grpc", "loki", "loki-dest.hpp"),
            func_pattern=r"  bool set_timestamp(.*?)  }",
        )

    amqp()
    loki()
