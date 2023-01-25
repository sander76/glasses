from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable, Generic, TypeVar
from weakref import WeakMethod

ReactrType = TypeVar("ReactrType")


class Reactr(Generic[ReactrType]):
    def __init__(self, default: ReactrType) -> None:
        self._default = default

    def __set_name__(self, owner: Any, name: str):
        self.name = name

    def __get__(self, obj: ReactrModel, type: type[ReactrModel]) -> ReactrType:
        return obj.__dict__.get(self.name) or self._default

    def __set__(self, obj: ReactrModel, value: ReactrType) -> None:
        obj.__dict__[self.name] = value
        obj.publish(self.name, value)


class ReactrModel:
    def __init__(self) -> None:
        self._subscriptions: dict[str, list[Callable[[object], None]]] = defaultdict(
            list
        )
        self._weakrefs: dict[WeakMethod, str] = {}

    def _get_weakref(self, func):
        return WeakMethod(func, self.unsubscribe)

    def publish(self, property: str, value):
        for subscription in self._subscriptions[property]:
            subscription()(value)

    def subscribe(self, property, callback):
        weakref = self._get_weakref(callback)
        self._subscriptions[property].append(weakref)
        if weakref in self._weakrefs:
            raise Exception("Alread an identical weakref available.")
        self._weakrefs[weakref] = property

    def unsubscribe(self, weakref):
        prop = self._weakrefs[weakref]
        subscriptions = self._subscriptions[prop]
        subscriptions.remove(weakref)
        print("removed")
