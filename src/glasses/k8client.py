from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod, abstractproperty
from importlib.abc import ResourceLoader
from typing import TYPE_CHECKING, Generic, TypeVar, Union

from kubernetes_asyncio import client, config
from kubernetes_asyncio.client.api_client import ApiClient

from glasses.namespace_provider import NameSpace, Pod


class BaseClient(ABC):
    @abstractmethod
    async def get_namespaces(self) -> dict[str, NameSpace]:
        ...

    @abstractmethod
    async def get_resources(self, namespace: str) -> dict[str, Pod]:
        ...


class K8Client(BaseClient):
    async def get_namespaces(self) -> dict[str, NameSpace]:
        """get namespaces.

        Reads the .kube config file.
        """
        _config = await config.load_kube_config()
        contexts = _config.list_contexts()

        result: dict[str, NameSpace] = {}
        for context in contexts:
            _namespace = context["context"]["namespace"]

            result[_namespace] = NameSpace(_namespace, client=self)
        return result

    async def get_resources(self, namespace: str) -> dict[str, Pod]:
        await config.load_kube_config()

        async with ApiClient() as api:
            v1 = client.CoreV1Api(api)
            pods = await v1.list_namespaced_pod(namespace)

            result: dict[str, Pod] = {}
            for pod in pods:
                _pod_name = pod["name"]
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
