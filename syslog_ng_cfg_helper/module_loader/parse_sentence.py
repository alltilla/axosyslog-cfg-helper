from typing import Set, Tuple
from syslog_ng_cfg_helper.driver_db import Block, DriverDB, Driver, Option


class ParseError(Exception):
    pass


def __is_type(symbol: str) -> bool:
    return symbol.startswith("<") and symbol.endswith(">")


def __is_block(sentence: Tuple[str, ...]) -> bool:
    if len(sentence) < 3:
        return False

    if __is_type(sentence[0]):
        return False

    if sentence[1] != "(":
        return False

    for symbol in sentence[2:]:
        if symbol == ")":
            return False

        if symbol == "(":
            return True

    raise ParseError(f"Block is not closed: {sentence}")


def __is_arrowed_option(sentence: Tuple[str, ...]) -> bool:
    if len(sentence) < 3:
        return False

    if sentence[1] != "=>":
        return False

    return True


def __is_named_option(sentence: Tuple[str, ...]) -> bool:
    if len(sentence) < 3:
        return False

    if sentence[1] != "(":
        return False

    return True


def __is_positional_option(sentence: Tuple[str, ...]) -> bool:
    if len(sentence) < 1:
        raise ParseError(f"Too short sentence: {sentence}")

    return __is_type(sentence[0])


def __get_block_content(sentence: Tuple[str, ...]) -> Tuple[str, ...]:
    expected_number_of_right_braces = 0
    number_of_right_braces = 0

    for i, symbol in enumerate(sentence):
        if symbol == "(":
            expected_number_of_right_braces += 1

        if symbol == ")":
            number_of_right_braces += 1

        if number_of_right_braces == expected_number_of_right_braces and expected_number_of_right_braces != 0:
            return sentence[2:i]

    raise ParseError(f"Block is not closed: {sentence}")


def __get_named_option_name(sentence: Tuple[str, ...]) -> str:
    return sentence[0]


def __get_named_option_params(sentence: Tuple[str, ...]) -> Tuple[str, ...]:
    return sentence[2 : sentence.index(")")]


def __parse_block(sentence: Tuple[str, ...]) -> Tuple[Block, int]:
    block = Block(sentence[0])

    block_content = __get_block_content(sentence)
    __parse_options_in_block(block_content, block)

    number_of_processed_symbols = len(block_content) + 3
    return (block, number_of_processed_symbols)


def __parse_arrowed_option(sentence: Tuple[str, ...]) -> Tuple[Option, int]:
    if len(sentence) < 4 or sentence[3] != "(":
        option_params = sentence[0:2]
    else:
        option_params = sentence[0 : sentence.index(")") + 1]

    option = Option(params={option_params})
    return (option, len(option_params))


def __parse_named_option(sentence: Tuple[str, ...]) -> Tuple[Option, int]:
    option_name = __get_named_option_name(sentence)
    option_params = __get_named_option_params(sentence)
    number_of_processed_symbols = len(option_params) + 3

    if len(option_params) == 0:
        option_params = ("<empty>",)

    option = Option(option_name, {option_params})

    return (option, number_of_processed_symbols)


def __parse_positional_option(sentence: Tuple[str, ...]) -> Tuple[Option, int]:
    return (Option(params={(sentence[0],)}), 1)


def __mark_n_symbols_as_processed(processed: Set[int], start_index: int, number_of_symbols: int) -> None:
    processed |= set(range(start_index, start_index + number_of_symbols))


def __parse_options_in_block(sentence: Tuple[str, ...], target_block: Block) -> None:
    processed: Set[int] = set()

    for i in range(len(sentence)):
        if i in processed:
            continue

        number_of_parsed_symbols = 0
        rest_of_sentence = sentence[i:]
        if __is_block(rest_of_sentence):
            block, number_of_parsed_symbols = __parse_block(rest_of_sentence)
            target_block.add_block(block)
        elif __is_arrowed_option(rest_of_sentence):
            arrowed_option, number_of_parsed_symbols = __parse_arrowed_option(rest_of_sentence)
            target_block.add_option(arrowed_option)
        elif __is_named_option(rest_of_sentence):
            named_option, number_of_parsed_symbols = __parse_named_option(rest_of_sentence)
            target_block.add_option(named_option)
        elif __is_positional_option(rest_of_sentence):
            positional_option, number_of_parsed_symbols = __parse_positional_option(rest_of_sentence)
            target_block.add_option(positional_option)

        __mark_n_symbols_as_processed(processed, i, number_of_parsed_symbols)


def __parse_common_global_options(sentence: Tuple[str, ...]) -> Driver:
    if sentence[-1] != ";":
        raise ParseError("Common global options sentence does not end with ';'.")

    if not (sentence[1] == "{" and sentence[-2] == "}"):
        raise ParseError("Common global options curly braces are missing.")

    driver = Driver("options", DriverDB.GLOBAL_OPTIONS_DRIVER_NAME)
    option_sentence = sentence[1:-2]
    __parse_options_in_block(option_sentence, driver)

    return driver


def parse_sentence(sentence: Tuple[str, ...]) -> Driver:
    if len(sentence) < 4:
        raise ParseError("Too short sentence.")

    if sentence[0] == "options":
        return __parse_common_global_options(sentence)

    if not sentence[0].startswith("LL_CONTEXT_"):
        raise ParseError("Context is missing.")

    if not (sentence[2] == "(" and sentence[-1] == ")"):
        raise ParseError("Braces are missing, probably not a driver.")

    context = sentence[0].replace("LL_CONTEXT_", "").replace("_", "-").lower()
    if context == "options":
        driver = Driver(context, DriverDB.GLOBAL_OPTIONS_DRIVER_NAME)
        option_sentence = sentence[1:]
    else:
        driver = Driver(context, sentence[1])
        option_sentence = sentence[3:-1]

    __parse_options_in_block(option_sentence, driver)

    return driver
