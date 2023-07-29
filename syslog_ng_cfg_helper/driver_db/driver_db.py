from __future__ import annotations

import json

from dataclasses import dataclass, field
from typing import Any, Dict, IO, KeysView, ValuesView

from .driver import Driver, DriverDiff


@dataclass
class ContextDiff:
    added_drivers: Dict[str, Driver] = field(default_factory=dict)
    removed_drivers: Dict[str, Driver] = field(default_factory=dict)
    changed_drivers: Dict[str, DriverDiff] = field(default_factory=dict)


@dataclass
class DriverDBDiff:
    added_contexts: Dict[str, Dict[str, Driver]] = field(default_factory=dict)
    removed_contexts: Dict[str, Dict[str, Driver]] = field(default_factory=dict)
    changed_contexts: Dict[str, ContextDiff] = field(default_factory=dict)


class DriverDB:
    def __init__(self) -> None:
        self.__contexts: Dict[str, Dict[str, Driver]] = {}

    @property
    def contexts(self) -> KeysView[str]:
        return self.__contexts.keys()

    def add_driver(self, driver: Driver) -> DriverDB:
        context = self.__contexts.setdefault(driver.context, {})

        if driver.name in context.keys():
            context[driver.name].merge(driver)
        else:
            context[driver.name] = driver.copy()

        return self

    def get_driver(self, context: str, driver_name: str) -> Driver:
        return self.__contexts[context][driver_name]

    def get_drivers_in_context(self, context: str) -> ValuesView[Driver]:
        return self.__contexts[context].values()

    def remove_context(self, context: str) -> None:
        self.__contexts.pop(context)

    def merge(self, other: DriverDB) -> DriverDB:
        for context in other.contexts:
            for driver in other.get_drivers_in_context(context):
                self.add_driver(driver)

        return self

    def __gather_context_diff(self, our_context: Dict[str, Driver], their_context: Dict[str, Driver]) -> ContextDiff:
        diff = ContextDiff()

        for their_driver_name, their_driver in their_context.items():
            if their_driver_name not in our_context.keys():
                diff.removed_drivers[their_driver_name] = their_driver.copy()
                continue

            our_driver = our_context[their_driver_name]
            if our_driver == their_driver:
                continue

            diff.changed_drivers[their_driver_name] = our_driver.diff(their_driver)

        for our_driver_name, our_driver in our_context.items():
            if our_driver_name not in their_context.keys():
                diff.added_drivers[our_driver_name] = our_driver.copy()

        return diff

    def diff(self, compared_to: DriverDB) -> DriverDBDiff:
        diff = DriverDBDiff()

        for their_context_name, their_context in compared_to.__contexts.items():
            if their_context_name not in self.__contexts.keys():
                diff.removed_contexts[their_context_name] = their_context.copy()
                continue

            our_context = self.__contexts[their_context_name]
            if our_context == their_context:
                continue

            diff.changed_contexts[their_context_name] = self.__gather_context_diff(our_context, their_context)

        for our_context_name, our_context in self.__contexts.items():
            if our_context_name not in compared_to.__contexts.keys():
                diff.added_contexts[our_context_name] = our_context.copy()
                continue

        return diff

    @staticmethod
    def from_dict(as_dict: Dict[str, Any]) -> DriverDB:
        self = DriverDB()

        for _, drivers in as_dict["contexts"].items():
            for _, driver in drivers.items():
                self.add_driver(Driver.from_dict(driver))

        return self

    def to_dict(self) -> Dict[str, Any]:
        as_dict: Dict[str, Any] = {"contexts": {}}

        for context_name, drivers in self.__contexts.items():
            context = as_dict["contexts"].setdefault(context_name, {})

            for driver_name, driver in drivers.items():
                context[driver_name] = driver.to_dict()

        return as_dict

    @staticmethod
    def load(file: IO) -> DriverDB:
        return DriverDB.from_dict(json.load(file))

    def dump(self, file: IO) -> None:
        json.dump(self.to_dict(), file)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, DriverDB):
            return False

        return self.__contexts == other.__contexts

    def __repr__(self) -> str:
        return f"DriverDB({repr(self.__contexts)})"
