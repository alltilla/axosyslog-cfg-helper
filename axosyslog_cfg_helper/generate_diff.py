import sys

from argparse import ArgumentParser, Namespace
from pathlib import Path

from axosyslog_cfg_helper.driver_db import DriverDB


def parse_args() -> Namespace:
    parser = ArgumentParser()
    parser.add_argument(
        "--old-db-file",
        "-o",
        type=str,
        required=True,
        help="Path of the old axosyslog-cfg-helper.db file.",
    )
    parser.add_argument(
        "--new-db-file",
        "-n",
        type=str,
        required=True,
        help="Path of the new axosyslog-cfg-helper.db file.",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    old_db_file = Path(args.old_db_file)
    new_db_file = Path(args.new_db_file)

    with old_db_file.open("r", encoding="utf-8") as file:
        old_driver_db = DriverDB.load(file)

    with new_db_file.open("r", encoding="utf-8") as file:
        new_driver_db = DriverDB.load(file)

    print(new_driver_db.diff(old_driver_db))

    return 0


if __name__ == "__main__":
    sys.exit(main())
