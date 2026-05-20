from pathlib import Path

from axosyslog_cfg_helper.driver_db import Block, Driver, DriverDB, Option
from axosyslog_cfg_helper.module_loader.load_scl import (
    _parse_file,
    _scan_body,
    _split_params,
    _strip_comments,
    _varargs_base,
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


def test_varargs_base_simple() -> None:
    refs = _scan_body("http(url(`u`) `__VARARGS__`)")
    assert _varargs_base(refs) == "http"


def test_varargs_base_nested() -> None:
    refs = _scan_body("parser { app-parser(topic(syslog) `__VARARGS__`); };")
    assert _varargs_base(refs) == "app-parser"


def test_varargs_base_backticked_name() -> None:
    refs = _scan_body("`kafka-implementation`(`__VARARGS__`);")
    # backticked driver names are pattern E; treat as unresolvable
    assert _varargs_base(refs) is None


def test_varargs_base_no_enclosing() -> None:
    refs = _scan_body("destination { pipe(p); `__VARARGS__`; };")
    assert _varargs_base(refs) is None


def test_scan_body_captures_refs_with_string_state() -> None:
    body = 'http(url("`a`/x") body(`b`) cloud-auth(azure(monitor(`c`))) `__VARARGS__`);'
    refs = {r.name: r for r in _scan_body(body)}
    assert refs["a"].in_string is True
    assert refs["a"].stack == ["http", "url"]
    assert refs["b"].in_string is False
    assert refs["b"].stack == ["http", "body"]
    assert refs["c"].in_string is False
    assert refs["c"].stack == ["http", "cloud-auth", "azure", "monitor"]
    assert refs["__VARARGS__"].stack == ["http"]


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


def _http_with_auth_and_url(template_params: bool = False) -> Driver:
    """Construct a base http driver with the structure azure_monitor wraps:
    cloud-auth(azure(monitor(app-id, app-secret, ...))), url(<string>), body(<template>).
    """
    http = Driver("destination", "http")
    http.add_option(Option(name="url", params={("<string>",)}))
    http.add_option(Option(name="body", params={("<template-content>",), ("<template-reference>",)}))
    cloud_auth = Block("cloud-auth")
    azure = Block("azure")
    monitor = Block("monitor")
    monitor.add_option(Option(name="app-id", params={("<string>",)}))
    monitor.add_option(Option(name="app-secret", params={("<string>",)}))
    monitor.add_option(Option(name="tenant-id", params={("<string>",)}))
    monitor.add_option(Option(name="scope", params={("<string>",)}))
    azure.add_block(monitor)
    cloud_auth.add_block(azure)
    http.add_block(cloud_auth)
    if template_params:
        http.add_option(Option(name="batch-lines", params={("<positive-integer>",)}))
    return http


def test_consumption_block_inflates_declared_param_with_subblock(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "x.conf",
        "block destination wrap(auth() ...) { http(cloud-auth(azure(monitor(`auth`))) `__VARARGS__`); };",
    )
    grammar_db = DriverDB()
    grammar_db.add_driver(_http_with_auth_and_url())
    out = load_scl(tmp_path, grammar_db)
    driver = out.get_driver("destination", "wrap")
    block_names = {b.name for b in driver.blocks}
    assert "auth" in block_names
    assert "cloud-auth" not in block_names
    auth_block = driver.get_block("auth")
    auth_option_names = {o.name for o in auth_block.options}
    assert auth_option_names == {"app-id", "app-secret", "tenant-id", "scope"}


def test_consumption_option_inflates_declared_param_with_option_params(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "x.conf",
        "block destination wrap(template() ...) { http(body(`template`) `__VARARGS__`); };",
    )
    grammar_db = DriverDB()
    grammar_db.add_driver(_http_with_auth_and_url())
    out = load_scl(tmp_path, grammar_db)
    driver = out.get_driver("destination", "wrap")
    option_names = {o.name for o in driver.options}
    assert "template" in option_names
    assert "body" not in option_names
    template = next(o for o in driver.options if o.name == "template")
    assert {("<template-content>",), ("<template-reference>",)} == set(template.params)


def test_string_interp_consumes_enclosing_option_but_does_not_inflate(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "x.conf",
        'block destination wrap(host() ...) { http(url("https://`host`/foo") `__VARARGS__`); };',
    )
    grammar_db = DriverDB()
    grammar_db.add_driver(_http_with_auth_and_url())
    out = load_scl(tmp_path, grammar_db)
    driver = out.get_driver("destination", "wrap")
    option_names = {o.name for o in driver.options}
    assert "url" not in option_names
    host = next(o for o in driver.options if o.name == "host")
    # Stays opaque -- url could not meaningfully inflate one of several string-shared params.
    assert set(host.params) == {("<empty>",)}


def test_consumption_hyphen_underscore_normalized(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "x.conf",
        "block destination wrap(batch_lines() ...) { http(batch-lines(`batch_lines`) `__VARARGS__`); };",
    )
    grammar_db = DriverDB()
    grammar_db.add_driver(_http_with_auth_and_url(template_params=True))
    out = load_scl(tmp_path, grammar_db)
    driver = out.get_driver("destination", "wrap")
    option_names = {o.name for o in driver.options}
    # SCL-derived names are emitted with hyphens; the underscore declared
    # `batch_lines` and the consumed hyphenated `batch-lines` from http
    # collapse to a single canonical `batch-lines` option that carries the
    # inflated type info from http.
    assert "batch_lines" not in option_names
    assert "batch-lines" in option_names
    batch_lines = next(o for o in driver.options if o.name == "batch-lines")
    assert set(batch_lines.params) == {("<positive-integer>",)}


def test_hardcoded_inheritance_excludes_drop_base_options(tmp_path: Path, monkeypatch) -> None:
    from axosyslog_cfg_helper.module_loader import load_scl as load_scl_mod

    monkeypatch.setattr(load_scl_mod, "SCL_INHERITANCE_EXCLUDES", {"http": {"keep-out", "secret-block"}})
    _write(
        tmp_path,
        "x.conf",
        "block destination wrap(only-this() ...) { http(`__VARARGS__`); };",
    )
    grammar_db = DriverDB()
    http = Driver("destination", "http")
    http.add_option(Option(name="keep-out", params={("<string>",)}))
    http.add_option(Option(name="kept", params={("<string>",)}))
    http.add_block(Block("secret-block"))
    grammar_db.add_driver(http)
    out = load_scl_mod.load_scl(tmp_path, grammar_db)
    driver = out.get_driver("destination", "wrap")
    option_names = {o.name for o in driver.options}
    block_names = {b.name for b in driver.blocks}
    assert "keep-out" not in option_names
    assert "secret-block" not in block_names
    assert "kept" in option_names
    assert "only-this" in option_names


def test_consumption_conflicting_paths_keep_consumption_drop_inflation(tmp_path: Path) -> None:
    # The declared param `x` substitutes into two different option positions in
    # the base driver. Inflation cannot pick a single target, so it is dropped
    # but the consumed tops are still removed from inherited.
    _write(
        tmp_path,
        "x.conf",
        "block destination wrap(x() ...) { http(body(`x`) url(`x`) `__VARARGS__`); };",
    )
    grammar_db = DriverDB()
    grammar_db.add_driver(_http_with_auth_and_url())
    out = load_scl(tmp_path, grammar_db)
    driver = out.get_driver("destination", "wrap")
    option_names = {o.name for o in driver.options}
    assert "body" not in option_names
    assert "url" not in option_names
    x = next(o for o in driver.options if o.name == "x")
    assert set(x.params) == {("<empty>",)}


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
