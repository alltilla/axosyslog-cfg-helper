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

from axosyslog_cfg_helper.driver_db import Driver, DriverDB, Option

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
class _SclBlock:  # pylint: disable=too-many-instance-attributes
    context: str
    name: str
    params: List[_Param]
    has_varargs: bool
    base_driver: Optional[str]
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


def _enclosing_driver_call(body: str, varargs_offset: int) -> Optional[str]:  # pylint: disable=too-many-branches
    """Return the identifier preceding the innermost open paren that encloses
    `varargs_offset`, or None if there is no enclosing driver call (e.g. a
    bare `__VARARGS__;` statement at block level).

    A forward scan up to `varargs_offset` accumulates a stack of open parens,
    each tagged with the identifier immediately preceding it. Close parens
    pop the stack. After the scan, the stack top is the innermost enclosing
    call.
    """
    paren_stack: List[Tuple[int, str]] = []  # (paren_index, preceding_identifier)
    i = 0
    n = varargs_offset
    in_string: Optional[str] = None
    while i < n:
        ch = body[i]
        if in_string:
            if ch == "\\" and i + 1 < n:
                i += 2
                continue
            if ch == in_string:
                in_string = None
            i += 1
            continue
        if ch in ('"', "'"):
            in_string = ch
            i += 1
            continue
        if ch == "(":
            # find identifier immediately preceding (skipping whitespace and
            # backticks); identifier may be wrapped in backticks like
            # `kafka-implementation` -- treat the backticked content as the
            # name itself (pattern E).
            j = i - 1
            while j >= 0 and body[j].isspace():
                j -= 1
            ident: str = ""
            if j >= 0 and body[j] == "`":
                # backticked: read backwards to matching opening backtick
                k = j - 1
                while k >= 0 and body[k] != "`":
                    k -= 1
                if k >= 0:
                    ident = "`" + body[k + 1 : j] + "`"
            else:
                end = j + 1
                while j >= 0 and (body[j].isalnum() or body[j] in "_-"):
                    j -= 1
                ident = body[j + 1 : end]
            paren_stack.append((i, ident))
            i += 1
            continue
        if ch == ")":
            if paren_stack:
                paren_stack.pop()
            i += 1
            continue
        i += 1
    if not paren_stack:
        return None
    # Innermost open paren is the last one on the stack.
    _, name = paren_stack[-1]
    if not name or name.startswith("`"):
        # Pattern E (backticked) or no preceding identifier -- not resolvable.
        return None
    return name


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

        has_varargs = _VARARGS_TOKEN in body_text
        base_driver: Optional[str] = None
        if has_varargs:
            base_driver = _enclosing_driver_call(body_text, body_text.find(_VARARGS_TOKEN))
            # Validate that *every* VARARGS occurrence resolves to the same base.
            scan = body_text.find(_VARARGS_TOKEN, body_text.find(_VARARGS_TOKEN) + 1)
            while scan >= 0:
                other = _enclosing_driver_call(body_text, scan)
                if other != base_driver:
                    base_driver = None
                    break
                scan = body_text.find(_VARARGS_TOKEN, scan + 1)

        # Compute line number of the block keyword for diagnostics
        line_no = text.count("\n", 0, idx) + 1
        blocks.append(
            _SclBlock(
                context=context,
                name=name,
                params=params,
                has_varargs=has_varargs,
                base_driver=base_driver,
                file_path=path,
                line=line_no,
            )
        )
        i = next_pos
    return blocks


def _block_to_driver(block: _SclBlock) -> Driver:
    driver = Driver(block.context, block.name)
    for param in block.params:
        # Convert hyphen/underscore unchanged (axosyslog accepts both); use
        # `<empty>` to match the convention used by the grammar loader.
        param_value: Tuple[str, ...] = ("<empty>",)
        driver.add_option(Option(name=param.name, params={param_value}))
    return driver


def _resolve(blocks: List[_SclBlock], grammar_db: DriverDB) -> DriverDB:
    by_key: Dict[Tuple[str, str], _SclBlock] = {(b.context, b.name): b for b in blocks}
    out = DriverDB()

    def resolve(block: _SclBlock, stack: Set[Tuple[str, str]]) -> Optional[Driver]:
        key = (block.context, block.name)
        if key in stack:
            print(f"    SCL cycle detected at {block.file_path}:{block.line} for {key}")
            return None
        driver = _block_to_driver(block)
        if block.has_varargs and block.base_driver:
            base_key = (block.context, block.base_driver)
            base_driver: Optional[Driver] = None
            if base_key in by_key:
                base_driver = resolve(by_key[base_key], stack | {key})
            else:
                try:
                    base_driver = grammar_db.get_driver(block.context, block.base_driver)
                except KeyError:
                    base_driver = None
            if base_driver is not None:
                for opt in base_driver.options:
                    driver.add_option(opt.copy())
                for blk in base_driver.blocks:
                    driver.add_block(blk.copy())
            else:
                print(
                    f"    SCL block {block.context}/{block.name} at "
                    f"{block.file_path}:{block.line}: base driver {block.base_driver!r} not found"
                )
        elif block.has_varargs and not block.base_driver:
            print(
                f"    SCL block {block.context}/{block.name} at {block.file_path}:{block.line}: "
                f"__VARARGS__ present but base driver not resolvable; emitting declared params only"
            )
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
