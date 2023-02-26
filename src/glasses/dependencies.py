from functools import cache

from glasses.controllers.log_provider import DummyLogReader, K8LogReader, LogReader
from glasses.k8client import DummyClient, K8Client
from glasses.namespace_provider import Cluster
from glasses.settings import LogCollectors, NameSpaceProvider, Settings


@cache
def get_namespace_provider(settings: Settings | None = None) -> Cluster:
    if settings is None:
        settings = Settings()

    if settings.namespace_provider == NameSpaceProvider.DUMMY_NAMESPACE_PROVIDER:
        return Cluster("dummy provider", DummyClient())
    if settings.namespace_provider == NameSpaceProvider.K8_NAMESPACE_PROVIDER:
        return Cluster("k8", K8Client())

    raise NotImplementedError(
        f"Unknown namespace provider {settings.namespace_provider}"
    )


@cache
def get_log_reader(settings: Settings | None = None) -> LogReader:
    if settings is None:
        settings = Settings()

    if settings.logcollector == LogCollectors.DUMMY_LOG_COLLECTOR:
        return DummyLogReader()
    if settings.logcollector == LogCollectors.K8_LOG_COLLECTOR:
        return K8LogReader()

    raise NotImplementedError(f"unknown logreader {settings.logcollector}")
