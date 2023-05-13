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
}
