from typing import Iterable

__INDENTATION = 4


def indent(string: str) -> str:
    lines = string.split("\n")
    indented_lines = [f"{' ' * __INDENTATION}{line}" for line in lines]
    return "\n".join(indented_lines)


def diff_indent(string: str) -> str:
    lines = string.split("\n")
    indented_lines = []
    for line in lines:
        if line:
            indented_lines.append(f"{line[0]}{' ' * __INDENTATION}{line[1:]}")
        else:
            indented_lines.append("")
    return "\n".join(indented_lines)


def prepend_each_line(string: str, prefix: str) -> str:
    lines = string.split("\n")
    formatted_lines = [f"{prefix}{line}" for line in lines]
    return "\n".join(formatted_lines)


def sorted_with_none(iterable: Iterable):
    def none_to_empty_str(elem):
        if elem is None:
            return ""
        return elem

    sorted_iterable = list(iterable)
    sorted_iterable.sort(key=none_to_empty_str)

    return sorted_iterable
