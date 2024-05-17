from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, ValuesView

from .exceptions import DiffException, MergeException
from .option import Option, OptionDiff
from .utils import color_purple, diff_indent, indent, prepend_each_line, sorted_with_none


@dataclass
class BlockDiff:
    name: Optional[str]

    added_blocks: Dict[Optional[str], Block] = field(default_factory=dict)
    removed_blocks: Dict[Optional[str], Block] = field(default_factory=dict)
    changed_blocks: Dict[Optional[str], BlockDiff] = field(default_factory=dict)

    added_options: Dict[Optional[str], Option] = field(default_factory=dict)
    removed_options: Dict[Optional[str], Option] = field(default_factory=dict)
    changed_options: Dict[Optional[str], OptionDiff] = field(default_factory=dict)

    def __str__(self) -> str:
        string = f" {self.name}(\n"

        strs: Dict[Optional[str], str] = {}

        for block_name, block in self.added_blocks.items():
            strs[block_name] = f"{prepend_each_line(indent(str(block)), '+')}\n"

        for block_name, block in self.removed_blocks.items():
            strs[block_name] = f"{prepend_each_line(indent(str(block)), '-')}\n"

        for block_name, block_diff in self.changed_blocks.items():
            strs[block_name] = f"{diff_indent(str(block_diff))}\n"

        for option_name, option in self.added_options.items():
            strs[option_name] = f"{prepend_each_line(indent(str(option)), '+')}\n"

        for option_name, option in self.removed_options.items():
            strs[option_name] = f"{prepend_each_line(indent(str(option)), '-')}\n"

        for option_name, option_diff in self.changed_options.items():
            strs[option_name] = f"{diff_indent(str(option_diff))}\n"

        for block_or_option_name in sorted_with_none(strs.keys()):
            string += strs[block_or_option_name]

        string += " )"

        return string


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
        if block.name not in self.__blocks:
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
        if option.name not in self.__options:
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

    def __process_option_to_block_transform_diff(
        self,
        their_option_name: str,
        their_option: Option,
        diff: BlockDiff,
    ) -> None:
        our_block = self.get_block(their_option_name)

        their_block_from_option = Block(their_option_name)
        their_block_from_option.add_option(Option(params=their_option.params))

        diff.changed_blocks[their_option_name] = our_block.diff(their_block_from_option)

    def __gather_option_diffs(self, compared_to: Block, diff: BlockDiff) -> None:
        for their_option_name, their_option in compared_to.__options.items():
            if their_option_name not in self.__options:
                if their_option_name not in self.__blocks:
                    diff.removed_options[their_option_name] = their_option.copy()
                else:
                    self.__process_option_to_block_transform_diff(their_option_name, their_option, diff)
                continue

            our_option = self.get_option(their_option_name)
            if our_option == their_option:
                continue

            diff.changed_options[their_option_name] = our_option.diff(their_option)

        for our_option_name, our_option in self.__options.items():
            if our_option_name not in compared_to.__options:
                diff.added_options[our_option_name] = our_option.copy()
                continue

    def __process_block_to_option_transform_diff(
        self,
        their_block_name: str,
        their_block: Block,
        diff: BlockDiff,
    ) -> None:
        our_option = self.get_option(their_block_name)

        our_block_from_option = Block(their_block_name)
        our_block_from_option.add_option(Option(params=our_option.params))

        diff.changed_blocks[their_block_name] = our_block_from_option.diff(their_block)

    def __gather_block_diffs(self, compared_to: Block, diff: BlockDiff) -> None:
        for their_block_name, their_block in compared_to.__blocks.items():
            if their_block_name not in self.__blocks:
                if their_block_name not in self.__options:
                    diff.removed_blocks[their_block_name] = their_block.copy()
                else:
                    self.__process_block_to_option_transform_diff(their_block_name, their_block, diff)
                continue

            our_block = self.get_block(their_block_name)
            if our_block == their_block:
                continue

            diff.changed_blocks[their_block_name] = our_block.diff(their_block)

        for our_block_name, our_block in self.__blocks.items():
            if our_block_name not in compared_to.__blocks:
                diff.added_blocks[our_block_name] = our_block.copy()
                continue

    def diff(self, compared_to: Block) -> BlockDiff:
        diff = BlockDiff(self.name)

        if self.name != compared_to.name:
            raise DiffException(
                f"Cannot check differences of Blocks with different names: '{self.name}' and '{compared_to.name}'"
            )

        self.__gather_option_diffs(compared_to, diff)
        self.__gather_block_diffs(compared_to, diff)

        return diff

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

    def __str(self, colored: bool = False) -> str:
        string = f"{self.colorize_name(self.name, colored)}(\n"

        block_and_option_strs: Dict[Optional[str], str] = {}

        for block_name, block in self.__blocks.items():
            block_and_option_strs.setdefault(block_name, "")
            block_and_option_strs[block_name] += f"{indent(block.colored_str() if colored else str(block))}\n"

        for option_name, option in self.__options.items():
            block_and_option_strs.setdefault(option_name, "")
            block_and_option_strs[option_name] += f"{indent(option.colored_str() if colored else str(option))}\n"

        for block_or_option_name in sorted_with_none(block_and_option_strs.keys()):
            string += block_and_option_strs[block_or_option_name]

        string += ")"

        return string

    def __str__(self) -> str:
        return self.__str()

    def colored_str(self) -> str:
        return self.__str(colored=True)

    @staticmethod
    def colorize_name(name: str, colored: bool = True) -> str:
        return color_purple(name) if colored else name

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Block):
            return False

        return self.__name == other.__name and self.__blocks == other.__blocks and self.__options == other.__options
