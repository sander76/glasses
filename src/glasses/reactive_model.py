from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable, Generic, TypeVar
from weakref import WeakMethod

ReactrType = TypeVar("ReactrType")


class Reactr(Generic[ReactrType]):
    def __init__(self, default: ReactrType) -> None:
        self._default = default

    def __set_name__(self, owner: Any, name: str) -> None:
        self.name = name

    def __get__(self, obj: ReactrModel, type: type[ReactrModel]) -> ReactrType:
        if obj is None:
            pass
        return obj.__dict__.get(self.name) or self._default

    def __set__(self, obj: ReactrModel, value: ReactrType) -> None:
        obj.__dict__[self.name] = value
        obj.publish(self.name, value)


class ReactrModel:
    def __init__(self) -> None:
        self._subscriptions: dict[str, list[WeakMethod]] = defaultdict(list)
        self._weakrefs: dict[WeakMethod, str] = {}

    def _get_weakref(self, func: Callable[[Any], None]) -> WeakMethod:
        return WeakMethod(func, self.unsubscribe)

    def publish(self, property: str, value: Any) -> None:
        for subscription in self._subscriptions[property]:
            subscription()(value)  # type: ignore

    def subscribe(self, property: str, callback: Callable[[Any], None]) -> None:
        weakref = self._get_weakref(callback)
        self._subscriptions[property].append(weakref)
        if weakref in self._weakrefs:
            raise Exception("Alread an identical weakref available.")
        self._weakrefs[weakref] = property

    def unsubscribe(self, weakref: WeakMethod) -> None:
        prop = self._weakrefs[weakref]
        subscriptions = self._subscriptions[prop]
        subscriptions.remove(weakref)
