from tempfile import TemporaryFile

from syslog_ng_cfg_helper.driver_db.driver_db import DriverDB
from syslog_ng_cfg_helper.driver_db.driver import Driver
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
