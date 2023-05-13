from pathlib import Path

from syslog_ng_cfg_helper.driver_db import DriverDB
from syslog_ng_cfg_helper.module_loader import load_modules


def run():
    db_file = Path(__file__).resolve().parent.parent / "syslog-ng-cfg-helper.db"

    lib_dir = Path(__file__).resolve().parent.parent / "syslog-ng-4.2.0" / "lib"
    modules_dir = Path(__file__).resolve().parent.parent / "syslog-ng-4.2.0" / "modules"

    driver_db = load_modules(lib_dir, modules_dir)

    with db_file.open("w") as file:
        driver_db.dump(file)

    driver_db = None

    with db_file.open("r") as file:
        driver_db = DriverDB.load(file)

    for ctx in driver_db.contexts:
        for driver in driver_db.get_drivers_in_context(ctx):
            print(driver)
