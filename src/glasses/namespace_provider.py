from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum, unique
from typing import TYPE_CHECKING, Any, Generic, Iterator, TypeVar

from rich.text import Text

if TYPE_CHECKING:
    from glasses.k8client import BaseClient

ItemType = TypeVar("ItemType", bound="BaseK8")


@unique
class Commands(Enum):
    VIEW_LOG = "view log"


class BaseK8(ABC, Generic[ItemType]):
    def __init__(self, name: str, parent: BaseK8 | None, client: BaseClient) -> None:
        self.name = name
        self._items: dict[str, ItemType] = {}
        self._client = client
        self.filter_text: str = ""
        self.parent = parent

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

    @property
    def label(self) -> Text | str:
        return self.name


class Pod(BaseK8):
    DATETIME_OUTPUT = "%Y-%m-%d %H:%M:%S"

    def __init__(
        self,
        name: str,
        parent: BaseK8,
        namespace: str,
        client: BaseClient,
        creation_timestamp: datetime,
    ) -> None:
        self.namespace = namespace
        self.creation_timestamp = creation_timestamp
        super().__init__(name, parent=parent, client=client)

    async def refresh(self) -> dict[str, Any]:
        return self.items

    @property
    def label(self) -> Text | str:
        return Text.assemble(
            Text("> ", "green"),
            self.name,
            Text(
                f"  [{self.creation_timestamp.strftime(Pod.DATETIME_OUTPUT)}]",
                "grey54",
            ),
        )


class NameSpace(BaseK8[Pod]):
    """A k8s namespace"""

    async def refresh(self) -> dict[str, Pod]:
        self._items = await self._client.get_resources(parent=self, namespace=self.name)
        return self._items


class Cluster(BaseK8[NameSpace]):
    """A k8s cluster"""

    def __init__(self, name: str, client: BaseClient) -> None:
        super().__init__(name, parent=None, client=client)

    async def refresh(self) -> dict[str, NameSpace]:
        data = await self._client.get_namespaces(parent=self)
        self._items = data
        return self._items
