import re

from typing import Dict, List, Optional, Set
from pathlib import Path
from neologism import DCFG, Rule

from axosyslog_cfg_helper.driver_db import Driver, DriverDB, Block, Option
from axosyslog_cfg_helper.globals import EXCLUSIVE_PLUGINS, PLUGIN_CONTEXTS, TYPES
from .parse_sentence import parse_sentence, ParseError


class GrammarFileMissingError(Exception):
    pass


def __find_grammar_files(driver_source_dir: Path) -> Set[Path]:
    grammar_files = set(driver_source_dir.rglob("*-grammar.y"))

    if len(grammar_files) == 0:
        raise GrammarFileMissingError()

    return grammar_files


def __format_types(grammar: DCFG) -> None:
    for type_symbol, formatted_type in TYPES:
        if type_symbol in grammar.symbols:
            grammar.make_symbol_terminal(type_symbol)
            grammar.add_rule(Rule(type_symbol, (formatted_type,)))


def __remove_ifdef(grammar: DCFG) -> None:
    for symbol in {"KW_IFDEF", "KW_ENDIF"}:
        if symbol in grammar.terminals:
            grammar.remove_symbol(symbol)


def __get_token_resolutions_from_struct(struct: str) -> Dict[str, Set[str]]:
    resolutions: Dict[str, Set[str]] = {}
    entry_regex = re.compile(r"{[^{}]+,[^{}]+}")

    for entry_match in entry_regex.finditer(struct):
        entry = entry_match.group(0)[1:-1].replace(" ", "").split(",")
        token = entry[1]
        keyword = entry[0][1:-1].replace("_", "-")
        resolutions.setdefault(token, set()).add(keyword)

    return resolutions


def __get_token_resolutions(parser_file: Path) -> Dict[str, Set[str]]:
    resolutions: Dict[str, Set[str]] = {}

    struct_regex = re.compile(r"CfgLexerKeyword(.*?)};")

    with parser_file.open("r") as file:
        file_content = file.read().replace("\n", "")
        for struct_match in struct_regex.finditer(file_content):
            resolutions.update(__get_token_resolutions_from_struct(struct_match.group(1)))

    return resolutions


def __resolve_tokens_to_keywords(grammar: DCFG, common_parser_file: Path, parser_file: Optional[Path] = None) -> None:
    parser_files: List[Path] = [common_parser_file]
    if parser_file:
        parser_files.append(parser_file)

    for file in parser_files:
        for token, resolutions in __get_token_resolutions(file).items():
            for resolution in resolutions:
                grammar.add_rule(Rule(token, (resolution,)))


def __prepare_module_grammar(module_source_dir: Path, common_parser_file: Path) -> DCFG:
    module_grammar = DCFG()

    for grammar_file in __find_grammar_files(module_source_dir):
        parser_file = Path(str(grammar_file).replace("-grammar.y", "-parser.c"))

        grammar = DCFG()
        grammar.load_yacc_file(str(grammar_file))

        __format_types(grammar)
        __remove_ifdef(grammar)
        __resolve_tokens_to_keywords(grammar, common_parser_file, parser_file)

        module_grammar.load_dcfg(grammar)
        module_grammar.start_symbol = grammar.start_symbol

    return module_grammar


def __merge_blocks_and_options_with_the_same_name(driver_db: DriverDB) -> None:
    def process(block: Block):
        for option in list(block.options):
            try:
                if option.name is None:
                    continue
                inner_block_with_same_name = block.get_block(option.name)
            except KeyError:
                continue

            for params in option.params:
                inner_block_with_same_name.add_option(Option(params={params}))

            block.remove_option(option.name)

        for inner_block in block.blocks:
            process(inner_block)

    for ctx in driver_db.contexts:
        for driver in driver_db.get_drivers_in_context(ctx):
            process(driver)


def __accepts_plugins(driver: Driver) -> bool:
    try:
        positional_option = driver.get_option(None)
    except KeyError:
        return False

    if not ("<plugin>",) in positional_option.params:
        return False

    return True


def __remove_plugin_param_from_driver(driver: Driver) -> None:
    new_params = set(driver.get_option(None).params)
    new_params.remove(("<plugin>",))
    driver.remove_option(None)
    if len(new_params) > 0:
        driver.add_option(Option(params=new_params))


def __connect_inner_plugins(driver_db: DriverDB) -> None:
    for plugin_context, driver_context in PLUGIN_CONTEXTS.items():
        if driver_context not in driver_db.contexts or plugin_context not in driver_db.contexts:
            continue

        plugins = driver_db.get_drivers_in_context(plugin_context)
        drivers = driver_db.get_drivers_in_context(driver_context)

        for driver in drivers:
            if not __accepts_plugins(driver):
                continue

            __remove_plugin_param_from_driver(driver)

            for plugin in plugins:
                if plugin.name in EXCLUSIVE_PLUGINS and driver.name not in EXCLUSIVE_PLUGINS[plugin.name]:
                    continue

                driver.add_block(plugin.to_block())

        driver_db.remove_context(plugin_context)


def __post_process_driver_db(driver_db: DriverDB) -> None:
    __merge_blocks_and_options_with_the_same_name(driver_db)
    __connect_inner_plugins(driver_db)


def __load_drivers_in_module(module_source_dir: Path, common_parser_file: Path) -> DriverDB:
    drivers = DriverDB()

    try:
        grammar = __prepare_module_grammar(module_source_dir, common_parser_file)
    except GrammarFileMissingError:
        print("    Skipping module: Grammar file is missing.")
        return DriverDB()

    for sentence in grammar.sentences:
        try:
            driver_slice = parse_sentence(sentence)
            drivers.add_driver(driver_slice)
        except ParseError as exception:
            print(f"    Cannot parse sentence '{' '.join(sentence)}': {exception}")

    return drivers


def __load_common_grammar_file(lib_dir: Path, common_parser_file: Path) -> DriverDB:
    grammar = DCFG()
    grammar.load_yacc_file(str(lib_dir / "cfg-grammar.y"))
    __format_types(grammar)
    __remove_ifdef(grammar)
    __resolve_tokens_to_keywords(grammar, common_parser_file)

    driver_db = DriverDB()
    global_options = Driver("options", DriverDB.GLOBAL_OPTIONS_DRIVER_NAME)
    driver_db.add_driver(global_options)

    for sentence in grammar.sentences:
        if not sentence or sentence[0] != "options":
            continue
        try:
            driver_slice = parse_sentence(sentence)
            driver_db.add_driver(driver_slice)
        except ParseError as exception:
            print(f"    Cannot parse sentence '{' '.join(sentence)}': {exception}")

    return driver_db


def load_modules(lib_dir: Path, modules_dir: Path) -> DriverDB:
    common_parser_file = lib_dir / "cfg-parser.c"
    driver_db = DriverDB()
    module_source_dirs: List[Path] = list(filter(lambda path: path.is_dir(), modules_dir.glob("*")))

    driver_db.merge(__load_common_grammar_file(lib_dir, common_parser_file))

    for module_source_dir in module_source_dirs:
        print(f"Loading module '{module_source_dir.name}'.")

        drivers = __load_drivers_in_module(module_source_dir, common_parser_file)
        driver_db.merge(drivers)

    __post_process_driver_db(driver_db)

    return driver_db
