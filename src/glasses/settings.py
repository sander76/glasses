from enum import Enum
from typing import Literal

from pydantic import BaseSettings

logparsers = Literal["json"]


class LogCollectors(Enum):
    DUMMY_LOG_COLLECTOR = "dummy_log_collector"
    K8_LOG_COLLECTOR = "k8_log_collector"


class NameSpaceProvider(Enum):
    DUMMY_NAMESPACE_PROVIDER = "dummy_namespace_provider"
    K8_NAMESPACE_PROVIDER = "k8_namespace_provider"


class Settings(BaseSettings):
    logparser: logparsers = "json"
    logcollector: LogCollectors = LogCollectors.K8_LOG_COLLECTOR
    namespace_provider: NameSpaceProvider = NameSpaceProvider.K8_NAMESPACE_PROVIDER


settings = Settings()
