import asyncio
from itertools import cycle
from pathlib import Path
from typing import AsyncIterator, Iterator

from kubernetes import client, config, watch  # type: ignore
from rich.json import JSON
from rich.text import Text

from glasses.log_parser import ParseError, jsonparse


class LogEvent:
    def __init__(self, raw: str | Text | JSON, parsed: Text) -> None:
        self.raw = raw

        self.parsed = parsed


class LogReader:
    def __init__(self) -> None:
        self.namespace: str = "no namespace"
        self.pod: str = "no pod"
        self._stream: asyncio.Queue[str] = asyncio.Queue()
        self._parser = jsonparse

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

    def start(self, namespace: str, pod: str) -> asyncio.Task:
        raise NotImplementedError()

    def stop(self) -> None:
        raise NotImplementedError()


class DummyLogReader(LogReader):
    def __init__(self) -> None:
        super().__init__()
        self._reader: asyncio.Task | None = None
        self.delay: float = 0.2

    def start(self, namespace: str, pod: str) -> asyncio.Task:
        self._reader = asyncio.create_task(self._read())
        return self._reader

    @staticmethod
    def log_data() -> Iterator:
        with open(Path(__file__).parent.parent.parent / "tests" / "log_data.txt") as fl:
            data = fl.read().split("\n")
        return cycle(data)

    async def _read(self) -> None:

        try:
            for line in self.log_data():

                await asyncio.sleep(self.delay)
                await self._stream.put(line)
        except asyncio.CancelledError:
            print("stopped logger input")

    def stop(self) -> None:
        if self._reader:
            self._reader.cancel()


class K8LogReader(LogReader):
    def __init__(self) -> None:
        super().__init__()
        self._config = config.load_config()
        self._client = client.CoreV1Api()
        self._reader: asyncio.Task | None = None

    async def _read(self) -> None:
        loop = asyncio.get_running_loop()

        def _get_log():
            w = watch.Watch()
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

    def start(self, namespace: str, pod: str) -> asyncio.Task:
        self.namespace = namespace
        self.pod = pod
        self._reader = asyncio.create_task(self._read())
        return self._reader

    def stop(self):
        if self._reader:
            self._reader.cancel()


if __name__ == "__main__":
    # config.load_config()
    # _client = client.CoreV1Api()

    # w = watch.Watch()

    # for e in w.stream(
    #     _client.read_namespaced_pod_log,
    #     name="grid-insight-job-service-5d7fb988f6-rgtmh",
    #     namespace="ogi-kcn-acc",
    #     tail_lines=10,
    # ):
    #     print(e)

    logreader = K8LogReader()

    async def run():
        async def read():
            async for line in logreader.read():
                print(line)

        logreader.start("ogi-kcn-acc", "grid-insight-job-service-5d7fb988f6-rgtmh")
        await read()

    asyncio.run(run())
