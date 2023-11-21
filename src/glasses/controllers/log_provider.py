import asyncio
from collections import deque
from enum import Enum, auto
from itertools import cycle
from pathlib import Path
from typing import AsyncIterator, Iterator

from aiohttp import ClientResponse
from kubernetes_asyncio import client, config
from rich.text import Text
from textual import log

from glasses.log_parsers import plain_text_parser
from glasses.log_parsers.json_parser import JsonParseError, jsonparse
from glasses.reactive_model import Reactr, ReactrModel

# _logger = logging.getLogger(__name__)


class LogEvent:
    def __init__(self, raw: str, parsed: Text) -> None:
        self.raw = raw
        self.parsed = parsed


class LogReader(ReactrModel):
    namespace: Reactr[str] = Reactr("no namespace")
    pod = Reactr("no pod")
    tail = Reactr[int](500)

    is_reading: bool = False

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
            except JsonParseError:
                parsed = plain_text_parser.parse(data)
                parsed = Text.assemble(Text("[!E] ", "red"), parsed)
            yield LogEvent(raw=data, parsed=parsed)

    async def _read(self) -> None:
        raise NotImplementedError()

    def start(self) -> asyncio.Task:
        self.is_reading = True
        self._reader = asyncio.create_task(self._read())
        return self._reader

    async def stop(self) -> None:
        self.is_reading = False
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

        try:
            await self._print_pod_log()
        except asyncio.CancelledError:
            log("stopped reading the log.")
        except Exception:
            log("an unknown problem occurred while reading the log.")
            raise
        finally:
            self.is_reading = False

    async def _print_pod_log(self) -> None:
        last_lines: deque[bytes] = deque(maxlen=10)

        def _add_to_queue(data: bytes) -> None:
            try:
                utf_data = data.decode("utf-8")
                self._stream.put_nowait(utf_data)
                last_lines.append(data)
            except UnicodeDecodeError:
                log.error(f"unable to utf-8 decode {data}")  # type: ignore
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
                    log("reading first batch")
                    _add_to_queue(ln)
                    # last_lines.append(ln)
                log("finished reading first batch")
            else:
                reading_state: K8LogReader.ReadingState = (
                    K8LogReader.ReadingState.WAITING_FOR_FIRST_ITEM
                )
                log("start watching log")
                while not resp.content.at_eof():
                    line = await resp.content.readline()
                    log("found logline")
                    if reading_state == K8LogReader.ReadingState.WAITING_FOR_FIRST_ITEM:
                        if len(last_lines) == 0:
                            reading_state = K8LogReader.ReadingState.FOUND
                            _add_to_queue(line)
                        elif line in last_lines:
                            reading_state = K8LogReader.ReadingState.FOUND
                        else:
                            log.warning(
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
        await _read(self.tail, follow=False)
        # start watching the log for changes.
        while True:
            try:
                await _read(2, follow=True)
            except asyncio.TimeoutError:
                log.info(f"timed out while logging pod {self.pod} on {self.namespace}")


class DummyLogReader(LogReader):
    def __init__(self) -> None:
        super().__init__()
        self.delay: float = 0.5
        # self.range: int = 1

    def log_data(self) -> Iterator:
        log_data = Path(__file__).parent.parent.parent.parent / "log_output.txt"
        with open(log_data) as fl:
            data = fl.read().split("\n")
        # for i in range(self.range):
        yield from data

    async def _read(self) -> None:
        try:
            for line in cycle(self.log_data()):
                await asyncio.sleep(self.delay)
                await self._stream.put(line)
        except asyncio.CancelledError:
            log.info("stopped logger input")
