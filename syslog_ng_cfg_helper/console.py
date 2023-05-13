from pathlib import Path

from syslog_ng_cfg_helper.driver_db import DriverDB


def run():
    db_file = Path(__file__).parent / "syslog-ng-cfg-helper.db"
    with db_file.open("r") as file:
        driver_db = DriverDB.load(file)

    for ctx in driver_db.contexts:
        for driver in driver_db.get_drivers_in_context(ctx):
            print(driver)
