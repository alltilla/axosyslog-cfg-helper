from typing import Iterable

__INDENTATION = 4


def indent(string: str) -> str:
    lines = string.split("\n")
    indented_lines = [f"{' ' * __INDENTATION}{line}" for line in lines]
    return "\n".join(indented_lines)


def sorted_with_none(iterable: Iterable):
    def none_to_empty_str(elem):
        if elem is None:
            return ""
        return elem

    sorted_iterable = list(iterable)
    sorted_iterable.sort(key=none_to_empty_str)

    return sorted_iterable
