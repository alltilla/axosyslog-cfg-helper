from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import Optional

from syslog_ng_cfg_helper.driver_db import DriverDB


def parse_args() -> Namespace:
    parser = ArgumentParser()
    parser.add_argument("--context", "-c", type=str, help="e.g.: destination")
    parser.add_argument("--driver", "-d", type=str, help="e.g.: http")

    return parser.parse_args()


def open_db() -> DriverDB:
    db_file = Path(__file__).parent / "syslog-ng-cfg-helper.db"
    with db_file.open("r") as file:
        driver_db = DriverDB.load(file)

    return driver_db


def print_options(driver_db: DriverDB, context_name: str, driver_name: str) -> None:
    if context_name not in driver_db.contexts:
        print(f"The context '{context_name}' is not in the database.")
        print_contexts(driver_db)
        return

    try:
        driver = driver_db.get_driver(context_name, driver_name)
        print(driver)
    except KeyError:
        print(f"The driver '{driver_name}' is not in the drivers of context '{context_name}'.")
        print_drivers(driver_db, context_name)


def print_drivers(driver_db: DriverDB, context_name: str) -> None:
    if context_name not in driver_db.contexts:
        print(f"The context '{context_name}' is not in the database.")
        print_contexts(driver_db)
        return

    driver_names = sorted(driver.name for driver in driver_db.get_drivers_in_context(context_name))
    print(f"Drivers of context '{context_name}':")
    for driver_name in driver_names:
        print(f"  {driver_name}")
    print(f"Print the options of DRIVER with `--context {context_name} --driver DRIVER`.")


def print_contexts(driver_db: DriverDB) -> None:
    print("Valid contexts:")
    for context_name in sorted(driver_db.contexts):
        print(f"  {context_name}")
    print("Print the drivers of CONTEXT with `--context CONTEXT`.")


def query(driver_db: DriverDB, context: Optional[str], driver: Optional[str]) -> None:
    if context and driver:
        print_options(driver_db, context, driver)
        return

    if context and not driver:
        print_drivers(driver_db, context)
        return

    if not context and driver:
        print(f"Please define the context of '{driver}' with `--context CONTEXT`.")
        return

    if not context and not driver:
        print_contexts(driver_db)
        return


def run():
    args = parse_args()
    driver_db = open_db()
    query(driver_db, args.context, args.driver)
