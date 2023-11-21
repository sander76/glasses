import asyncio
from typing import Any, Sequence

import pytest

from glasses.controllers.log_provider import K8LogReader


class _Reader:
    def __init__(
        self, watched_items: list[bytes | asyncio.TimeoutError | asyncio.CancelledError]
    ) -> None:
        self._watch_items = watched_items
        self._current_idx = 0

    def at_eof(self) -> bool:
        return self._current_idx == len(self._watch_items)

    async def readline(self) -> bytes:
        item = self._watch_items[self._current_idx]
        self._current_idx += 1

        if isinstance(item, asyncio.TimeoutError):
            raise item
        if isinstance(item, asyncio.CancelledError):
            raise item
        else:
            return item


class _Resp:
    def __init__(self, watched_items: Sequence[bytes | Exception]) -> None:
        self.content = _Reader(watched_items)


class FakeV1Api:
    def __init__(
        self,
        first_run_items: list[bytes | Exception],
        watched_items: list[bytes | Exception],
    ) -> None:
        self._first_run_items = _Resp(first_run_items)
        self._resp = _Resp(watched_items)

    async def read_namespaced_pod_log(
        self,
        pod: str,
        namespace: str,
        tail_lines: int = 0,
        follow: bool = False,
        **kwargs: Any,
    ) -> str | _Resp:
        if follow:
            return self._resp
        else:
            return self._first_run_items


def _exhaust_queue(queue: asyncio.Queue) -> list[str]:
    items = []
    try:
        while True:
            items.append(queue.get_nowait())
    except asyncio.QueueEmpty:
        print("empty")
    return items


@pytest.mark.asyncio
async def test_read_timeout__read_log__should_retry() -> None:
    log_reader = K8LogReader(
        FakeV1Api(
            [
                b"log line 1",
                b"log line 2",
            ],
            [
                b"log line 2",
                b"first line",
                asyncio.TimeoutError(),  # the read log request times out.
                b"first line",
                b"second line",
                asyncio.CancelledError(),  # used to signal stop logging.
            ],
        )
    )
    try:
        await log_reader._print_pod_log()
    except asyncio.CancelledError:
        print("finished")

    queue_items = _exhaust_queue(log_reader._stream)
    assert queue_items == ["log line 1", "log line 2", "first line", "second line"]


@pytest.mark.asyncio
async def test_normal_read__read_log__no_entries_are_duplicate() -> None:
    log_reader = K8LogReader(
        FakeV1Api(
            [
                b"log line 0",
                b"log line 1",
            ],
            [
                b"log line 1",  # this line is identical to the one gathered in the first step. It is assumed this one will be removed.
                b"second log line",
                asyncio.CancelledError(),  # used to signal stop logging.
            ],
        )
    )

    try:
        await log_reader._print_pod_log()
    except asyncio.CancelledError:
        print("finsihed")

    queue_items = _exhaust_queue(log_reader._stream)

    assert queue_items == ["log line 0", "log line 1", "second log line"]


@pytest.mark.asyncio
async def test_empty_first_read__read_log__should_stream_all_messages() -> None:
    # perform a test where the first log run (with lines == 50) returns nothing.
    # then the streaming log should return a list of two. Both must be in result. No error should be reported.
    log_reader = K8LogReader(
        FakeV1Api(
            [],
            [
                b"log line 1",  # this line is identical to the one gathered in the first step. It is assumed this one will be removed.
                b"second log line",
                asyncio.CancelledError(),  # used to signal stop logging.
            ],
        )
    )

    try:
        await log_reader._print_pod_log()
    except asyncio.CancelledError:
        print("finsihed")

    queue_items = _exhaust_queue(log_reader._stream)

    assert queue_items == ["log line 1", "second log line"]


@pytest.mark.asyncio
async def test_non_overlapping_log_messages__read_log__should_have_warning_message() -> None:
    log_reader = K8LogReader(
        FakeV1Api(
            [b"log line 0"],
            [
                b"log line 1",  # this line is identical to the one gathered in the first step. It is assumed this one will be removed.
                b"second log line",
                asyncio.CancelledError(),  # used to signal stop logging.
            ],
        )
    )

    try:
        await log_reader._print_pod_log()
    except asyncio.CancelledError:
        print("finsihed")

    queue_items = _exhaust_queue(log_reader._stream)

    assert queue_items == [
        "log line 0",
        "WARNING. MIGHT HAVE LOST A LOGLINE",
        "log line 1",
        "second log line",
    ]


@pytest.mark.asyncio
async def test_watch_log_lines_fully_overlap_first_run_items__read_log__should_not_have_duplicate_messages() -> None:
    log_reader = K8LogReader(
        FakeV1Api(
            [
                b"log line 0",
                b"log line 1",
            ],
            [
                b"log line 0",  # this line is identical to the one gathered in the first step. It is assumed this one will be removed.
                b"log line 1",
                b"log line 2",
                asyncio.TimeoutError(),
                b"log line 1",
                b"log line 2",
                b"log line 3",
                asyncio.CancelledError(),  # used to signal stop logging.
            ],
        )
    )

    try:
        await log_reader._print_pod_log()
    except asyncio.CancelledError:
        print("finsihed")

    queue_items = _exhaust_queue(log_reader._stream)

    assert queue_items == ["log line 0", "log line 1", "log line 2", "log line 3"]


@pytest.mark.asyncio
async def test_failing_log_data__read_log__is_handled_properly():
    log_reader = K8LogReader(
        FakeV1Api(
            [ValueError()],  # this will cause the reader to fail hard.
            [],
        )
    )

    log_reader.start()
    await asyncio.sleep(0.2)
    assert log_reader.is_reading is False
