from typing import Literal

from pydantic import BaseSettings

logparsers = Literal["json"]
logcollectors = Literal["DummyLogReader"]


class Settings(BaseSettings):
    logparser: logparsers = "json"
    logcollector: logcollectors = "DummyLogReader"


settings = Settings()
