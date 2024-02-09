TYPES = (
    ("nonnegative_float", "<nonnegative-float>"),
    ("nonnegative_integer", "<nonnegative-integer>"),
    ("optional_arrow", "=>"),
    ("python_yesno", "<python-yesno>"),
    ("path", "<path>"),
    ("positive_float", "<positive-float>"),
    ("positive_integer", "<positive-integer>"),
    ("string", "<string>"),
    ("string_list", "<string-list>"),
    ("string_or_number", "<string-or-number>"),
    ("template_content", "<template-content>"),
    ("template_content_list", "<template-content-list>"),
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
