import asyncio
from itertools import cycle
from pathlib import Path
from typing import AsyncIterator, Iterator

from kubernetes import client, config, watch  # type: ignore
from rich.json import JSON
from rich.text import Text

from glasses.log_parser import ParseError, jsonparse
from glasses.reactive_model import Reactr, ReactrModel


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
            except ParseError as err:
                parsed = Text(f"ERROR: {err}, data={data}", "red")
                yield LogEvent(raw=data, parsed=parsed)
            else:
                yield LogEvent(raw=JSON(data), parsed=parsed)

    async def _read(self) -> None:
        raise NotImplementedError()

    def start(self) -> asyncio.Task:
        self._reader = asyncio.create_task(self._read())
        self.is_reading = True
        return self._reader

    def stop(self) -> None:
        if self._reader:
            self._reader.cancel()
        self._reader = None
        self.is_reading = False


class K8LogReader(LogReader):
    def __init__(self) -> None:
        super().__init__()
        self._config = config.load_config()
        self._client = client.CoreV1Api()

    async def _read(self) -> None:
        try:
            loop = asyncio.get_running_loop()

            w = watch.Watch()

            def _get_log() -> None:
                try:
                    for e in w.stream(
                        self._client.read_namespaced_pod_log,
                        name=self.pod,
                        namespace=self.namespace,
                        tail_lines=50,
                    ):
                        asyncio.run_coroutine_threadsafe(self._stream.put(e), loop=loop)
                except Exception as err:
                    return err

            result = await asyncio.to_thread(_get_log)
            print(result)
        except asyncio.CancelledError:
            w.stop()


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

        try:
            for line in self.log_data():

                await asyncio.sleep(self.delay)
                await self._stream.put(line)
        except asyncio.CancelledError:
            print("stopped logger input")
