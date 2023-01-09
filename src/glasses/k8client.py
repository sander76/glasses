from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod

from kubernetes import client, config  # type: ignore

from glasses.namespace_provider import NameSpace, Pod


class BaseClient(ABC):
    @abstractmethod
    async def get_namespaces(self) -> dict[str, NameSpace]:
        ...

    @abstractmethod
    async def get_resources(self, namespace: str) -> dict[str, Pod]:
        ...


class K8Client(BaseClient):
    def __init__(self) -> None:
        super().__init__()
        self._config = config.load_config()
        self._client = client.CoreV1Api()

    async def get_namespaces(self) -> dict[str, NameSpace]:
        """get namespaces.

        Reads the .kube config file.
        """
        contexts = config.list_kube_config_contexts()

        result: dict[str, NameSpace] = {}
        for context in contexts[0]:
            _namespace = context["context"]["namespace"]

            result[_namespace] = NameSpace(_namespace, client=self)
        return result

    async def get_resources(self, namespace: str) -> dict[str, Pod]:
        loop = asyncio.get_running_loop()
        v1_pod_list = await loop.run_in_executor(
            None, self._client.list_namespaced_pod, namespace
        )

        result: dict[str, Pod] = {}
        for pod in v1_pod_list.items:
            _pod_name = pod.metadata.name

            result[_pod_name] = Pod(_pod_name, namespace=namespace, client=self)
        return result


class DummyClient(BaseClient):
    async def get_namespaces(self) -> dict[str, NameSpace]:
        return {
            "namespace_1": NameSpace(name="namespace_1", client=self),
            "namespace_2": NameSpace(name="namespace_2", client=self),
        }

    async def get_resources(self, namespace: str) -> dict[str, Pod]:
        resources = {
            "pod_1": Pod(name="pod_1", namespace=namespace, client=self),
            "pod_2": Pod(name="pod_2", namespace=namespace, client=self),
        }
        return resources


if __name__ == "__main__":
    k8client = K8Client()

    result = asyncio.run(k8client.get_resources("ogi-kcn-acc"))

    print(result)
