from __future__ import annotations
from typing import Any, Dict, Iterable, FrozenSet, Optional, Set, Tuple

from .exceptions import MergeException
from .utils import indent


Params = Tuple[str, ...]


class Option:
    def __init__(self, name: Optional[str] = None, params: Optional[Iterable[Params]] = None) -> None:
        self.__name = name
        self.__params: Set[Params] = set(tuple(elem) for elem in params or [])

    @property
    def name(self) -> Optional[str]:
        return self.__name

    @property
    def params(self) -> FrozenSet[Params]:
        return frozenset(self.__params)

    def copy(self) -> Option:
        clone = Option(self.name)
        clone.merge(self)

        return clone

    def merge(self, other: Option) -> None:
        if self.name != other.name:
            raise MergeException(f"Cannot merge Options with different names: '{self.name}' and '{other.name}'")

        self.__params |= other.__params

    @staticmethod
    def from_dict(as_dict: Dict[str, Any]) -> Option:
        return Option(as_dict["name"], as_dict["params"])

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.__name, "params": tuple(self.__params)}

    def __repr__(self) -> str:
        return f"Option({repr(self.name)}, {repr(self.params)})"

    def __named_option_str(self) -> str:
        string = f"{self.__name}("

        if len(self.__params) == 0:
            return string + ")"

        if len(self.__params) == 1:
            return string + " ".join(next(iter(self.__params))) + ")"

        for params in sorted(self.__params):
            string += f"\n{indent(' '.join(params))}"
        string += "\n)"

        return string

    def __positional_option_str(self) -> str:
        string = ""

        for params in sorted(self.params):
            string += " ".join(params) + "\n"

        string = string[:-1]

        return string

    def __str__(self) -> str:
        if self.name is not None:
            return self.__named_option_str()

        return self.__positional_option_str()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Option):
            return False

        return self.__name == other.__name and self.__params == other.__params
