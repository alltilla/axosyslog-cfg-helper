from pathlib import Path

from axosyslog_cfg_helper.module_loader.load_modules import __get_token_resolutions


def test_get_token_resolutions_resolves_include_through_include_dirs(tmp_path: Path) -> None:
    lib_dir = tmp_path / "lib"
    modules_dir = tmp_path / "modules"
    (lib_dir / "x").mkdir(parents=True)
    (modules_dir / "x").mkdir(parents=True)

    (lib_dir / "x" / "y-parser.h").write_text('#define Y_KEYWORDS \\\n  { "ip", KW_IP }, \\\n  { "port", KW_PORT }\n')
    (modules_dir / "x" / "y-parser.h").write_text("void y_parser_init(void);\n")

    parser_file = modules_dir / "x" / "y-parser.c"
    parser_file.write_text(
        '#include "x/y-parser.h"\n'
        "static CfgLexerKeyword y_keywords[] = {\n"
        '  { "y", KW_Y },\n'
        "  Y_KEYWORDS,\n"
        "  { NULL }\n"
        "};\n"
    )

    resolutions = __get_token_resolutions(parser_file, (lib_dir, modules_dir))

    assert resolutions == {"KW_IP": {"ip"}, "KW_PORT": {"port"}, "KW_Y": {"y"}}
