from functools import cache

from glasses.log_provider import DummyLogReader, LogReader
from glasses.namespace_provider import DummyClustere, Cluster
from glasses.settings import logcollectors, logparsers, settings


def get_cluster() -> Cluster:
    return DummyClustere(name="default provider", parent=None)


@cache
def get_log_reader(logcollector: logcollectors) -> LogReader:
    if logcollector == "DummyLogReader":
        return DummyLogReader()
    raise NotImplementedError(f"unknown logreader {settings.logcollector}")


@cache
def get_log_parser(logparser: logparsers):
    pass
