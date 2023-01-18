from functools import cache

from glasses.k8client import DummyClient, K8Client
from glasses.log_provider import DummyLogReader, K8LogReader, LogReader
from glasses.namespace_provider import Cluster
from glasses.settings import LogCollectors, NameSpaceProvider, settings


@cache
def get_namespace_provider(namespace: NameSpaceProvider) -> Cluster:
    if namespace == NameSpaceProvider.DUMMY_NAMESPACE_PROVIDER:
        return Cluster("dummy provider", DummyClient())
    if namespace == NameSpaceProvider.K8_NAMESPACE_PROVIDER:
        return Cluster("k8", K8Client())

    raise NotImplementedError(f"Unknown namespace provider {namespace}")


@cache
def get_log_reader(logcollector: LogCollectors) -> LogReader:
    if logcollector == LogCollectors.DUMMY_LOG_COLLECTOR:
        return DummyLogReader()
    if logcollector == LogCollectors.K8_LOG_COLLECTOR:
        return K8LogReader()

    raise NotImplementedError(f"unknown logreader {settings.logcollector}")
