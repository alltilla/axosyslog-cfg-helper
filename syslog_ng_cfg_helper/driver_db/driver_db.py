from __future__ import annotations

import json

from typing import Any, Dict, IO, KeysView, ValuesView

from .driver import Driver


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
