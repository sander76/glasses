import asyncio
from enum import Enum, auto
from functools import cached_property
from json import JSONDecodeError
from pathlib import Path
from typing import Iterator, NamedTuple

from rich.console import Console
from rich.json import JSON
from rich.style import Style
from rich.text import Lines, Text
from textual import events, on
from textual.app import ComposeResult, RenderResult
from textual.binding import Binding
from textual.geometry import Size
from textual.message import Message
from textual.reactive import Reactive, reactive
from textual.scroll_view import ScrollView
from textual.strip import Strip
from textual.widget import Widget
from textual.widgets import Button, Input, Static

from glasses.controllers.log_provider import LogEvent, LogReader
from glasses.widgets.dialog import IntegerDialog, QuestionDialog
from glasses.widgets.search import Search

LogDataLineIndex = int
LogDataIndex = int
OccurrenceCount = int


class State(Enum):
    IDLE = auto()
    LOGGING = auto()


class LoggingState(Static):
    """Display a logging state"""

    DEFAULT_CSS = """
    LoggingState {
        width: 100%;
    }
    """

    state = reactive(State.IDLE)

    def watch_state(self, state: State) -> None:
        match state:
            case State.IDLE:
                self.remove_class("logging")
                self.add_class("not_logging")
                self.update("not logging")
            case State.LOGGING:
                self.remove_class("not_logging")
                self.add_class("logging")
                self.update("logging")


class Info(Static):
    namespace = reactive("unknown")
    pod_name = reactive("unknown")
    tail = reactive(500)

    def render(self) -> RenderResult:
        return f"namespace:{self.namespace}  pod:{self.pod_name}  tail:{self.tail}"


class StateCache(NamedTuple):
    line_length: int
    selected: bool
    expanded: bool
    search_text: str


class LogData:
    def __init__(
        self,
        log_event: LogEvent,
        console: Console,
    ) -> None:
        self._console = console

        self.log_event = log_event

        # start index of lines collection where this piece of logdata starts.
        self.line_index: int = -1

        # raw lines without ui styling like selected, search highlight.
        self._raw_lines: Lines

        # styled lines including ui styling like selected, search highlight.
        self._lines: list[Strip] = []
        self._max_width: int = -1

        self.selected: bool = False
        self.expanded: bool = False

        self._state: StateCache = StateCache(
            line_length=-1, selected=False, search_text="", expanded=self.expanded
        )
        self.line_count = 0
        self._render_plain()

    def toggle_expand(self) -> None:
        self.expanded = not self.expanded
        self._render_plain()

    def search(self, search_string: str) -> int:
        """Return the number of occurrences in the logentry."""
        return self.log_event.parsed.plain.count(search_string)

    def _render_plain(self) -> None:
        self._max_width = 0
        new_line = self.log_event.parsed.copy()
        if self.expanded:
            new_line.append("\n\n")
            raw = self.log_event.raw

            styled_raw: Text | str
            try:
                styled_raw = JSON(raw).text
            except JSONDecodeError:
                styled_raw = raw

            new_line.append(styled_raw)
            new_line.append("\n")

        self._raw_lines = new_line.split(allow_blank=True)
        self._max_width = max(len(line) for line in self._raw_lines)
        self.line_count = len(self._raw_lines)

    def _render(
        self,
        search_text: str,
        line_length: int,
        selected_style: Style,
    ) -> Iterator[Strip]:
        # need to provide these render options. otherwise horizontal
        # scrolling becomes erratic (random characters everywhere).
        render_options = self._console.options
        render_options = render_options.update(width=line_length, overflow="ignore")

        for raw_line in self._raw_lines:
            styled_line = raw_line.copy()

            if search_text:
                styled_line.highlight_words([search_text], "black on yellow")

            styled_line.align("left", line_length)

            if self.selected:
                styled_line.stylize(selected_style.background_style)

            yield Strip(self._console.render(styled_line, render_options), line_length)

    def update(
        self,
        selected_style: Style,
        search_text: str,
        line_length: int,
    ) -> None:
        """Update the output of the logdata"""
        new_state = StateCache(
            line_length=line_length,
            selected=self.selected,
            search_text=search_text,
            expanded=self.expanded,
        )

        if len(self._lines) > 0 and self._state == new_state:
            return

        self._lines = list(self._render(search_text, line_length, selected_style))
        self._state = new_state


class LineCache:
    def __init__(self, console: Console) -> None:
        self._log_data: list[LogData] = []

        # A list which keeps track of a single UI-line and the  corresponsing log line
        #
        # The list index corresponds to the UI lines. The value
        # corresponds to the Logdata and LogData-index

        # idx   value
        # 0     LogData_1, 0, 0  -> logline 0 corresponds with line_index 0 of LogData_1. LogData_1 is index 0 of log-lines_list
        # 1     LogData_2, 0, 1  -> logline 1 corresponds with line_index 0 of LogData_2. LogData_2 is index 1 of log_lines_list
        # 2     LogData_2, 1, 1  -> logline 2 corresponds with line_index 1 of LogData_2. LogData_2 is index 1 of log_lines_list
        #
        # Using the above example it is easy to get the logdata
        # based on the provided log_line_index.
        self._log_lines_idx__log_data_idx: list[tuple[LogData, int, LogDataIndex]] = []

        self._max_width: int = 0
        self._console = console

    def log_data_index_from_line_index(self, line_idx: int) -> int:
        _, _, log_data_index = self._log_lines_idx__log_data_idx[line_idx]
        return log_data_index

    @property
    def log_data(self) -> list[LogData]:
        return self._log_data

    @property
    def line_count(self) -> int:
        """Return the amount of lines/Strips"""

        return len(self._log_lines_idx__log_data_idx)

    @property
    def log_data_count(self) -> int:
        return len(self._log_data)

    def line(
        self,
        line_idx: int,
        search_text: str,
        selected_style: Style,
        line_length: int,
    ) -> Strip:
        log_data, log_data_line_idx, _ = self._log_lines_idx__log_data_idx[line_idx]
        log_data.update(
            selected_style=selected_style,
            search_text=search_text,
            line_length=line_length,
        )

        return log_data._lines[log_data_line_idx]

    def toggle_expand(self, log_data_idx: int) -> None:
        log_data = self._log_data[log_data_idx]
        log_data.toggle_expand()
        self._reconstruct_index()

    def _reconstruct_index(self) -> None:
        self._max_width = 0
        self._log_lines_idx__log_data_idx = []
        for idx, log_data in enumerate(self.log_data):
            log_data.line_index = len(self._log_lines_idx__log_data_idx)
            self._log_lines_idx__log_data_idx.extend(
                self._lines_construct_from_log_data(log_data, idx)
            )
            self._max_width = max(self._max_width, log_data._max_width)

    async def add_log_events(self, log_events: list[LogEvent]) -> Size:
        for log_event in log_events:
            log_data = LogData(log_event, self._console)
            log_data.line_index = len(self._log_lines_idx__log_data_idx)
            self._log_lines_idx__log_data_idx.extend(
                self._lines_construct_from_log_data(log_data, len(self._log_data))
            )

            self._log_data.append(log_data)
            self._max_width = max(self._max_width, log_data._max_width)
        return Size(self._max_width, len(self._log_lines_idx__log_data_idx))

    def _lines_construct_from_log_data(
        self, log_data: LogData, log_data_index: int
    ) -> list[tuple[LogData, int, LogDataIndex]]:
        new_list: list[tuple[LogData, int, LogDataIndex]] = []
        for idx in range(log_data.line_count):
            new_list.append((log_data, idx, log_data_index))
        return new_list


class LogOutput(ScrollView, can_focus=True):
    BINDINGS = [
        ("x", "expand", "Expand"),
        Binding("down", "cursor_down", "Cursor Down", show=False),
        Binding("up", "cursor_up", "Cursor Up", show=False),
    ]

    COMPONENT_CLASSES = {"logoutput--highlight"}

    DEFAULT_CSS = """
    LogOutput .logoutput--highlight {
        background: $secondary 10%;
    }
    """
    current_row: Reactive[int] = Reactive(-1)
    _line_cache: LineCache

    class SearchResultCountChanged(Message):
        """Search result count message changed."""

        def __init__(self, count: dict[LogDataIndex, OccurrenceCount]) -> None:
            self.count = count
            super().__init__()

    def __init__(self, reader: LogReader) -> None:
        super().__init__(classes="focusable")
        self._reader = reader
        self._highlight_text: str = ""
        self._render_width: int = -1
        self._search_text_task: asyncio.Task | None = None

    def on_mount(self) -> None:
        self._line_cache = LineCache(self.app.console)
        asyncio.create_task(self._watch_log())
        super().on_mount()

    @staticmethod
    def new_scroll(
        view_y_top: int, view_y_bottom: int, log_data_y_top: int, log_data_y_bottom: int
    ) -> int | None:
        """Return a new value to scroll to.

        Returns:
            a value to scroll to (the top Y coordinate.) Or None if no scrolling required.
        """
        scroll_to: int = 0
        if view_y_top <= log_data_y_top:
            if view_y_bottom < log_data_y_bottom:
                delta_y = log_data_y_bottom - view_y_bottom
                scroll_to = view_y_top + delta_y
                return scroll_to
            else:
                # all inside the view.
                return None
        else:
            delta_y = log_data_y_top - view_y_top
            scroll_to = view_y_top + delta_y
            return scroll_to

    @property
    def render_width(self) -> int:
        return max(self.size.width, self._line_cache._max_width)

    def _scroll_cursor_into_view(self) -> None:
        """When the cursor is at a boundary of the LogOutput and moves out
        of view, this method handles scrolling to ensure it remains visible."""
        log_data = self._line_cache.log_data[self.current_row]

        view_y_top = self.scroll_offset.y
        view_y_bottom = (
            self.scroll_offset.y + self.size.height - 1
        )  # -1 for the horizontal scrollbar

        log_data_y_top = log_data.line_index
        log_data_y_bottom = log_data.line_index + log_data.line_count

        scroll_value = LogOutput.new_scroll(
            view_y_top, view_y_bottom, log_data_y_top, log_data_y_bottom
        )
        if scroll_value is not None:
            self.scroll_to(None, scroll_value, animate=False)

    def watch_current_row(self, old_row: int, new_row: int) -> None:
        if new_row == -1:
            return
        if old_row > -1:
            self._line_cache.log_data[old_row].selected = False

        self._line_cache.log_data[new_row].selected = True

        self._scroll_cursor_into_view()

    def action_cursor_down(self) -> None:
        if self.current_row == self._line_cache.log_data_count - 1:
            # at the bottom of the list. do nothing
            return
        if self.current_row == -1:
            self.current_row = 0
        else:
            self.current_row += 1

    def action_cursor_up(self) -> None:
        if self.current_row <= 0:
            return
        self.current_row -= 1

    async def _on_click(self, event: events.Click) -> None:
        corresponding_line_index = self.scroll_offset.y + event.y
        if corresponding_line_index > self._line_cache.line_count:
            # You clicked on the screen, but there was no log_data there.
            return
        self.current_row = self._line_cache.log_data_index_from_line_index(
            corresponding_line_index
        )

    def render_line(self, y: int) -> Strip:
        scroll_x, scroll_y = self.scroll_offset

        strip = self._render_line(scroll_y + y, scroll_x, self.size.width)
        return strip

    def _render_line(self, log_line_idx: int, scroll_x: int, width: int) -> Strip:
        if log_line_idx >= self._line_cache.line_count:
            return Strip.blank(width)
        rich_style = self.get_component_rich_style("logoutput--highlight")

        return (
            self._line_cache.line(
                log_line_idx, self._highlight_text, rich_style, self.render_width
            )
        ).crop(scroll_x, scroll_x + width)

    async def add_log_event(self, log_events: list[LogEvent]) -> None:
        size = await self._line_cache.add_log_events(log_events)

        self.virtual_size = size

    def clear_log(self) -> None:
        self._line_cache = LineCache(self._console)
        self.virtual_size = Size(0, 0)
        self.current_row = -1
        self.refresh()

    async def _watch_log(self) -> None:
        delay = 0.2  # second
        max_item_length = 100

        send_task: asyncio.Task | None = None
        log_items: list[LogEvent] = []

        is_sending: bool = False
        sending: asyncio.Event = asyncio.Event()

        async def send_with_delay() -> None:
            nonlocal log_items
            nonlocal is_sending
            try:
                if not len(log_items) >= max_item_length:
                    await asyncio.sleep(delay)
                is_sending = True
                await self.add_log_event(log_items)

                is_sending = False
                log_items = []
                sending.set()
            except asyncio.CancelledError:
                self.log("Stopping sending with delay task.")

        async for log_event in self._reader.read():
            if send_task:
                if is_sending:
                    await sending.wait()
                else:
                    send_task.cancel()
            log_items.append(log_event)
            send_task = asyncio.create_task(send_with_delay())

    def action_expand(self) -> None:
        if self.current_row < 0:
            return
        self._line_cache.toggle_expand(self.current_row)

        # virtual size has changed.
        self.virtual_size = Size(
            self._line_cache._max_width, self._line_cache.line_count
        )

    def highlight(self, search_text: str) -> None:
        self._highlight_text = search_text
        self.search_log_items(search_text)
        self.refresh()

    def search_log_items(self, search_text: str) -> None:
        async def _search_task() -> dict[LogDataIndex, OccurrenceCount]:
            """Look for occurrences of search_text inside the log output.

            Returns:
                a dict where the key is a logline index
                    and the value the amount of occurrences of the search text
            """
            if search_text == "":
                return {}

            # mappable with the key as the log_item index, the amount of
            # occurrences of the search_text.
            search_items: dict[LogDataIndex, OccurrenceCount] = {}

            for idx, log_item in enumerate(self._line_cache.log_data):
                count = log_item.search(search_text)
                if count:
                    search_items[idx] = count
            return search_items

        def count_finished(result: asyncio.Future) -> None:
            try:
                count = result.result()
            except asyncio.CancelledError:
                self.log("Task cancelled. doing nothing")
                count = {}
            self.post_message(self.SearchResultCountChanged(count))

        if self._search_text_task is not None:
            self._search_text_task.cancel()

        self._search_text_task = asyncio.create_task(_search_task())
        self._search_text_task.add_done_callback(count_finished)


class LogViewer(Static, can_focus=True):
    BINDINGS = [
        ("s", "start", "Start"),
        ("t", "stop", "Stop"),
        ("c", "clear", "Clear"),
        ("h", "history", "History"),
        ("ctrl+s", "search", "Search"),
    ]

    def __init__(self, reader: LogReader) -> None:
        super().__init__(id="log-viewer")
        self.reader = reader
        self._log_output = LogOutput(self.reader)
        self._search_result: dict[LogDataIndex, OccurrenceCount]

    @cached_property
    def log_output(self) -> LogOutput:
        return self.query_one("LogOutput", expect_type=LogOutput)

    @cached_property
    def search(self) -> Search:
        return self.query_one("Search", expect_type=Search)

    def compose(self) -> ComposeResult:
        yield Info()
        yield Search()
        yield LoggingState()
        yield self._log_output

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "savelog":
            self.action_save_log()
        if event.button.id == "navigate_to_next_search_result":
            current_selected_item = self._log_output.current_row

            for item in self._search_result.keys():
                if item > current_selected_item:
                    break
            else:
                return
            self._log_output.current_row = item

    async def start(self) -> None:
        async def _start(proceed: bool) -> None:
            """This is either directly called or as a callback from the push-screen inside this function."""
            if not proceed:
                return

            await self.reader.stop()
            self.action_clear()
            self.query_one(
                "LoggingState", expect_type=LoggingState
            ).state = State.LOGGING
            self.reader.start()

        if self.reader.is_reading:
            self.app.push_screen(QuestionDialog("Stop current logging?"), _start)
        else:
            await _start(True)

    async def action_start(self) -> None:
        await self.start()

    async def action_stop(self) -> None:
        (self.query_one("LoggingState", expect_type=LoggingState)).state = State.IDLE
        await self.reader.stop()

    def action_clear(self) -> None:
        self._log_output.clear_log()

    def action_save_log(self) -> None:
        with open(Path.home() / "log_output.txt", "w") as file:
            lines = (
                log_data.log_event.raw
                for log_data in self._log_output._line_cache.log_data
            )

            file.writelines("\n".join(lines))

    def action_history(self) -> None:
        """The amount of lines to fetch."""

        async def _set_history(history: int | None) -> None:
            if history is None:
                return
            self.reader.tail = history

            info = self.query_one("Info", expect_type=Info)
            info.tail = history
            await self.reader.stop()
            self.action_clear()
            await self.start()

        self.app.push_screen(
            IntegerDialog("tail value", self.reader.tail), _set_history
        )

    def action_search(self) -> None:
        search = self.query_one("Search", expect_type=Search)
        search.toggle_class("hide")

    @on(Input.Changed, "#search_input")
    async def _on_search_changed(self, event: Input.Changed) -> None:
        event.stop()
        self._log_output.highlight(event.value)

    @on(LogOutput.SearchResultCountChanged)
    def _result_count_changed(self, event: LogOutput.SearchResultCountChanged) -> None:
        self._search_result = event.count
        self.search.search_count = sum(event.count.values())

    async def on_unmount(self) -> None:
        await self.reader.stop()

    async def on_show(self) -> None:
        info = self.query_one("Info", expect_type=Info)
        info.pod_name = self.reader.pod
        info.namespace = self.reader.namespace
        self.query_one("LogOutput", expect_type=LogOutput).focus()

    # def on_log_output_search_result_count_changed(
    #     self, event: LogOutput.SearchResultCountChanged
    # ) -> None:
    #     self._search_result = event.count
    #     self._log_control.update_search_result_count(event.count)


# class LogControl(Widget):
#     DEFAULT_CSS = """
#     LogControl {
#         height: auto;
#         dock: top;
#         layout: vertical;
#     }

#     LogControl Input {
#         height: 1;
#         border: none;
#         min-width: 10;
#         padding: 0;
#         margin: 0 1;
#         background: $accent-darken-2;
#     }

#     LogControl Input:focus {
#         border: none;
#     }
#     #tail {
#         width:10;
#     }
#     #search {
#         width: 20;
#     }
#     #namespace {
#         width: 12;
#     }
#     #pod_name {
#         width: 100%;
#     }
#     LogControl Button {
#         height: 1;
#         border: none;
#         border-top: none;
#         border-bottom: none;
#     }

#     LogControl Button:hover {
#         border-top: none;
#     }

#     LogControl Button.-active {
#         border-bottom: none;
#         border-top: none;
#     }
#     LogControl Horizontal {
#         height:auto;

#     }
#     Label {
#         min-width: 12
#     }
#     """

#     def __init__(self, reader: LogReader) -> None:
#         super().__init__()
#         self._reader = reader
#         self._reader.subscribe("namespace", self._update_namespace)
#         self._reader.subscribe("pod", self._update_pod)

#     def _update_namespace(self, _: str) -> None:
#         self.query_one("#namespace", expect_type=Input).value = self._reader.namespace

#     def _update_pod(self, _: str) -> None:
#         self.query_one("#pod_name", expect_type=Input).value = self._reader.pod

#     def update_search_result_count(
#         self, result: dict[LogDataIndex, OccurrenceCount]
#     ) -> None:
#         total_count = sum(
#             search_result_count for search_result_count in result.values()
#         )
#         self.query_one("#search_results", expect_type=Label).update(str(total_count))

#     def compose(self) -> ComposeResult:
#         yield Horizontal(
#             Label("namespace: "),
#             Input(self._reader.namespace, id="namespace"),
#             Label("pod name: "),
#             Input(self._reader.pod, id="pod_name"),
#         )
#         yield Horizontal(
#             Label("logtail"),
#             Input(str(self._reader.tail), id="tail"),
#             Label("search"),
#             Input(self._reader.highlight_text, id="search"),
#             Label("0", id="search_results"),
#             Button("next", id="navigate_to_next_search_result"),
#         )
#         yield Horizontal(
#             Button("save log", id="savelog"),
#         )

#     async def on_input_changed(self, event: Input.Changed) -> None:
#         if event.input.id == "tail":
#             try:
#                 value = int(event.value)
#             except ValueError:
#                 val = self.query_one("#tail", Input)
#                 val.value = str(self._reader.tail)
#             else:
#                 self._reader.tail = value
#             event.stop()
#         elif event.input.id == "search":
#             self._reader.highlight_text = event.value
