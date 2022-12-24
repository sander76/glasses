import abc
import asyncio
from itertools import cycle
from pathlib import Path
from typing import Any, AsyncGenerator, AsyncIterator, Coroutine, Iterator

from rich.json import JSON
from rich.text import Text

from glasses.log_parser import ParseError, jsonparse


class LogEvent:
    def __init__(self, raw: str | Text | JSON, parsed: Text) -> None:
        self.raw = raw

        self.parsed = parsed


class LogReader:
    async def read(self) -> AsyncIterator[LogEvent]:
        raise NotImplementedError()

    def start(self):
        raise NotImplementedError()

    def stop(self):
        raise NotImplementedError()


class DummyLogReader(LogReader):
    def __init__(self) -> None:
        self._reader: asyncio.Task | None = None
        self._stream: asyncio.Queue[str] = asyncio.Queue()
        self._parser = jsonparse
        self.delay: float = 0.2

    async def read(self) -> AsyncIterator[LogEvent]:
        while True:
            data = await self._stream.get()
            self._stream.task_done()
            try:
                parsed = self._parser(data)
            except ParseError as err:
                parsed = Text(f"ERROR: {err}, data={data}", "red")
                yield LogEvent(raw=data, parsed=parsed)
            else:
                yield LogEvent(raw=JSON(data), parsed=parsed)

    def start(self):
        self._reader = asyncio.create_task(self._read())
        return self._reader

    @staticmethod
    def log_data() -> Iterator:
        with open(Path(__file__).parent.parent / "tests" / "log_data.txt") as fl:
            data = fl.read().split("\n")
        return cycle(data)

    async def _read(self):

        try:
            for line in self.log_data():

                await asyncio.sleep(self.delay)
                await self._stream.put(line)
        except asyncio.CancelledError:
            print("stopped logger input")

    def stop(self) -> None:
        if self._reader:
            self._reader.cancel()
