from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime

from kubernetes import client, config  # type: ignore

from glasses.namespace_provider import BaseK8, NameSpace, Pod


class BaseClient(ABC):
    @abstractmethod
    async def get_namespaces(self, parent: BaseK8) -> dict[str, NameSpace]:
        ...

    @abstractmethod
    async def get_resources(self, parent: BaseK8, namespace: str) -> dict[str, Pod]:
        ...


class K8Client(BaseClient):
    def __init__(self) -> None:
        super().__init__()
        self._config = config.load_config()
        self._client = client.CoreV1Api()

    async def get_namespaces(self, parent: BaseK8) -> dict[str, NameSpace]:
        """get namespaces.

        Reads the .kube config file.
        """

        # for an async usage:
        #         loader = await config.load_kube_config()

        # # list contexts
        # for context in loader.list_contexts():
        #     print(context["context"]["namespace"])

        contexts = config.list_kube_config_contexts()

        result: dict[str, NameSpace] = {}
        for context in contexts[0]:
            _namespace = context["context"]["namespace"]

            result[_namespace] = NameSpace(_namespace, parent=parent, client=self)
        return result

    async def get_resources(self, parent: BaseK8, namespace: str) -> dict[str, Pod]:
        loop = asyncio.get_running_loop()
        v1_pod_list = await loop.run_in_executor(
            None, self._client.list_namespaced_pod, namespace
        )

        result: dict[str, Pod] = {}
        for pod in v1_pod_list.items:
            _pod_name = pod.metadata.name
            _creation_timestamp = pod.metadata.creation_timestamp

            result[_pod_name] = Pod(
                _pod_name,
                parent=parent,
                namespace=namespace,
                client=self,
                creation_timestamp=_creation_timestamp,
            )
        return result


class DummyClient(BaseClient):
    async def get_namespaces(self, parent: BaseK8) -> dict[str, NameSpace]:
        return {
            "namespace_1": NameSpace(name="namespace_1", parent=parent, client=self),
            "namespace_2": NameSpace(name="namespace_2", parent=parent, client=self),
            "namespace_3": NameSpace(name="namespace_3", parent=parent, client=self),
        }

    async def get_resources(self, parent: BaseK8, namespace: str) -> dict[str, Pod]:
        resources = {
            f"pod_{idx}": Pod(
                name=f"pod_{idx}",
                parent=parent,
                namespace=namespace,
                client=self,
                creation_timestamp=datetime.now(),
            )
            for idx in range(10)
        }

        # resources = {
        #     "pod_1": Pod(
        #         name="pod_1",
        #         parent=parent,
        #         namespace=namespace,
        #         client=self,
        #         creation_timestamp=datetime.now(),
        #     ),
        #     "pod_2": Pod(
        #         name="pod_2",
        #         parent=parent,
        #         namespace=namespace,
        #         client=self,
        #         creation_timestamp=datetime.now(),
        #     ),
        # }
        return resources
