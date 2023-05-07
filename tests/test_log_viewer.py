import pytest
from rich.color import Color, ColorType
from rich.console import Console
from rich.segment import Segment
from rich.style import Style
from rich.text import Text
from textual.strip import Strip

from glasses.controllers.log_provider import LogEvent
from glasses.widgets.log_viewer import LineCache, LogOutput


@pytest.fixture()
def console() -> Console:
    return Console()


@pytest.mark.asyncio()
async def test_log_event__add_item__populated(console):
    log_event = LogEvent("Raw text", Text("Raw text"))

    line_cache = LineCache(console)
    await line_cache.add_log_events([log_event])

    assert line_cache.log_data_count == 1
    assert line_cache.line_count == 1
    assert line_cache._max_width == 8


@pytest.mark.asyncio()
async def test_log_events__add_item__populated(console):
    log_events = [LogEvent(txt, Text(txt)) for txt in ("First line", "Second line")]

    line_cache = LineCache(console)

    await line_cache.add_log_events(log_events)

    assert line_cache.log_data_count == 2
    assert line_cache.line_count == 2
    assert line_cache._max_width == 11


# def test_plain_line__render__correct_output():
#     log_data = LogData(LogEvent("First line", parsed=Text("First line")))
#     assert False


# def test_selected__render__correct_output():
#     assert False

# def test_search__render__correct_output():
#     assert False

# def test_expanded__render__correct_output():
#     assert False

# def test_expanded_selected_search__render__correct_output():
#     assert False


# def test_call_update_twice__render_only_called_once():
#     assert False

# def test_expand_logdata__all_lines__correct_output():
#     """Three log data items.

#     The middle one is expanded. check output
#     The middle one is nox expanded. check output
#     """
#     assert False


@pytest.mark.asyncio
async def test_single_log_event__get_lines__returns_rendered_line(console):
    log_events = [LogEvent("First line", Text("First line"))]

    line_cache = LineCache(console)

    await line_cache.add_log_events(log_events)

    line_1 = line_cache.line(0, "", Style(bgcolor="blue"), 10)

    assert line_1 == Strip([Segment("First line"), Segment("\n")], 10)


@pytest.mark.asyncio()
async def test_multiline_log_events__get_lines__correct_result(console):
    log_events = [LogEvent("Two\nLines", Text("Two\nLines"))]
    irrelevant_style = Style(bgcolor="blue")
    line_cache = LineCache(console)

    await line_cache.add_log_events(log_events)

    line_0 = line_cache.line(0, "", irrelevant_style, 5)
    line_1 = line_cache.line(1, "", irrelevant_style, 5)

    assert len(line_cache._log_lines_idx__log_data_idx) == 2
    assert line_0 == Strip([Segment("Two  "), Segment("\n")], 5)
    assert line_1 == Strip([Segment("Lines"), Segment("\n")], 5)


@pytest.mark.asyncio
async def test_single_log_event__expand_and_unexpand__correct_result(console):
    """expand a log event, check result, unexpand log event, check result"""
    log_events = [
        LogEvent("Raw First line", Text("First line")),
        # LogEvent("Raw second line", Text("Second line")),
    ]
    irrelevant_style = Style(bgcolor="blue")
    line_cache = LineCache(console)

    await line_cache.add_log_events(log_events)

    lines = [
        line_cache.line(idx, "", irrelevant_style, 14)
        for idx in range(line_cache.line_count)
    ]

    line_cache.toggle_expand(0)

    lines = [
        line_cache.line(idx, "", irrelevant_style, 14)
        for idx in range(line_cache.line_count)
    ]
    assert lines == [
        Strip([Segment("First line    "), Segment("\n")], 14),
        Strip([Segment("              "), Segment("\n")], 14),
        Strip([Segment("Raw First line"), Segment("\n")], 14),
        Strip([Segment("              "), Segment("\n")], 14),
    ]

    line_cache.toggle_expand(0)
    lines = [
        line_cache.line(idx, "", irrelevant_style, 10)
        for idx in range(line_cache.line_count)
    ]
    assert lines == [
        Strip([Segment("First line"), Segment("\n")], 10),
    ]


@pytest.mark.asyncio
async def test_single_log_event__select_and_unselect__correct_result(console):
    """Select a log event, check result, unselect a log event check result."""
    log_events = [LogEvent("First line", Text("First line"))]
    selected_style = Style(bgcolor=Color("blue", ColorType.STANDARD, number=4))
    line_cache = LineCache(console)

    await line_cache.add_log_events(log_events)
    log_data = line_cache.log_data[0]
    log_data.selected = True

    line_1 = line_cache.line(
        0,
        "",
        selected_style,  # use this style to highlight te selection.
        line_length=20,
    )

    assert line_1 == Strip(
        [Segment("First line          ", selected_style), Segment("\n")], 20
    )

    log_data.selected = False
    line_1 = line_cache.line(
        0,
        "",
        selected_style,  # use this style to highlight te selection.
        line_length=20,
    )
    assert line_1 == Strip(
        [Segment("First line          "), Segment("\n")], 20
    ), "there should be no styling applied to the test as this would indicate the item is still selected."


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
