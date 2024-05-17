from typing import List, Tuple
import pytest

from axosyslog_cfg_helper.module_loader.parse_sentence import parse_sentence
from axosyslog_cfg_helper.driver_db import Driver, Block, Option


def get_test_params() -> List[Tuple[Tuple[str, ...], Driver]]:
    # pylint: disable=too-many-statements
    test_params: List[Tuple[Tuple[str, ...], Driver]] = []

    expected_0 = Driver("ctx", "driver")
    expected_0.add_option(Option("named-option-1", {("<param-1>",)}))
    test_params.append(
        (
            (
                "LL_CONTEXT_CTX",
                "driver",
                "(",
                "named-option-1",
                "(",
                "<param-1>",
                ")",
                ")",
            ),
            expected_0,
        )
    )

    expected_1 = Driver("ctx", "driver")
    expected_1.add_option(Option("named-option-1", {("<empty>",)}))
    expected_1.add_option(Option("<named-option-2>", {("<param-2-1>",)}))
    expected_1.add_option(Option("named-option-3", {("<param-3-1>", "<param-3-2>")}))
    test_params.append(
        (
            (
                "LL_CONTEXT_CTX",
                "driver",
                "(",
                "named-option-1",
                "(",
                ")",
                "<named-option-2>",
                "(",
                "<param-2-1>",
                ")",
                "named-option-3",
                "(",
                "<param-3-1>",
                "<param-3-2>",
                ")",
                ")",
            ),
            expected_1,
        )
    )

    expected_2 = Driver("ctx", "driver")
    expected_2.add_option(Option(params={("<positional-option-1>",)}))
    test_params.append(
        (
            (
                "LL_CONTEXT_CTX",
                "driver",
                "(",
                "<positional-option-1>",
                ")",
            ),
            expected_2,
        )
    )

    expected_3 = Driver("ctx", "driver")
    expected_3.add_option(Option(params={("<positional-option-1>",)}))
    expected_3.add_option(Option(params={("<positional-option-2>",)}))
    expected_3.add_option(Option("named-option", {("<param-1>", "<param-2>")}))
    expected_3.add_option(Option(params={("<positional-option-3>",)}))
    test_params.append(
        (
            (
                "LL_CONTEXT_CTX",
                "driver",
                "(",
                "<positional-option-1>",
                "<positional-option-2>",
                "named-option",
                "(",
                "<param-1>",
                "<param-2>",
                ")",
                "<positional-option-3>",
                ")",
            ),
            expected_3,
        )
    )

    expected_4 = Driver("ctx", "driver")
    expected_4.add_block(Block("block"))
    expected_4.get_block("block").add_option(Option("named-option-1", {("<param-1-1>", "<param-1-2>")}))
    expected_4.get_block("block").add_option(Option("named-option-2", {("<param-2-1>", "<param-2-2>")}))
    test_params.append(
        (
            (
                "LL_CONTEXT_CTX",
                "driver",
                "(",
                "block",
                "(",
                "named-option-1",
                "(",
                "<param-1-1>",
                "<param-1-2>",
                ")",
                "named-option-2",
                "(",
                "<param-2-1>",
                "<param-2-2>",
                ")",
                ")",
                ")",
            ),
            expected_4,
        )
    )

    expected_5 = Driver("ctx", "driver")
    expected_5.add_block(Block("block-1"))
    expected_5.get_block("block-1").add_option(Option(params={("<positional-option-1>",)}))
    expected_5.get_block("block-1").add_block(Block("block-2"))
    expected_5.get_block("block-1").get_block("block-2").add_option(
        Option("named-option-1", {("<param-1-1>", "<param-1-2>")})
    )
    expected_5.get_block("block-1").get_block("block-2").add_option(Option(params={("<positional-option-2>",)}))
    expected_5.get_block("block-1").add_option(Option("named-option-2", {("<param-2-1>", "<param-2-2>")}))
    test_params.append(
        (
            (
                "LL_CONTEXT_CTX",
                "driver",
                "(",
                "block-1",
                "(",
                "<positional-option-1>",
                "block-2",
                "(",
                "named-option-1",
                "(",
                "<param-1-1>",
                "<param-1-2>",
                ")",
                "<positional-option-2>",
                ")",
                "named-option-2",
                "(",
                "<param-2-1>",
                "<param-2-2>",
                ")",
                ")",
                ")",
            ),
            expected_5,
        )
    )

    expected_6 = Driver("ctx", "driver")
    expected_6.add_block(Block("block-1"))
    expected_6.get_block("block-1").add_option(Option(params={("<positional-option-1>",)}))
    expected_6.get_block("block-1").add_option(Option("named-option-1", {("<param-1-1>", "<param-1-2>")}))
    expected_6.add_option(Option("named-option-2", {("<empty>",)}))
    expected_6.add_option(Option(params={("<positional-option-2>",)}))
    expected_6.add_block(Block("block-2"))
    expected_6.get_block("block-2").add_option(Option("named-option-3", {("<param-3-1>", "<param-3-2>")}))
    expected_6.get_block("block-2").add_block(Block("block-3"))
    expected_6.get_block("block-2").get_block("block-3").add_option(Option(params={("<positional-option-3>",)}))
    expected_6.get_block("block-2").get_block("block-3").add_option(Option(params={("<positional-option-4>",)}))
    expected_6.get_block("block-2").get_block("block-3").add_option(Option("named-option-4", {("<empty>",)}))
    expected_6.add_option(Option("named-option-5", {("<param-5-1>", "<param-5-2>")}))
    expected_6.add_option(Option(params={("<positional-option-5>",)}))
    test_params.append(
        (
            (
                "LL_CONTEXT_CTX",
                "driver",
                "(",
                "block-1",
                "(",
                "<positional-option-1>",
                "named-option-1",
                "(",
                "<param-1-1>",
                "<param-1-2>",
                ")",
                ")",
                "named-option-2",
                "(",
                ")",
                "<positional-option-2>",
                "block-2",
                "(",
                "named-option-3",
                "(",
                "<param-3-1>",
                "<param-3-2>",
                ")",
                "block-3",
                "(",
                "<positional-option-3>",
                "<positional-option-4>",
                "named-option-4",
                "(",
                ")",
                ")",
                ")",
                "named-option-5",
                "(",
                "<param-5-1>",
                "<param-5-2>",
                ")",
                "<positional-option-5>",
                ")",
            ),
            expected_6,
        )
    )

    expected_7 = Driver("ctx", "driver")
    expected_7.add_block(Block("block"))
    expected_7.get_block("block").add_option(Option(params={("opt", "=>", "hint", "(", "<arg>", ")")}))
    test_params.append(
        (
            (
                "LL_CONTEXT_CTX",
                "driver",
                "(",
                "block",
                "(",
                "opt",
                "=>",
                "hint",
                "(",
                "<arg>",
                ")",
                ")",
                ")",
            ),
            expected_7,
        )
    )

    return test_params


@pytest.mark.parametrize("sentence, expected_driver", get_test_params(), ids=range(len(get_test_params())))
def test_parse_sentence(sentence, expected_driver):
    assert parse_sentence(sentence) == expected_driver
