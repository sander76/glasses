import pytest
from rich.color import Color, ColorType
from rich.console import Console
from rich.segment import Segment
from rich.style import Style
from rich.text import Text
from textual.strip import Strip

from glasses.controllers.log_provider import LogEvent
from glasses.widgets.log_viewer import LineCache, LogData, LogOutput


@pytest.fixture()
def console() -> Console:
    return Console()


@pytest.mark.asyncio()
async def test_log_event__add_item__populated(console):
    log_event = LogEvent("Raw text", Text("Raw text"))

    line_cache = LineCache(console, Style())
    await line_cache.add_log_events([log_event])

    assert line_cache.log_data_count == 1
    assert line_cache.line_count == 1
    assert line_cache._max_width == 8


@pytest.mark.asyncio()
async def test_log_events__add_item__populated(console):
    log_events = [LogEvent(txt, Text(txt)) for txt in ("First line", "Second line")]

    line_cache = LineCache(console, Style())

    await line_cache.add_log_events(log_events)

    assert line_cache.log_data_count == 2
    assert line_cache.line_count == 2

    assert line_cache[0].line_index == 0
    assert line_cache[1].line_index == 1


@pytest.mark.asyncio()
async def test_multiline_log_events__add_item__populated(console):
    log_events = [
        LogEvent(text, Text(text)) for text in ("Two\nLines", "Three\nlines\npart")
    ]

    line_cache = LineCache(console, Style())

    await line_cache.add_log_events(log_events)

    assert line_cache.log_data_count == 2
    assert len(line_cache._log_lines) == 5

    assert line_cache[0].line_index == 0
    assert line_cache[1].line_index == 2


def test_log_event__log_data_highlight__is_correct(console):
    log_event = LogEvent("Two\nLines", Text("Two\nLines"))

    log_data = LogData(
        log_event,
        console,
        console.options.update(overflow="ignore", no_wrap=True),
        Style(bgcolor="blue"),
    )

    # first a full run
    result = log_data.lines
    assert result == [
        Strip([Segment("Two"), Segment("  ")], 5),
        Strip([Segment("Lines")], 5),
    ]
    cached_full_stage = log_data._render_stages["newline"]

    # second a highlight run
    log_data.highlight = True
    result = log_data.lines
    assert result == [
        Strip(
            [
                Segment(
                    "Two", Style(bgcolor=Color("blue", ColorType.STANDARD, number=4))
                ),
                Segment("  "),
            ],
            5,
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
    assert result == [
        Strip([Segment("Two"), Segment("  ")], 5),
        Strip([Segment("Lines")], 5),
    ]


# def test_log_event__update_log_data__


def test_scroll_data_below_view_window():
    """
    view_y_top     -------
                   |
                   |
                   |
                   |    ------- log_data_y_top
                   |          |
    view_y_bottom  -------    |
                              |
                        ------- log_data_y_bottom

    """
    input = {
        "view_y_top": 10,
        "view_y_bottom": 16,
        "log_data_y_top": 14,
        "log_data_y_bottom": 18,
    }

    # the view window needs to shift two downwards to fit the log_data
    expected_new_view_y_top = 12

    value = LogOutput.new_scroll(**input)

    assert value == expected_new_view_y_top


def test_scroll_data_above_view_window():
    """
                        ------- log_data_y_top
    view_y_top     -------    |
                   |          |
                   |    ------- log_data_y_bottom
                   |
                   |
                   |
    view_y_bottom  -------

    """
    input = {
        "view_y_top": 10,
        "view_y_bottom": 16,
        "log_data_y_top": 8,
        "log_data_y_bottom": 12,
    }

    # the view window needs to shift two downwards to fit the log_data
    expected_new_view_y_top = 8

    value = LogOutput.new_scroll(**input)

    assert value == expected_new_view_y_top


@pytest.mark.asyncio()
async def test_log_event_expand__lines__success(console):
    log_event1 = LogEvent("Log event 1", Text("Log event 1"))
    log_event2 = LogEvent("Log event 2", Text("Log event 2"))

    line_cache = LineCache(console, Style())
    await line_cache.add_log_events([log_event1, log_event2])

    assert line_cache.line_count == 2
    assert line_cache.line_count == len(line_cache._log_lines_idx__log_data_idx)
    assert line_cache.log_data_index_from_line_index(0) == 0
    assert line_cache.log_data_index_from_line_index(1) == 1

    first_log_data = line_cache[0]
    first_log_data.expanded = True

    line_cache.update_log_data(0)

    assert line_cache.line_count == 4  # Expanded logevent has an empty line added.
    assert len(line_cache._log_lines_idx__log_data_idx) == 4
    assert line_cache.log_data_index_from_line_index(0) == 0
    assert line_cache.log_data_index_from_line_index(1) == 0
    assert line_cache.log_data_index_from_line_index(2) == 0
    assert line_cache.log_data_index_from_line_index(3) == 1
