from functools import cache

from glasses.k8client import BaseClient, DummyClient
from glasses.log_provider import DummyLogReader, LogReader
from glasses.settings import logcollectors, logparsers, settings


def get_k8_client() -> BaseClient:
    return DummyClient()


@cache
def get_log_reader(logcollector: logcollectors) -> LogReader:
    if logcollector == "DummyLogReader":
        return DummyLogReader()
    raise NotImplementedError(f"unknown logreader {settings.logcollector}")


@cache
def get_log_parser(logparser: logparsers):
    pass
