import json
import pytest

from axosyslog_cfg_helper.driver_db.driver import Driver, DriverDiff
from axosyslog_cfg_helper.driver_db.block import Block, BlockDiff
from axosyslog_cfg_helper.driver_db.exceptions import DiffException, MergeException
from axosyslog_cfg_helper.driver_db.option import Option, OptionDiff


def test_defaults() -> None:
    driver = Driver("context", "driver")

    assert driver.context == "context"
    assert driver.name == "driver"
    assert len(driver.options) == 0
    assert len(driver.blocks) == 0


def test_copy() -> None:
    driver = Driver("context", "driver")
    copied = driver.copy()

    assert id(driver) != id(copied)

    driver.add_option(Option("option-name", {("param",)}))

    assert len(driver.options) == 1
    assert driver.get_option("option-name") == Option("option-name", {("param",)})

    assert len(copied.options) == 0


def test_merge() -> None:
    driver_1 = Driver("context", "driver")
    driver_1.add_block(Block("block-1"))
    driver_1.add_option(Option("option-name", {("param-1",)}))

    driver_2 = Driver("context", "driver")
    driver_1.add_block(Block("block-2"))
    driver_2.add_option(Option("option-name", {("param-2",)}))

    expected_merged_driver = Driver("context", "driver")
    expected_merged_driver.add_block(Block("block-1"))
    expected_merged_driver.add_block(Block("block-2"))
    expected_merged_driver.add_option(Option("option-name", {("param-1",), ("param-2",)}))

    driver_1.merge(driver_2)
    assert driver_1 == expected_merged_driver


def test_merge_different() -> None:
    driver_1 = Driver("context", "driver-1")
    driver_2 = Driver("context", "driver-2")
    driver_3 = Driver("other-context", "driver-1")

    with pytest.raises(MergeException):
        driver_1.merge(driver_2)

    with pytest.raises(MergeException):
        driver_1.merge(driver_3)


def test_to_block() -> None:
    driver = Driver("context", "driver")
    driver.add_block(Block("block"))

    expected_block = Block("driver")
    expected_block.add_block(Block("block"))

    assert driver.to_block() == expected_block


def test_eq() -> None:
    driver_1 = Driver("context", "driver")
    driver_2 = Driver("context", "driver")

    assert driver_1 == driver_2

    driver_2.add_block(Block("block"))

    assert driver_1 != driver_2

    assert driver_1 != Block("driver")
    assert driver_1 != "not-a-Block-type"


# pylint: disable=line-too-long
def test_repr() -> None:
    driver = Driver("context", "driver")
    driver.add_block(Block("block"))
    driver.add_option(Option("option-name", {("param-1", "param-2")}))

    assert (
        repr(driver)
        == r"Driver('context', 'driver', {'block': Block('block', {}, {})}, {'option-name': Option('option-name', frozenset({('param-1', 'param-2')}))})"
    )


def test_str() -> None:
    driver = Driver("context", "driver")
    driver.add_block(Block("block"))
    driver.get_block("block").add_option(Option(params={("positional-option-1",)}))
    driver.add_option(Option(params={("positional-option-2",)}))
    driver.add_option(Option("option-name", {("param-1", "param-2")}))

    assert (
        str(driver)
        == """
driver(
    positional-option-2
    block(
        positional-option-1
    )
    option-name(param-1 param-2)
)
""".strip()
    )


def test_serialization() -> None:
    driver = Driver("context", "driver")
    driver.add_block(Block("block"))
    driver.get_block("block").add_option(Option(params={("positional-option-1",)}))
    driver.add_option(Option(params={("positional-option-2",)}))
    driver.add_option(Option("option-name", {("param-1", "param-2")}))

    serialized = json.dumps(driver.to_dict())
    deserialized = Driver.from_dict(json.loads(serialized))

    assert driver == deserialized


def test_diff() -> None:
    old_driver = Driver("ctx", "driver")
    new_driver = Driver("ctx", "driver")
    assert new_driver.diff(old_driver) == DriverDiff(context="ctx", name="driver")

    # Added Option
    new_driver.add_option(Option("option"))
    assert new_driver.diff(old_driver) == DriverDiff(
        context="ctx",
        name="driver",
        added_options={"option": Option("option")},
    )
    new_driver.remove_option("option")

    # Removed Option
    old_driver.add_option(Option("option"))
    assert new_driver.diff(old_driver) == DriverDiff(
        context="ctx",
        name="driver",
        removed_options={"option": Option("option")},
    )
    old_driver.remove_option("option")

    # Changed Option
    old_driver.add_option(Option("option"))
    new_driver.add_option(Option("option", {("param",)}))
    assert new_driver.diff(old_driver) == DriverDiff(
        context="ctx",
        name="driver",
        changed_options={"option": OptionDiff("option", added_params={("param",)})},
    )
    old_driver.remove_option("option")
    new_driver.remove_option("option")

    # Added Block
    new_driver.add_block(Block("block"))
    assert new_driver.diff(old_driver) == DriverDiff(
        context="ctx",
        name="driver",
        added_blocks={"block": Block("block")},
    )
    new_driver.remove_block("block")

    # Removed Block
    old_driver.add_block(Block("block"))
    assert new_driver.diff(old_driver) == DriverDiff(
        context="ctx",
        name="driver",
        removed_blocks={"block": Block("block")},
    )
    old_driver.remove_block("block")

    # Changed Block
    old_driver.add_block(Block("block"))
    new_driver.add_block(Block("block"))
    new_driver.get_block("block").add_option(Option("option"))
    assert new_driver.diff(old_driver) == DriverDiff(
        context="ctx",
        name="driver",
        changed_blocks={"block": BlockDiff("block", added_options={"option": Option("option")})},
    )
    old_driver.remove_block("block")
    new_driver.remove_block("block")


def test_diff_error() -> None:
    old_driver = Driver("ctx", "driver-1")
    new_driver = Driver("ctx", "driver-2")
    with pytest.raises(DiffException):
        new_driver.diff(old_driver)

    old_driver = Driver("ctx-1", "driver")
    new_driver = Driver("ctx-2", "driver")
    with pytest.raises(DiffException):
        new_driver.diff(old_driver)

    old_block = Block("foo")
    new_driver = Driver("ctx", "foo")
    with pytest.raises(DiffException):
        new_driver.diff(old_block)


def test_diff_str() -> None:
    old_driver = Driver("ctx", "driver")
    new_driver = Driver("ctx", "driver")

    # Added Option
    new_driver.add_option(Option("new-option"))

    # Removed Option
    old_driver.add_option(Option("old-option"))

    # Changed Option
    old_driver.add_option(Option("option"))
    new_driver.add_option(Option("option", {("param",)}))

    # Added Block
    new_driver.add_block(Block("new-block"))

    # Removed Block
    old_driver.add_block(Block("old-block"))

    # Changed Block
    old_driver.add_block(Block("block"))
    new_driver.add_block(Block("block"))
    new_driver.get_block("block").add_option(Option("option"))

    expected_str = """
 driver(
     block(
+        option()
     )
+    new-block(
+    )
+    new-option()
-    old-block(
-    )
-    old-option()
     option(
+        param
     )
 )
"""[
        1:-1
    ]

    assert str(new_driver.diff(old_driver)) == expected_str
