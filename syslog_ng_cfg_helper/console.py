from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import Optional

from syslog_ng_cfg_helper.driver_db import DriverDB, Driver
from syslog_ng_cfg_helper.driver_db.utils import color_red


def colorize_context_name(name: str, colored: bool = True) -> str:
    return color_red(name) if colored else name


def parse_args() -> Namespace:
    parser = ArgumentParser()
    parser.add_argument("--context", "-c", type=str, help="e.g.: destination")
    parser.add_argument("--driver", "-d", type=str, help="e.g.: http")
    parser.add_argument("--no-color", "-n", action="store_true", help="Do not color the output")

    return parser.parse_args()


def open_db() -> DriverDB:
    db_file = Path(__file__).parent / "syslog-ng-cfg-helper.db"
    with db_file.open("r") as file:
        driver_db = DriverDB.load(file)

    return driver_db


def print_options(driver_db: DriverDB, context_name: str, driver_name: str, colored: bool) -> None:
    if context_name not in driver_db.contexts:
        print(f"The context '{context_name}' is not in the database.")
        print_contexts(driver_db, colored)
        return

    try:
        driver = driver_db.get_driver(context_name, driver_name)
        print(driver.colored_str() if colored else str(driver))
    except KeyError:
        print(
            f"The driver '{Driver.colorize_name(driver_name, colored)}' is not in the drivers of context "
            f"'{colorize_context_name(context_name, colored)}'."
        )
        print_drivers(driver_db, context_name, colored)


def print_drivers(driver_db: DriverDB, context_name: str, colored: bool) -> None:
    if context_name not in driver_db.contexts:
        print(f"The context '{colorize_context_name(context_name, colored)}' is not in the database.")
        print_contexts(driver_db, colored)
        return

    driver_names = sorted(driver.name for driver in driver_db.get_drivers_in_context(context_name))
    print(f"Drivers of context '{colorize_context_name(context_name, colored)}':")
    for driver_name in driver_names:
        print(f"  {Driver.colorize_name(driver_name, colored)}")
    print(
        f"Print the options of {Driver.colorize_name('DRIVER', colored)} with "
        f"`--context {context_name} --driver DRIVER`."
    )


def print_contexts(driver_db: DriverDB, colored: bool) -> None:
    print("Valid contexts:")
    for context_name in sorted(driver_db.contexts):
        print(f"  {colorize_context_name(context_name, colored)}")
    print(f"Print the drivers of {colorize_context_name('CONTEXT', colored)} with `--context CONTEXT`.")


def query(driver_db: DriverDB, context: Optional[str], driver: Optional[str], colored: bool) -> None:
    if context and driver:
        print_options(driver_db, context, driver, colored)
        return

    if context and not driver:
        print_drivers(driver_db, context, colored)
        return

    if not context and driver:
        print(f"Please define the context of '{Driver.colorize_name(driver, colored)}' with `--context CONTEXT`.")
        return

    if not context and not driver:
        print_contexts(driver_db, colored)
        return


def run():
    args = parse_args()
    driver_db = open_db()
    query(driver_db, args.context, args.driver, not args.no_color)
