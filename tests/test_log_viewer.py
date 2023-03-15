import pytest
from rich.color import Color, ColorType
from rich.console import Console
from rich.segment import Segment
from rich.style import Style
from rich.text import Text
from textual.strip import Strip

from glasses.controllers.log_provider import LogEvent
from glasses.widgets.log_viewer import LineCache, LogData


@pytest.fixture()
def console() -> Console:
    return Console()


@pytest.mark.asyncio()
async def test_log_event__add_item__populated(console):
    log_event = LogEvent("Raw text", Text("Raw text"))

    line_cache = LineCache(console, Style())
    await line_cache.add_log_events([log_event])

    assert len(line_cache) == 1
    assert len(line_cache._log_lines) == 1
    assert line_cache._max_width == 8


@pytest.mark.asyncio()
async def test_log_events__add_item__populated(console):
    log_events = [LogEvent(txt, Text(txt)) for txt in ("First line", "Second line")]

    line_cache = LineCache(console, Style())

    await line_cache.add_log_events(log_events)

    assert len(line_cache) == 2
    assert len(line_cache._log_lines) == 2

    assert line_cache[0].line_index == 0
    assert line_cache[1].line_index == 1


@pytest.mark.asyncio()
async def test_multiline_log_events__add_item__populated(console):
    log_events = [
        LogEvent(text, Text(text)) for text in ("Two\nLines", "Three\nlines\npart")
    ]

    line_cache = LineCache(console, Style())

    await line_cache.add_log_events(log_events)

    assert len(line_cache) == 2
    assert len(line_cache._log_lines) == 5

    assert line_cache[0].line_index == 0
    assert line_cache[1].line_index == 2


def test_log_event__log_data_highlight__is_correct(console):
    log_event = LogEvent("Two\nLines", Text("Two\nLines"))

    log_data = LogData(log_event, console, Style(bgcolor="blue"))

    # first a full run
    result = log_data.lines
    assert result == [Strip([Segment("Two")], 3), Strip([Segment("Lines")], 5)]
    cached_full_stage = log_data._render_stages["newline"]

    # second a highlight run
    log_data.highlight = True
    result = log_data.lines
    assert result == [
        Strip(
            [
                Segment(
                    "Two", Style(bgcolor=Color("blue", ColorType.STANDARD, number=4))
                )
            ],
            3,
        ),
        Strip(
            [
                Segment(
                    "Lines", Style(bgcolor=Color("blue", ColorType.STANDARD, number=4))
                )
            ],
            5,
        ),
    ]
    assert log_data._render_stages["newline"] is cached_full_stage

    log_data.highlight = False
    result = log_data.lines
    assert result == [Strip([Segment("Two")], 3), Strip([Segment("Lines")], 5)]


def test_log_event__colored_log_data__is_correct(console):
    log_event = LogEvent("Two\nLines", Text("Two\nLines", Style(color="red")))

    log_data = LogData(log_event, console, Style(bgcolor="blue"))
    log_data.highlight = True
    # first a full run
    result = log_data.lines
    assert result == [Strip([Segment("Two")], 3), Strip([Segment("Lines")], 5)]
