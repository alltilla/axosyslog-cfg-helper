from pathlib import Path

from axosyslog_cfg_helper.driver_db import Driver, DriverDB, Option
from axosyslog_cfg_helper.module_loader.load_scl import (
    _enclosing_driver_call,
    _parse_file,
    _split_params,
    _strip_comments,
    load_scl,
)


def _write(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_strip_comments_keeps_string_contents() -> None:
    text = '# this is a comment\nblock destination foo(opt("a # b")) { }'
    stripped = _strip_comments(text)
    assert "# this is a comment" not in stripped
    assert '"a # b"' in stripped


def test_split_params_basic() -> None:
    params = _split_params('url() index("") workers(4) ...')
    assert [p.name for p in params] == ["url", "index", "workers"]
    assert [p.default for p in params] == ["", '""', "4"]


def test_split_params_nested_parens_in_default() -> None:
    params = _split_params('tmpl("$(format-json --scope all)") timeout(10)')
    assert params[0].name == "tmpl"
    assert "format-json" in (params[0].default or "")
    assert params[1].name == "timeout"


def test_enclosing_driver_call_simple() -> None:
    body = "http(url(`u`) `__VARARGS__`)"
    assert _enclosing_driver_call(body, body.index("__VARARGS__")) == "http"


def test_enclosing_driver_call_nested() -> None:
    body = "parser { app-parser(topic(syslog) `__VARARGS__`); };"
    assert _enclosing_driver_call(body, body.index("__VARARGS__")) == "app-parser"


def test_enclosing_driver_call_backticked_name() -> None:
    body = "`kafka-implementation`(`__VARARGS__`);"
    # backticked driver names are pattern E; treat as unresolvable
    assert _enclosing_driver_call(body, body.index("__VARARGS__")) is None


def test_enclosing_driver_call_no_enclosing() -> None:
    body = "destination { pipe(p); `__VARARGS__`; };"
    assert _enclosing_driver_call(body, body.index("__VARARGS__")) is None


def test_parse_file_declared_params_no_varargs(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "x.conf",
        """
        block rewrite mymask(value() template("$MSG")) {
            subst("foo", "bar", value(`value`));
        };
        """,
    )
    blocks = _parse_file(path)
    assert len(blocks) == 1
    block = blocks[0]
    assert (block.context, block.name) == ("rewrite", "mymask")
    assert block.has_varargs is False
    assert block.base_driver is None
    assert [p.name for p in block.params] == ["value", "template"]


def test_parse_file_direct_driver_wrap(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "x.conf",
        """
        block destination wrap(url() ...) {
            http(url(`url`) `__VARARGS__`);
        };
        """,
    )
    blocks = _parse_file(path)
    assert blocks[0].has_varargs is True
    assert blocks[0].base_driver == "http"


def test_parse_file_scl_to_scl_chain(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "a.conf",
        "block destination inner(a() ...) { http(`__VARARGS__`); };",
    )
    _write(
        tmp_path,
        "b.conf",
        "block destination outer(b() ...) { inner(`__VARARGS__`); };",
    )

    grammar_db = DriverDB()
    base = Driver("destination", "http")
    base.add_option(Option(name="batch-lines", params={("<positive-integer>",)}))
    grammar_db.add_driver(base)

    out = load_scl(tmp_path, grammar_db)

    outer = out.get_driver("destination", "outer")
    option_names = {o.name for o in outer.options}
    # declared param of outer + inherited from inner -> http chain
    assert "b" in option_names
    assert "batch-lines" in option_names


def test_unresolvable_block_emitted_with_declared_params_only(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "x.conf",
        "block destination weird(only-this()) { destination { something; `__VARARGS__`; }; };",
    )
    out = load_scl(tmp_path, DriverDB())
    driver = out.get_driver("destination", "weird")
    option_names = {o.name for o in driver.options}
    assert option_names == {"only-this"}


def test_load_scl_missing_dir_returns_empty(tmp_path: Path) -> None:
    out = load_scl(tmp_path / "does-not-exist", DriverDB())
    assert not list(out.contexts)


def test_multiline_block_header(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "x.conf",
        """
        block destination big(
            opt1()
            opt2("default value with (parens) inside")
            opt3(42)
            ...
        ) {
            http(`__VARARGS__`);
        };
        """,
    )
    blocks = _parse_file(path)
    assert len(blocks) == 1
    assert [p.name for p in blocks[0].params] == ["opt1", "opt2", "opt3"]
    assert blocks[0].base_driver == "http"
