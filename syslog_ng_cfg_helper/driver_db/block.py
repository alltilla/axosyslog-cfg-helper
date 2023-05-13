from __future__ import annotations
from typing import Any, Dict, Optional, ValuesView

from .exceptions import MergeException
from .option import Option
from .utils import indent, sorted_with_none


class Block:
    def __init__(self, name: str):
        self.__name = name
        self.__blocks: Dict[str, Block] = {}
        self.__options: Dict[Optional[str], Option] = {}

    @property
    def name(self) -> str:
        return self.__name

    @property
    def blocks(self) -> ValuesView[Block]:
        return self.__blocks.values()

    def get_block(self, name: str) -> Block:
        return self.__blocks[name]

    def add_block(self, block: Block) -> None:
        if block.name not in self.__blocks.keys():
            self.__blocks[block.name] = block.copy()
        else:
            self.get_block(block.name).merge(block)

    def remove_block(self, name) -> None:
        self.__blocks.pop(name)

    @property
    def options(self) -> ValuesView[Option]:
        return self.__options.values()

    def get_option(self, name: Optional[str]) -> Option:
        return self.__options[name]

    def add_option(self, option: Option) -> None:
        if option.name not in self.__options.keys():
            self.__options[option.name] = option.copy()
        else:
            self.get_option(option.name).merge(option)

    def remove_option(self, name: Optional[str]) -> None:
        self.__options.pop(name)

    def merge(self, other: Block) -> None:
        if self.name != other.name:
            raise MergeException(f"Cannot merge two Blocks with different names: '{self.name}' and '{other.name}'")

        for block in other.blocks:
            self.add_block(block)

        for option in other.options:
            self.add_option(option)

    def copy(self) -> Block:
        clone = Block(self.name)
        clone.merge(self)

        return clone

    @staticmethod
    def from_dict(as_dict: Dict[str, Any]) -> Block:
        self = Block(as_dict["name"])

        for block in as_dict["blocks"].values():
            self.add_block(Block.from_dict(block))

        for option in as_dict["options"].values():
            self.add_option(Option.from_dict(option))

        return self

    def to_dict(self) -> Dict[str, Any]:
        as_dict: Dict[str, Any] = {
            "name": self.name,
            "blocks": {},
            "options": {},
        }

        for block_name, block in self.__blocks.items():
            as_dict["blocks"][block_name] = block.to_dict()

        for option_name, option in self.__options.items():
            as_dict["options"][option_name or ""] = option.to_dict()

        return as_dict

    def __repr__(self) -> str:
        return f"Block({repr(self.__name)}, {repr(self.__blocks)}, {repr(self.__options)})"

    def __str__(self) -> str:
        string = f"{self.name}(\n"

        block_and_option_strs: Dict[Optional[str], str] = {}

        for block_name in sorted(self.__blocks.keys()):
            block_and_option_strs.setdefault(block_name, "")
            block_and_option_strs[block_name] += f"{indent(str(self.get_block(block_name)))}\n"

        for option_name in sorted_with_none(self.__options.keys()):
            block_and_option_strs.setdefault(option_name, "")
            block_and_option_strs[option_name] += f"{indent(str(self.get_option(option_name)))}\n"

        for block_or_option_name in sorted_with_none(block_and_option_strs.keys()):
            string += block_and_option_strs[block_or_option_name]

        string += ")"

        return string

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Block):
            return False

        return self.__name == other.__name and self.__blocks == other.__blocks and self.__options == other.__options
