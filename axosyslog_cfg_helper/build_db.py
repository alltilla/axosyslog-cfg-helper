import sys

from argparse import ArgumentParser, Namespace
from pathlib import Path

from axosyslog_cfg_helper.module_loader import load_modules


def parse_args() -> Namespace:
    parser = ArgumentParser()
    parser.add_argument(
        "--source-dir",
        "-s",
        type=str,
        required=True,
        help="Path of the AxoSyslog source directory (extracted from a release tarball).",
    )
    parser.add_argument("--output", "-o", type=str, required=True, help="Output path of the database built.")

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    source_dir = Path(args.source_dir)
    lib_dir = source_dir / "lib"
    modules_dir = source_dir / "modules"

    output = Path(args.output)

    driver_db = load_modules(lib_dir, modules_dir)

    with output.open("w", encoding="utf-8") as file:
        driver_db.dump(file)

    return 0


if __name__ == "__main__":
    sys.exit(main())
