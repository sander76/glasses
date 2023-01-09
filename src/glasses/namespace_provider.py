from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod, abstractproperty
from enum import Enum, unique
from typing import TYPE_CHECKING, Generic, TypeVar, Union

from kubernetes_asyncio import client, config
from kubernetes_asyncio.client.api_client import ApiClient

# from pydantic import BaseModel
if TYPE_CHECKING:
    from glasses.k8client import BaseClient

ItemType = TypeVar("ItemType")


@unique
class Commands(Enum):
    VIEW_LOG = "view log"


class BaseK8(ABC, Generic[ItemType]):
    def __init__(self, name: str, client: BaseClient) -> None:
        self.name = name
        self._items: dict[str, ItemType] = {}
        self._client = client
        self.commands: set[str] = {}

    @abstractmethod
    async def refresh(self) -> dict[str, ItemType]:
        """Refresh this resource."""

    @property
    def items(self) -> dict[str, ItemType]:
        """All items belonging to this resource.

        They are updated by the refresh method.
        """
        return self._items


class Pod(BaseK8[str]):
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


class K8Cluster(Cluster):
    async def refresh(self) -> dict[str, ItemType]:
        await config.load_kube_config()

        async with ApiClient() as api:
            v1 = client.CoreV1Api(api)
            namespaces = await v1.list_namespace()
        new_namespaces: dict[str, ItemType] = {}
        for namespace in namespaces:
            new_namespaces[namespace.name] = self.items.get(namespace.name, namespace)
        self._items = new_namespaces
        return self._items


if __name__ == "__main__":
    client = K8Client()
