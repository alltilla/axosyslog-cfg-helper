import json
import pytest

from axosyslog_cfg_helper.driver_db.block import Block, BlockDiff, OptionDiff
from axosyslog_cfg_helper.driver_db.exceptions import DiffException, MergeException
from axosyslog_cfg_helper.driver_db.option import Option


def test_defaults() -> None:
    block = Block("block")

    assert block.name == "block"
    assert len(block.blocks) == 0
    assert len(block.options) == 0


def test_add_get_remove_option() -> None:
    block = Block("block")
    block.add_option(Option("option", {("param-1-1", "param-1-2")}))
    block.add_option(Option("option", {("param-2-1", "param-2-2")}))
    block.add_option(Option(params={("param-3",)}))
    block.add_option(Option(params={("param-4",)}))

    assert len(block.options) == 2
    assert block.get_option("option") == Option("option", {("param-1-1", "param-1-2"), ("param-2-1", "param-2-2")})

    assert block.get_option(None) == Option(None, {("param-3",), ("param-4",)})

    block.remove_option("option")
    assert len(block.options) == 1
    with pytest.raises(KeyError):
        block.get_option("option")

    block.remove_option(None)
    assert len(block.options) == 0
    with pytest.raises(KeyError):
        block.get_option(None)


def test_add_get_remove_block() -> None:
    block = Block("block")

    inner_block_1 = Block("inner-block")
    inner_block_1.add_option(Option("option", {("param-1", "param-2")}))

    inner_block_2 = Block("inner-block")
    inner_block_2.add_option(Option("option", {("param-3", "param-4")}))

    block.add_block(inner_block_1)
    block.add_block(inner_block_2)

    expected_merged_inner_block = Block("inner-block")
    expected_merged_inner_block.add_option(Option("option", {("param-1", "param-2"), ("param-3", "param-4")}))

    assert len(block.blocks) == 1
    assert block.get_block("inner-block") == expected_merged_inner_block

    block.remove_block("inner-block")

    assert len(block.blocks) == 0
    with pytest.raises(KeyError):
        block.get_block("inner-block")


def test_eq() -> None:
    block_1 = Block("block")
    inner_block_1 = Block("inner-block")
    block_1.add_block(inner_block_1)
    block_1.add_option(Option("option", {("param-1",)}))

    block_2 = Block("block")
    inner_block_2 = Block("inner-block")
    block_2.add_block(inner_block_2)
    block_2.add_option(Option("option", {("param-1",)}))

    assert block_1 == block_2

    block_2.add_block(Block("inner-block-2"))

    assert block_1 != block_2

    assert block_1 != "not-a-Block-type"


def test_copy() -> None:
    block = Block("block")
    block.add_option(Option("option", {("param-1",)}))
    copied = block.copy()

    assert id(block) != id(copied)

    block.add_block(Block("inner-block"))
    block.add_option(Option("option", {("param-2",)}))

    assert len(block.blocks) == 1
    assert len(block.options) == 1
    assert block.get_block("inner-block") == Block("inner-block")
    assert block.get_option("option") == Option("option", {("param-1",), ("param-2",)})

    assert len(copied.blocks) == 0
    assert len(copied.options) == 1
    assert copied.get_option("option") == Option("option", {("param-1",)})


def test_merge() -> None:
    block_1 = Block("block")

    block_1.add_option(Option("option-1", {("param-1-1",)}))

    inner_block_1_1 = Block("inner-block-1")
    inner_block_1_1.add_option(Option("option-2", {("param-2-1",)}))
    block_1.add_block(inner_block_1_1)

    block_2 = Block("block")

    block_2.add_option(Option("option-1", {("param-1-2",)}))

    inner_block_1_2 = Block("inner-block-1")
    inner_block_1_2.add_option(Option("option-2", {("param-2-2",)}))
    block_2.add_block(inner_block_1_2)

    inner_block_2 = Block("inner-block-2")
    inner_block_2.add_option(Option(params={("param-3-1",)}))
    block_2.add_block(inner_block_2)

    expected_merged_block = Block("block")

    expected_merged_block.add_option(Option("option-1", {("param-1-1",), ("param-1-2",)}))

    expected_inner_block_1 = Block("inner-block-1")
    expected_inner_block_1.add_option(Option("option-2", {("param-2-1",), ("param-2-2",)}))
    expected_merged_block.add_block(expected_inner_block_1)

    expected_inner_block_2 = Block("inner-block-2")
    expected_inner_block_2.add_option(Option(params={("param-3-1",)}))
    expected_merged_block.add_block(expected_inner_block_2)

    block_1.merge(block_2)
    assert block_1 == expected_merged_block


def test_merge_different() -> None:
    block_1 = Block("block-1")
    block_2 = Block("block-2")

    with pytest.raises(MergeException):
        block_1.merge(block_2)


# pylint: disable=line-too-long
def test_repr() -> None:
    block = Block("block")
    block.add_block(Block("inner-block"))
    block.add_option(Option("option-1", {("param-1-1", "param-1-2")}))
    block.add_option(Option(params={("param-2-1",)}))

    assert (
        repr(block)
        == r"Block('block', {'inner-block': Block('inner-block', {}, {})}, {'option-1': Option('option-1', frozenset({('param-1-1', 'param-1-2')})), None: Option(None, frozenset({('param-2-1',)}))})"
    )


def test_str() -> None:
    block = Block("block")
    block.add_block(Block("inner-block"))
    block.add_option(Option(params={("positional-option-1",)}))
    block.get_block("inner-block").add_option(Option(params={("positional-option-2",)}))
    block.add_option(Option("a-option-1", {("param-1-1", "param-1-2")}))
    block.add_option(Option("option-2", {("param-2-1", "param-2-2")}))

    assert (
        str(block)
        == """
block(
    positional-option-1
    a-option-1(param-1-1 param-1-2)
    inner-block(
        positional-option-2
    )
    option-2(param-2-1 param-2-2)
)
""".strip()
    )


def test_serialization() -> None:
    block = Block("block")
    block.add_block(Block("inner-block"))
    block.add_option(Option(params={("positional-option-1",)}))
    block.get_block("inner-block").add_option(Option(params={("positional-option-2",)}))
    block.add_option(Option("a-option-1", {("param-1-1", "param-1-2")}))
    block.add_option(Option("option-2", {("param-2-1", "param-2-2")}))

    serialized = json.dumps(block.to_dict())
    deserialized = Block.from_dict(json.loads(serialized))

    assert block == deserialized


def test_diff() -> None:
    old_block = Block("block")
    new_block = Block("block")
    assert new_block.diff(old_block) == BlockDiff("block")

    # Added Option
    new_block.add_option(Option("option"))
    assert new_block.diff(old_block) == BlockDiff(
        "block",
        added_options={"option": Option("option")},
    )
    new_block.remove_option("option")

    # Removed Option
    old_block.add_option(Option("option"))
    assert new_block.diff(old_block) == BlockDiff(
        "block",
        removed_options={"option": Option("option")},
    )
    old_block.remove_option("option")

    # Changed Option
    old_block.add_option(Option("option"))
    new_block.add_option(Option("option", {("param",)}))
    assert new_block.diff(old_block) == BlockDiff(
        "block",
        changed_options={"option": OptionDiff("option", added_params={("param",)})},
    )
    old_block.remove_option("option")
    new_block.remove_option("option")

    # Added Block
    new_block.add_block(Block("inner-block"))
    assert new_block.diff(old_block) == BlockDiff(
        "block",
        added_blocks={"inner-block": Block("inner-block")},
    )
    new_block.remove_block("inner-block")

    # Removed Block
    old_block.add_block(Block("inner-block"))
    assert new_block.diff(old_block) == BlockDiff(
        "block",
        removed_blocks={"inner-block": Block("inner-block")},
    )
    old_block.remove_block("inner-block")

    # Changed Block
    old_block.add_block(Block("inner-block"))
    new_block.add_block(Block("inner-block"))
    new_block.get_block("inner-block").add_option(Option("option"))
    assert new_block.diff(old_block) == BlockDiff(
        "block",
        changed_blocks={"inner-block": BlockDiff("inner-block", added_options={"option": Option("option")})},
    )
    old_block.remove_block("inner-block")
    new_block.remove_block("inner-block")


def test_diff_error() -> None:
    old_block = Block("block-1")
    new_block = Block("block-2")

    with pytest.raises(DiffException):
        new_block.diff(old_block)


def test_diff_str() -> None:
    old_block = Block("block")
    new_block = Block("block")

    # Added Option
    new_block.add_option(Option("new-option"))

    # Removed Option
    old_block.add_option(Option("old-option"))

    # Changed Option
    old_block.add_option(Option("option"))
    new_block.add_option(Option("option", {("param",)}))

    # Added Block
    new_block.add_block(Block("new-inner-block"))

    # Removed Block
    old_block.add_block(Block("old-inner-block"))

    # Changed Block
    old_block.add_block(Block("inner-block"))
    new_block.add_block(Block("inner-block"))
    new_block.get_block("inner-block").add_option(Option("option"))

    expected_str = """
 block(
     inner-block(
+        option()
     )
+    new-inner-block(
+    )
+    new-option()
-    old-inner-block(
-    )
-    old-option()
     option(
+        param
     )
 )
"""[
        1:-1
    ]

    assert str(new_block.diff(old_block)) == expected_str
