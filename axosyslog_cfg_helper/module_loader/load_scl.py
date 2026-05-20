"""Load SCL (Syslog-ng Configuration Library) block definitions into a DriverDB.

SCL files are .conf-syntax wrappers around grammar-defined drivers:

    block destination foo(opt1() opt2(default) ...) {
        http(url(`opt1`) `__VARARGS__`);
    }

Each `block` becomes a callable driver whose declared parameters are explicit
options and whose `__VARARGS__` slot inherits the options of the innermost
enclosing driver call in the body. Blocks may wrap other blocks; resolution is
topological so SCL-to-SCL chains (e.g. azure_monitor_builtin -> azure_monitor
-> http) end up with the full union of options.

Patterns this loader cannot resolve are emitted with declared params only:
  - `__VARARGS__` inside a named option (e.g. `parameters(__VARARGS__)`)
  - the driver name being a backtick-substituted template variable
  - bare `__VARARGS__;` statements at block level (no enclosing driver call)
See README / follow-up issue for the catalogued cases.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from axosyslog_cfg_helper.driver_db import Block, Driver, DriverDB, Option
from axosyslog_cfg_helper.globals import SCL_INHERITANCE_EXCLUDES

_BLOCK_CONTEXTS = {"destination", "source", "parser", "rewrite", "filter"}
_VARARGS_TOKEN = "__VARARGS__"


@dataclass
class _Param:
    name: str
    # default text as it appears between the parens; empty string if the param
    # was declared with empty parens like `opt()`. None means a literal `...`
    # (varargs marker, not a normal parameter).
    default: Optional[str]


@dataclass
class _BacktickRef:
    """A `name` reference encountered while scanning a block body.

    `stack` records the enclosing driver-call identifiers from outermost to
    innermost at the position of the reference. `in_string` is true when the
    reference appears inside a string literal (e.g. interpolated into a URL
    template). For these, the path to consume in the base driver is `stack`
    itself; for non-string refs, the innermost frame is the option/block the
    reference is "inside" and the SCL declared param replaces it.
    """

    name: str
    stack: List[str]
    in_string: bool


@dataclass
class _SclBlock:  # pylint: disable=too-many-instance-attributes
    context: str
    name: str
    params: List[_Param]
    has_varargs: bool
    base_driver: Optional[str]
    body: str
    refs: List[_BacktickRef]
    file_path: Path
    line: int
    # populated during topological resolution
    resolved: bool = field(default=False)


def _strip_comments(text: str) -> str:
    """Replace `# ...` comments with spaces, leaving string contents untouched."""
    out: List[str] = []
    i = 0
    n = len(text)
    string_char: Optional[str] = None
    while i < n:
        ch = text[i]
        if string_char:
            out.append(ch)
            if ch == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if ch == string_char:
                string_char = None
            i += 1
            continue
        if ch in ('"', "'"):
            string_char = ch
            out.append(ch)
            i += 1
            continue
        if ch == "#":
            # comment runs to end of line
            while i < n and text[i] != "\n":
                i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _find_matching(text: str, start: int, open_ch: str, close_ch: str) -> int:
    """Return index of the close char matching the open char at `start`.

    `text[start]` must equal `open_ch`. Tracks string state. Raises ValueError
    if unbalanced.
    """
    if text[start] != open_ch:
        raise ValueError(f"expected {open_ch!r} at offset {start}, got {text[start]!r}")
    depth = 0
    string_char: Optional[str] = None
    i = start
    while i < len(text):
        ch = text[i]
        if string_char:
            if ch == "\\" and i + 1 < len(text):
                i += 2
                continue
            if ch == string_char:
                string_char = None
            i += 1
            continue
        if ch in ('"', "'"):
            string_char = ch
            i += 1
            continue
        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise ValueError(f"unbalanced {open_ch!r}{close_ch!r} starting at {start}")


def _split_params(text: str) -> List[_Param]:
    """Parse the parameter list between block header parens.

    Entries are whitespace-separated `name(default)` forms. The literal `...`
    indicates the block accepts varargs.
    """
    params: List[_Param] = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch.isspace() or ch == ",":
            i += 1
            continue
        if text.startswith("...", i):
            i += 3
            continue
        if ch == "(":
            # Stray '(' without a name -- skip to its matching ')'.
            close = _find_matching(text, i, "(", ")")
            i = close + 1
            continue
        # Read identifier
        start = i
        while i < n and (text[i].isalnum() or text[i] in "_-"):
            i += 1
        if i == start:
            # unexpected; skip char
            i += 1
            continue
        name = text[start:i]
        # Skip whitespace, then expect '('
        while i < n and text[i].isspace():
            i += 1
        if i < n and text[i] == "(":
            close = _find_matching(text, i, "(", ")")
            default = text[i + 1 : close].strip()
            params.append(_Param(name=name, default=default))
            i = close + 1
        else:
            params.append(_Param(name=name, default=None))
    return params


def _read_ident_before(body: str, paren_index: int) -> str:
    """Return the identifier (possibly backtick-wrapped) immediately preceding
    the `(` at `paren_index`. Returns "" if there is none.
    """
    j = paren_index - 1
    while j >= 0 and body[j].isspace():
        j -= 1
    if j >= 0 and body[j] == "`":
        k = j - 1
        while k >= 0 and body[k] != "`":
            k -= 1
        if k >= 0:
            return "`" + body[k + 1 : j] + "`"
        return ""
    end = j + 1
    while j >= 0 and (body[j].isalnum() or body[j] in "_-"):
        j -= 1
    return body[j + 1 : end]


def _scan_body(body: str) -> List[_BacktickRef]:  # pylint: disable=too-many-branches,too-many-statements
    """Walk `body` once and return every `name` backtick reference together
    with the stack of enclosing driver-call identifiers at its position.
    """
    refs: List[_BacktickRef] = []
    paren_stack: List[str] = []
    in_string: Optional[str] = None
    i = 0
    n = len(body)
    while i < n:
        ch = body[i]
        if in_string:
            if ch == "\\" and i + 1 < n:
                i += 2
                continue
            if ch == "`":
                end = body.find("`", i + 1)
                if end > 0:
                    refs.append(_BacktickRef(name=body[i + 1 : end], stack=list(paren_stack), in_string=True))
                    i = end + 1
                    continue
            if ch == in_string:
                in_string = None
            i += 1
            continue
        if ch in ('"', "'"):
            in_string = ch
            i += 1
            continue
        if ch == "`":
            end = body.find("`", i + 1)
            if end > 0:
                refs.append(_BacktickRef(name=body[i + 1 : end], stack=list(paren_stack), in_string=False))
                i = end + 1
                continue
            i += 1
            continue
        if ch == "(":
            paren_stack.append(_read_ident_before(body, i))
            i += 1
            continue
        if ch == ")":
            if paren_stack:
                paren_stack.pop()
            i += 1
            continue
        i += 1
    return refs


def _varargs_base(refs: List[_BacktickRef]) -> Optional[str]:
    """Resolve the innermost enclosing driver call for every __VARARGS__ ref
    in `refs`. Returns the call's identifier if all occurrences agree, or
    None if there is no enclosing call or the occurrences disagree.
    """
    base: Optional[str] = None
    seen = False
    for ref in refs:
        if ref.name != _VARARGS_TOKEN:
            continue
        seen = True
        if not ref.stack:
            return None
        innermost = ref.stack[-1]
        if not innermost or innermost.startswith("`"):
            return None
        if base is None:
            base = innermost
        elif base != innermost:
            return None
    return base if seen else None


def _parse_file(path: Path) -> List[_SclBlock]:  # pylint: disable=too-many-branches,too-many-locals,too-many-statements
    raw = path.read_text(encoding="utf-8")
    text = _strip_comments(raw)
    blocks: List[_SclBlock] = []
    i = 0
    n = len(text)
    while i < n:
        # Find the next occurrence of the keyword `block` at a word boundary.
        idx = text.find("block", i)
        if idx < 0:
            break
        # word-boundary check
        if idx > 0 and (text[idx - 1].isalnum() or text[idx - 1] in "_-`"):
            i = idx + 1
            continue
        after = idx + len("block")
        if after >= n or not text[after].isspace():
            i = idx + 1
            continue
        # Parse: block <context> <name> ( <params> ) { <body> }
        j = after
        while j < n and text[j].isspace():
            j += 1
        ctx_start = j
        while j < n and (text[j].isalnum() or text[j] in "_-"):
            j += 1
        context = text[ctx_start:j]
        if context not in _BLOCK_CONTEXTS:
            i = idx + 1
            continue
        while j < n and text[j].isspace():
            j += 1
        name_start = j
        while j < n and (text[j].isalnum() or text[j] in "_-"):
            j += 1
        name = text[name_start:j]
        if not name:
            i = idx + 1
            continue
        while j < n and text[j].isspace():
            j += 1
        if j >= n or text[j] != "(":
            i = idx + 1
            continue
        try:
            params_close = _find_matching(text, j, "(", ")")
        except ValueError:
            i = idx + 1
            continue
        params_text = text[j + 1 : params_close]
        params = _split_params(params_text)
        # Find body braces
        k = params_close + 1
        while k < n and text[k].isspace():
            k += 1
        body_text = ""
        if k < n and text[k] == "{":
            try:
                body_close = _find_matching(text, k, "{", "}")
                body_text = text[k + 1 : body_close]
                next_pos = body_close + 1
            except ValueError:
                next_pos = params_close + 1
        else:
            next_pos = params_close + 1

        refs = _scan_body(body_text)
        has_varargs = any(ref.name == _VARARGS_TOKEN for ref in refs)
        base_driver = _varargs_base(refs) if has_varargs else None

        # Compute line number of the block keyword for diagnostics
        line_no = text.count("\n", 0, idx) + 1
        blocks.append(
            _SclBlock(
                context=context,
                name=name,
                params=params,
                has_varargs=has_varargs,
                base_driver=base_driver,
                body=body_text,
                refs=refs,
                file_path=path,
                line=line_no,
            )
        )
        i = next_pos
    return blocks


def _norm(name: str) -> str:
    """Normalize a name for hyphen/underscore-insensitive comparison."""
    return name.replace("_", "-")


def _find_block(node: Block, name: str) -> Optional[Block]:
    norm = _norm(name)
    return next((b for b in node.blocks if _norm(b.name) == norm), None)


def _find_option(node: Block, name: str) -> Optional[Option]:
    norm = _norm(name)
    return next((o for o in node.options if o.name and _norm(o.name) == norm), None)


def _walk_path(base: Block, path: List[str]) -> Optional[object]:
    """Walk `path` inside `base`. Each segment is matched against sub-blocks
    first, then options. Returns the leaf Block or Option, or None if the
    path cannot be fully resolved.
    """
    node: Block = base
    for idx, seg in enumerate(path):
        nb = _find_block(node, seg)
        if nb is not None:
            node = nb
            if idx == len(path) - 1:
                return nb
            continue
        no = _find_option(node, seg)
        if no is not None:
            if idx == len(path) - 1:
                return no
            return None  # options cannot have sub-things
        return None
    return node


def _consumption(block: _SclBlock) -> Tuple[Set[str], Dict[str, List[str]]]:
    """Inspect a block's backtick references and decide which top-level options
    or sub-blocks of the VARARGS base driver are consumed by declared params.

    Returns (consumed_top_names_normalized, inflate_paths_by_param). Params
    that appear inside string literals contribute to consumption (the string-
    bearing option is hidden) but not to inflation. Params with conflicting
    references (same name pointing into multiple distinct paths) are dropped
    from inflation but their consumed tops are kept.
    """
    declared_names = {p.name for p in block.params}
    consumed_top: Set[str] = set()
    inflate: Dict[str, List[str]] = {}
    conflict: Set[str] = set()
    base = block.base_driver
    if base is None:
        return consumed_top, inflate
    for ref in block.refs:
        if ref.name == _VARARGS_TOKEN or ref.name not in declared_names:
            continue
        if not ref.stack or ref.stack[0] != base:
            continue
        path_in_base = ref.stack[1:]
        if not path_in_base:
            continue
        consumed_top.add(_norm(path_in_base[0]))
        if ref.in_string:
            continue
        if ref.name in inflate and inflate[ref.name] != path_in_base:
            conflict.add(ref.name)
        else:
            inflate[ref.name] = path_in_base
    for name in conflict:
        inflate.pop(name, None)
    return consumed_top, inflate


def _inflate_param(driver: Driver, param_name: str, leaf: object) -> None:
    """Replace declared `param_name` option with content derived from `leaf`."""
    if isinstance(leaf, Block):
        try:
            driver.remove_option(param_name)
        except KeyError:
            pass
        new_block = Block(param_name)
        for o in leaf.options:
            new_block.add_option(o.copy())
        for b in leaf.blocks:
            new_block.add_block(b.copy())
        driver.add_block(new_block)
    elif isinstance(leaf, Option):
        try:
            driver.remove_option(param_name)
        except KeyError:
            pass
        driver.add_option(Option(name=param_name, params=set(leaf.params)))


def _build_driver(block: _SclBlock, base_driver: Optional[Driver]) -> Driver:
    driver = Driver(block.context, block.name)
    # Seed declared params with opaque <empty>; consumed ones get replaced.
    for param in block.params:
        driver.add_option(Option(name=param.name, params={("<empty>",)}))
    if base_driver is None:
        return driver
    consumed_top, inflate = _consumption(block)
    hard_excludes = {_norm(n) for n in SCL_INHERITANCE_EXCLUDES.get(block.base_driver or "", set())}
    forbidden = consumed_top | hard_excludes
    for opt in base_driver.options:
        if opt.name is not None and _norm(opt.name) in forbidden:
            continue
        driver.add_option(opt.copy())
    for blk in base_driver.blocks:
        if _norm(blk.name) in forbidden:
            continue
        driver.add_block(blk.copy())
    for param_name, path in inflate.items():
        leaf = _walk_path(base_driver, path)
        if leaf is not None:
            _inflate_param(driver, param_name, leaf)
    return driver


def _resolve(blocks: List[_SclBlock], grammar_db: DriverDB) -> DriverDB:
    by_key: Dict[Tuple[str, str], _SclBlock] = {(b.context, b.name): b for b in blocks}
    out = DriverDB()

    def resolve(block: _SclBlock, stack: Set[Tuple[str, str]]) -> Optional[Driver]:
        key = (block.context, block.name)
        if key in stack:
            print(f"    SCL cycle detected at {block.file_path}:{block.line} for {key}")
            return None
        base_driver: Optional[Driver] = None
        if block.has_varargs and block.base_driver:
            base_key = (block.context, block.base_driver)
            if base_key in by_key:
                base_driver = resolve(by_key[base_key], stack | {key})
            else:
                try:
                    base_driver = grammar_db.get_driver(block.context, block.base_driver)
                except KeyError:
                    base_driver = None
            if base_driver is None:
                print(
                    f"    SCL block {block.context}/{block.name} at "
                    f"{block.file_path}:{block.line}: base driver {block.base_driver!r} not found"
                )
        elif block.has_varargs and not block.base_driver:
            print(
                f"    SCL block {block.context}/{block.name} at {block.file_path}:{block.line}: "
                f"__VARARGS__ present but base driver not resolvable; emitting declared params only"
            )
        driver = _build_driver(block, base_driver)
        out.add_driver(driver)
        block.resolved = True
        return driver

    for block in blocks:
        if not block.resolved:
            resolve(block, set())
    return out


def load_scl(scl_dir: Path, grammar_db: DriverDB) -> DriverDB:
    """Walk `scl_dir` for *.conf files, parse `block` definitions, and emit a
    DriverDB whose drivers include the SCL wrappers with options inherited
    from their VARARGS base driver (looked up in `grammar_db` or in another
    SCL block parsed in this pass).
    """
    if not scl_dir.is_dir():
        return DriverDB()
    blocks: List[_SclBlock] = []
    for conf in sorted(scl_dir.rglob("*.conf")):
        try:
            blocks.extend(_parse_file(conf))
        except (ValueError, OSError, UnicodeDecodeError) as exc:  # pragma: no cover - defensive
            print(f"    SCL parse error in {conf}: {exc}")
    return _resolve(blocks, grammar_db)
