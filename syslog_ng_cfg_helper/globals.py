import re

from pathlib import Path

from .driver_db import DriverDB, Option

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
    def loki() -> None:
        driver = driver_db.get_driver("destination", "loki")
        with Path(modules_dir, "grpc", "loki", "loki-dest.hpp").open("r", encoding="utf-8") as file:
            set_timestamp_func = re.findall(r"  bool set_timestamp(.*?)  }", file.read().replace("\n", ""))[0]
            timestamp_regex = re.compile(r'strcasecmp\(t, "([^"]+)"\)')
            for timestamp in timestamp_regex.finditer(set_timestamp_func):
                driver.add_option(Option("timestamp", {(timestamp.group(1),)}))

    loki()
