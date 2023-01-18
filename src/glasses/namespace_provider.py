from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum, unique
from typing import TYPE_CHECKING, Generic, Iterator, TypeVar

if TYPE_CHECKING:
    from glasses.k8client import BaseClient

ItemType = TypeVar("ItemType", bound="BaseK8")


@unique
class Commands(Enum):
    VIEW_LOG = "view log"


class BaseK8(ABC, Generic[ItemType]):
    def __init__(self, name: str, client: BaseClient) -> None:
        self.name = name
        self._items: dict[str, ItemType] = {}
        self._client = client
        self.commands: set[Commands] = set()
        self.filter_text: str = ""

    @abstractmethod
    async def refresh(self) -> dict[str, ItemType]:
        """Refresh this resource."""

    @property
    def items(self) -> dict[str, ItemType]:
        """All items belonging to this resource.

        They are updated by the refresh method.
        """
        return self._items

    def filter_items(self) -> Iterator[ItemType]:
        for item in self._items.values():
            if self.filter_text in item.name:
                yield item


class Pod(BaseK8):
    def __init__(self, name: str, namespace: str, client: BaseClient) -> None:
        self.namespace = namespace
        super().__init__(name, client)
        self.commands = {Commands.VIEW_LOG}

    async def refresh(self):
        return self.items


class NameSpace(BaseK8[Pod]):
    """A k8s namespace"""

    async def refresh(self) -> dict[str, Pod]:
        self._items = await self._client.get_resources(self.name)
        return self._items


class Cluster(BaseK8[NameSpace]):
    """A k8s cluster"""

    def __init__(self, name: str, client: BaseClient) -> None:
        super().__init__(name, client=client)

    async def refresh(self) -> dict[str, NameSpace]:
        data = await self._client.get_namespaces()
        self._items = data
        return self._items
