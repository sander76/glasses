import asyncio
import logging
from collections import deque
from enum import Enum, auto
from itertools import cycle
from pathlib import Path
from typing import AsyncIterator, Iterator

from aiohttp import ClientResponse
from kubernetes_asyncio import client, config
from rich.json import JSON
from rich.text import Text

from glasses.log_parser import JsonParseError, jsonparse
from glasses.reactive_model import Reactr, ReactrModel

_logger = logging.getLogger(__name__)


class LogEvent:
    def __init__(self, raw: str | Text | JSON, parsed: Text) -> None:
        self.raw = raw

        self.parsed = parsed


class LogReader(ReactrModel):
    namespace = Reactr("no namespace")
    pod = Reactr("no pod")
    is_reading = Reactr(False)

    def __init__(self) -> None:
        super().__init__()
        self._stream: asyncio.Queue[str] = asyncio.Queue()
        self._parser = jsonparse
        self._reader: asyncio.Task | None = None

    async def read(self) -> AsyncIterator[LogEvent]:
        while True:
            data = await self._stream.get()
            self._stream.task_done()
            try:
                parsed = self._parser(data)
            except JsonParseError as err:
                parsed = Text.assemble(Text("[!E] ", "red"), err.raw)
                yield LogEvent(raw=err.raw, parsed=parsed)
            else:
                yield LogEvent(raw=JSON(data), parsed=parsed)

    async def _read(self) -> None:
        raise NotImplementedError()

    def start(self) -> asyncio.Task:
        self._reader = asyncio.create_task(self._read())
        return self._reader

    async def stop(self) -> None:
        if self._reader:
            self._reader.cancel()
            await self._reader
        self._reader = None


class K8LogReader(LogReader):
    class ReadingState(Enum):
        WAITING_FOR_FIRST_ITEM = auto()
        FOUND = auto()
        NOT_FOUND = auto

    def __init__(self, client: client.CoreV1Api | None = None) -> None:
        """Initialize the reader

        Args:
            client: An instantiated client. make sure it is also configured.. Defaults to None.
        """
        super().__init__()
        if client is None:
            self._configured = False
        else:
            self._configured = True
        self._client = client

    async def _read(self) -> None:

        if not self._configured:
            await config.load_kube_config()
            self._configured = True
        if self._client is None:
            self._client = client.CoreV1Api()

        self.is_reading = True
        try:
            await self.print_pod_log()
        except asyncio.CancelledError:
            _logger.info("stopped reading the log.")
            self.is_reading = False
        except Exception:
            _logger.exception("an unknown problem occurred while reading the log.")
            self.is_reading = False

    async def print_pod_log(self, lines: int = 50) -> None:

        last_lines: deque[bytes] = deque(maxlen=10)

        def _add_to_queue(data: bytes) -> None:
            try:
                utf_data = data.decode("utf-8")
                self._stream.put_nowait(utf_data)
                last_lines.append(data)
            except UnicodeDecodeError:
                _logger.error(f"unable to utf-8 decode {data}")  # type: ignore
                self._stream.put_nowait(f"[error] Unable to parse incoming logline: {data}")  # type: ignore

        async def _read(tail_lines: int, follow: bool) -> None:
            assert self._client is not None
            resp: ClientResponse = await self._client.read_namespaced_pod_log(
                self.pod,
                self.namespace,
                tail_lines=tail_lines,
                follow=follow,
                _preload_content=False,
            )

            if not follow:
                while not resp.content.at_eof():
                    ln = await resp.content.readline()
                    _add_to_queue(ln)
                    # last_lines.append(ln)
            else:
                reading_state: K8LogReader.ReadingState = (
                    K8LogReader.ReadingState.WAITING_FOR_FIRST_ITEM
                )

                while not resp.content.at_eof():
                    line = await resp.content.readline()

                    if reading_state == K8LogReader.ReadingState.WAITING_FOR_FIRST_ITEM:
                        if len(last_lines) == 0:
                            reading_state = K8LogReader.ReadingState.FOUND
                            _add_to_queue(line)
                        elif line in last_lines:
                            reading_state = K8LogReader.ReadingState.FOUND
                        else:
                            _logger.warning(
                                "Missing overlap of lines between log call and previous log_call. Possibly log lines are lost."
                            )
                            self._stream.put_nowait(
                                "WARNING. MIGHT HAVE LOST A LOGLINE"
                            )
                            _add_to_queue(line)
                            reading_state = K8LogReader.ReadingState.NOT_FOUND
                    elif reading_state == K8LogReader.ReadingState.FOUND:
                        if line in last_lines:
                            reading_state = K8LogReader.ReadingState.FOUND
                        else:
                            _add_to_queue(line)
                            reading_state = K8LogReader.ReadingState.NOT_FOUND
                    elif reading_state == K8LogReader.ReadingState.NOT_FOUND:
                        _add_to_queue(line)

                print("eof reached.")

        # do the first read getting the log history.
        await _read(lines, follow=False)
        # start watching the log for changes.
        while True:
            try:
                await _read(2, follow=True)
            except asyncio.TimeoutError:
                _logger.info(
                    f"timed out while logging pod {self.pod} on {self.namespace}"
                )


class DummyLogReader(LogReader):
    def __init__(self) -> None:
        super().__init__()
        self.delay: float = 0.2

    @staticmethod
    def log_data() -> Iterator:
        with open(Path(__file__).parent / "log_data.txt") as fl:
            data = fl.read().split("\n")
        return cycle(data)

    async def _read(self) -> None:
        self.is_reading = True
        try:
            for line in self.log_data():

                await asyncio.sleep(self.delay)
                await self._stream.put(line)
        except asyncio.CancelledError:
            self.is_reading = False
            _logger.info("stopped logger input")
