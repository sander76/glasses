from abc import ABC, abstractmethod, abstractproperty
from typing import Generic, TypeVar, Union

ItemType = TypeVar("ItemType")


class BaseK8(ABC, Generic[ItemType]):
    def __init__(self, name: str, parent: Union["BaseK8", None]) -> None:
        self.name = name
        self._items: dict[str, ItemType] = {}
        self.parent = parent

    @abstractmethod
    async def refresh(self):
        """Refresh this resource."""

    @property
    def items(self) -> dict[str, ItemType]:
        """All items belonging to this resource.

        They are updated by the refresh method.
        """
        return self._items


class Pod(BaseK8[str]):
    def __init__(self, name: str, parent: "NameSpace"):
        super().__init__(name, parent=parent)
        self.commands: list[str] = ["log"]

    async def refresh(self):
        pass


class NameSpace(BaseK8[Pod]):
    """A k8s namespace"""


class Cluster(BaseK8[NameSpace]):
    """A k8s cluster"""


class DummyPod(Pod):
    ...
    # async def refresh(self) -> list[str]:
    #     await asyncio.sleep(1)
    #     return ["log"]


class DummyNameSpace(NameSpace):
    async def refresh(self) -> dict[str, Pod]:
        self._items = {
            "pod_1": DummyPod(name="pod_1", parent=self),
            "pod_2": DummyPod(name="pod_2", parent=self),
        }
        return self._items


class DummyClustere(Cluster):
    async def refresh(self) -> dict[str, NameSpace]:
        self._items = {
            "namespace 1": DummyNameSpace(name="namespace_1", parent=self),
            "namespace_2": DummyNameSpace(name="namespace_2", parent=self),
        }
        return self._items
