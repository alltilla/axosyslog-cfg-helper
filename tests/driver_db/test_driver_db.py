from tempfile import TemporaryFile

from syslog_ng_cfg_helper.driver_db.driver_db import ContextDiff, DriverDB, DriverDBDiff
from syslog_ng_cfg_helper.driver_db.driver import Driver, DriverDiff
from syslog_ng_cfg_helper.driver_db.option import Option


def test_defaults() -> None:
    driver_db = DriverDB()
    assert len(driver_db.contexts) == 0


def test_add_driver_get_driver_get_drivers_in_context() -> None:
    driver_db = DriverDB()

    driver_db.add_driver(Driver("context-1", "driver-1-1"))
    driver_db.add_driver(Driver("context-1", "driver-1-2"))
    driver_2_1_1 = Driver("context-2", "driver-2-1")
    driver_2_1_1.add_option(Option("option-name", {("param-1",)}))
    driver_db.add_driver(driver_2_1_1)

    driver_2_1_2 = Driver("context-2", "driver-2-1")
    driver_2_1_2.add_option(Option("option-name", {("param-2",)}))
    driver_db.add_driver(driver_2_1_2)

    assert len(driver_db.contexts) == 2
    assert len(driver_db.get_drivers_in_context("context-1")) == 2
    assert len(driver_db.get_drivers_in_context("context-2")) == 1
    assert driver_db.get_driver("context-1", "driver-1-1") == Driver("context-1", "driver-1-1")

    expected_driver_2_1 = Driver("context-2", "driver-2-1")
    expected_driver_2_1.add_option(Option("option-name", {("param-1",), ("param-2",)}))
    assert driver_db.get_driver("context-2", "driver-2-1") == expected_driver_2_1


def test_remove_context() -> None:
    driver_db = DriverDB()
    driver_db.add_driver(Driver("context", "driver"))

    assert len(driver_db.contexts) == 1
    assert next(iter(driver_db.contexts)) == "context"

    driver_db.remove_context("context")

    assert len(driver_db.contexts) == 0


def test_eq() -> None:
    driver_db_1 = DriverDB()
    driver_db_2 = DriverDB()

    driver_db_1.add_driver(Driver("context", "driver"))
    driver_db_2.add_driver(Driver("context", "driver"))

    assert driver_db_1 == driver_db_2

    driver_db_2.get_driver("context", "driver").add_option(Option("option-name", {("param",)}))

    assert driver_db_1 != driver_db_2
    assert driver_db_1 != "not-a-DriverDB-type"


def test_merge() -> None:
    driver_db_1 = DriverDB()

    driver_db_1.add_driver(Driver("context-1", "driver-1-1"))
    driver_2_1_1 = Driver("context-2", "driver-2-1")
    driver_2_1_1.add_option(Option("option-name", {("param-1",)}))
    driver_db_1.add_driver(driver_2_1_1)

    driver_db_2 = DriverDB()

    driver_2_1_2 = Driver("context-2", "driver-2-1")
    driver_2_1_2.add_option(Option("option-name", {("param-2",)}))
    driver_db_2.add_driver(driver_2_1_2)
    driver_db_2.add_driver(Driver("context-3", "driver-3-1"))

    expected_merged_driver_db = DriverDB()

    expected_merged_driver_db.add_driver(Driver("context-1", "driver-1-1"))
    expected_driver_2_1 = Driver("context-2", "driver-2-1")
    expected_driver_2_1.add_option(Option("option-name", {("param-1",), ("param-2",)}))
    expected_merged_driver_db.add_driver(expected_driver_2_1)
    expected_merged_driver_db.add_driver(Driver("context-3", "driver-3-1"))

    driver_db_1.merge(driver_db_2)

    assert driver_db_1 == expected_merged_driver_db


# pylint: disable=line-too-long
def test_repr() -> None:
    driver_db = DriverDB()
    driver_db.add_driver(Driver("context-1", "driver-1-1"))
    driver_db.add_driver(Driver("context-1", "driver-1-2"))
    driver_db.add_driver(Driver("context-2", "driver-2-1"))

    assert (
        repr(driver_db)
        == r"DriverDB({'context-1': {'driver-1-1': Driver('context-1', 'driver-1-1', {}, {}), 'driver-1-2': Driver('context-1', 'driver-1-2', {}, {})}, 'context-2': {'driver-2-1': Driver('context-2', 'driver-2-1', {}, {})}})"
    )


def test_serialize() -> None:
    driver_db = DriverDB()
    driver_db.add_driver(Driver("context-1", "driver-1-1"))
    driver_db.add_driver(Driver("context-1", "driver-1-2"))
    driver_db.add_driver(Driver("context-2", "driver-2-1"))

    with TemporaryFile("w+") as file:
        driver_db.dump(file)
        file.seek(0)
        deserialized = DriverDB.load(file)

    assert driver_db == deserialized


def test_diff() -> None:
    old_driver_db = DriverDB()
    new_driver_db = DriverDB()
    assert new_driver_db.diff(old_driver_db) == DriverDBDiff()

    # Added context
    new_driver_db.add_driver(Driver("ctx", "driver"))
    assert new_driver_db.diff(old_driver_db) == DriverDBDiff(
        added_contexts={"ctx": {"driver": Driver("ctx", "driver")}}
    )
    new_driver_db.remove_context("ctx")

    # Removed context
    old_driver_db.add_driver(Driver("ctx", "driver"))
    assert new_driver_db.diff(old_driver_db) == DriverDBDiff(
        removed_contexts={"ctx": {"driver": Driver("ctx", "driver")}}
    )
    old_driver_db.remove_context("ctx")

    # Added driver
    old_driver_db.add_driver(Driver("ctx", "driver-1"))
    new_driver_db.add_driver(Driver("ctx", "driver-1"))
    new_driver_db.add_driver(Driver("ctx", "driver-2"))
    assert new_driver_db.diff(old_driver_db) == DriverDBDiff(
        changed_contexts={"ctx": ContextDiff("ctx", added_drivers={"driver-2": Driver("ctx", "driver-2")})}
    )
    old_driver_db.remove_context("ctx")
    new_driver_db.remove_context("ctx")

    # Removed driver
    old_driver_db.add_driver(Driver("ctx", "driver-1"))
    new_driver_db.add_driver(Driver("ctx", "driver-1"))
    old_driver_db.add_driver(Driver("ctx", "driver-2"))
    assert new_driver_db.diff(old_driver_db) == DriverDBDiff(
        changed_contexts={"ctx": ContextDiff("ctx", removed_drivers={"driver-2": Driver("ctx", "driver-2")})}
    )
    old_driver_db.remove_context("ctx")
    new_driver_db.remove_context("ctx")

    # Changed driver
    old_driver_db.add_driver(Driver("ctx", "driver"))
    new_driver_db.add_driver(Driver("ctx", "driver"))
    new_driver_db.get_driver("ctx", "driver").add_option(Option("option"))
    assert new_driver_db.diff(old_driver_db) == DriverDBDiff(
        changed_contexts={
            "ctx": ContextDiff(
                "ctx",
                changed_drivers={
                    "driver": DriverDiff(context="ctx", name="driver", added_options={"option": Option("option")})
                },
            )
        }
    )
    old_driver_db.remove_context("ctx")
    new_driver_db.remove_context("ctx")


def test_diff_str() -> None:
    old_driver_db = DriverDB()
    new_driver_db = DriverDB()

    # Added context
    new_driver_db.add_driver(Driver("new-ctx", "driver"))

    # Removed context
    old_driver_db.add_driver(Driver("old-ctx", "driver"))

    # Added driver
    new_driver_db.add_driver(Driver("ctx", "new-driver"))

    # Removed driver
    old_driver_db.add_driver(Driver("ctx", "old-driver"))

    # Changed driver
    old_driver_db.add_driver(Driver("ctx", "driver"))
    new_driver_db.add_driver(Driver("ctx", "driver"))
    new_driver_db.get_driver("ctx", "driver").add_option(Option("option"))

    expected_str = """
--- a/ctx
+++ b/ctx

 driver(
+    option()
 )

+new-driver(
+)

-old-driver(
-)

--- /dev/null
+++ b/new-ctx

+driver(
+)

--- a/old-ctx
+++ /dev/null

-driver(
-)
"""[
        1:-1
    ]

    assert str(new_driver_db.diff(old_driver_db)) == expected_str
