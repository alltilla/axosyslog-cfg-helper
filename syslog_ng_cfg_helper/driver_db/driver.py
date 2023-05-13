from __future__ import annotations

from typing import Dict, Any

from .exceptions import MergeException
from .block import Block
from .option import Option


class Driver(Block):
    def __init__(self, context: str, name: str) -> None:
        self.__context = context
        super().__init__(name)

    @property
    def context(self) -> str:
        return self.__context

    def copy(self) -> Driver:
        copied = Driver(self.context, self.name)
        copied.merge(self)

        return copied

    def merge(self, other: Block) -> None:
        if isinstance(other, Driver) and self.context != other.context:
            raise MergeException(
                f"Cannot merge two drivers with different contexts: '{self.context}' and '{other.context}'"
            )

        super().merge(other)

    def to_block(self) -> Block:
        block = Block(self.name)
        block.merge(self)

        return block

    @staticmethod
    def from_dict(as_dict: Dict[str, Any]) -> Driver:
        self = Driver(as_dict["context"], as_dict["name"])

        for block in as_dict["blocks"].values():
            self.add_block(Block.from_dict(block))

        for option in as_dict["options"].values():
            self.add_option(Option.from_dict(option))

        return self

    def to_dict(self) -> Dict[str, Any]:
        as_dict = super().to_dict()
        as_dict.update({"context": self.context})

        return as_dict

    def __repr__(self) -> str:
        block_repr = super().__repr__()
        return f"Driver({repr(self.context)}, {block_repr[len('Block(') :]}"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Driver):
            return False

        return self.context == other.context and super().__eq__(other)
