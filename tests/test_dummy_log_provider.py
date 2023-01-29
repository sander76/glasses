import pytest
import pytest_asyncio
from textual.widgets import Label

from glasses.controllers.log_provider import DummyLogReader, LogEvent


@pytest_asyncio.fixture
async def dummylogger():
    log_provider = DummyLogReader()
    log_provider.delay = 0.01
    log_provider.start()
    yield log_provider

    log_provider.stop()


@pytest.mark.asyncio
async def test_dummy_log_provider__returns_valid_data(dummylogger):

    first_item = await anext(dummylogger.read())

    assert isinstance(first_item, LogEvent)


@pytest.mark.asyncio
async def test_dummy_log_data__returns_valid_data(dummylogger):
    max_items = 10
    item_nr = 0

    async for item in dummylogger.read():
        item_nr += 1

        assert isinstance(item, LogEvent)
        Label(item.raw)
        Label(item.parsed)
        if item_nr == max_items:
            break
