import asyncio
from enum import Enum, auto
from typing import Any, NamedTuple

from rich.console import Console, ConsoleOptions
from rich.json import JSON
from rich.measure import measure_renderables
from rich.style import Style
from textual import events, log
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.geometry import Size
from textual.reactive import Reactive, reactive
from textual.scroll_view import ScrollView
from textual.strip import Strip
from textual.widget import Widget
from textual.widgets import Button, Input, Label, Static

from glasses.controllers.log_provider import LogEvent, LogReader
from glasses.namespace_provider import Pod
from glasses.widgets.dialog import DialogResult, StopLoggingScreen, show_dialog


class State(Enum):
    IDLE = auto()
    LOGGING = auto()


class LoggingState(Static):
    """Display a logging state"""

    DEFAULT_CSS = """
    LoggingState {
        width: 100%;
    }
    .logging {
        background: $success;
    }
    .not_logging {
        background: $warning;
    }
    """
    state = reactive(State.IDLE)

    def __init__(self, reader: LogReader) -> None:
        reader.subscribe("is_reading", self.is_reading_changed)
        super().__init__(classes="not_logging")

    def is_reading_changed(self, state: State) -> None:
        if state:
            self.state = State.LOGGING
            self.remove_class("not_logging")
            self.add_class("logging")
        else:
            self.state = State.IDLE
            self.remove_class("logging")
            self.add_class("not_logging")

    def render(self) -> str:
        if self.state == State.IDLE:
            return "not logging"
        return "logging"


class LogControl(Widget):
    DEFAULT_CSS = """
    LogControl {
        height: auto;
        dock: top;
        layout: vertical;
    }
    .small_input {
        height: 1;
        border: none;
        background: blue;
        width: 50;
    }
    .small_input:focus {
        border: none;
    }


    LogControl Button {
        width: auto;
        min-width: 20;
        height: 1;
        background: $panel;
        color: $text;
        border: none;
        border-top: none;
        border-bottom: none;
        /* content-align: center top; */
        text-style: bold;
    }

    LogControl Button:focus {
        color: $secondary;
    }

    """

    def __init__(self, reader: LogReader) -> None:
        super().__init__()
        self._reader = reader
        self._logging_state = LoggingState(reader)
        self._reader.subscribe("namespace", self._update_namespace)
        self._reader.subscribe("pod", self._update_pod)

    def _update_namespace(self, _: str) -> None:
        self.query_one("#namespace", expect_type=Input).value = self._reader.namespace

    def _update_pod(self, _: str) -> None:
        self.query_one("#pod_name", expect_type=Input).value = self._reader.pod

    def compose(self) -> ComposeResult:
        yield Horizontal(
            Label("namespace: "),
            Input(self._reader.namespace, id="namespace", classes="small_input"),
            Label("logtail"),
            Input(str(self._reader.tail), id="tail", classes="small_input"),
        )
        yield Horizontal(
            Label("pod name: "),
            Input(self._reader.pod, id="pod_name", classes="small_input"),
            Label("search"),
            Input(self._reader.highlight_text, id="search", classes="small_input"),
        )
        yield Horizontal(
            Button("log", id="startlog"),
            Button("stop", id="stoplog"),
            Button("clear log", id="clearlog"),
        )
        yield self._logging_state

    async def on_input_changed(self, event: Input.Changed) -> None:

        if event.input.id == "tail":
            try:
                value = int(event.value)
            except ValueError:
                val = self.query_one("#tail", Input)
                val.value = str(self._reader.tail)
            else:
                self._reader.tail = value
            event.stop()
        elif event.input.id == "search":
            self._reader.highlight_text = event.value


class StateCache(NamedTuple):
    expanded: bool
    search_text: str
    highlight: bool
    # line_count: int


class LogData:
    def __init__(
        self,
        log_event: LogEvent,
        console: Console,
        render_settings: ConsoleOptions,
        highligh_style: Style,
    ) -> None:
        self._console = console
        self._render_settings = render_settings

        self.log_event = log_event
        self._rich_style = highligh_style

        # start index of lines collection where this piece of logdata starts.
        self.line_index: int = -1

        self.expanded = False
        self.search_text: str = ""
        self.highlight: bool = False

        self.search_matches: int = 0

        self._render_stages = {"newline": None, "search_text": None}
        self._lines: list[Strip] = []
        self._max_width: int = 0

        self._current_state: StateCache = self.get_current_state()
        super().__init__()

    def get_current_state(self) -> StateCache:
        return StateCache(self.expanded, self.search_text, self.highlight)

    def update(self) -> bool:
        """Update the output of the logdata

        Returns:
            A boolean indicating whether the line_count has changed.
        """
        new_state = self.get_current_state()
        if self.line_count == 0 or new_state.expanded != self._current_state.expanded:
            stage = "full"
        elif new_state.search_text != self._current_state.search_text:
            stage = "search"
        elif new_state.highlight != self._current_state.highlight:
            stage = "highlight"
        else:
            # nothing to update and no re-indexing necessary
            return False

        old_line_length = self.line_count
        if stage == "full":
            log("doing a full log update")
            new_line = self.log_event.parsed.copy()
            if self.expanded:

                new_line.append("\n\n")
                raw = self.log_event.raw
                if isinstance(raw, JSON):
                    raw = raw.text
                new_line.append(raw)
            self._render_stages["newline"] = new_line

        if stage in ["full", "search"]:
            log("doing a search update")
            _line = self._render_stages["newline"].copy()

            if self.search_text:
                self.search_matches = _line.highlight_regex(
                    self.search_text, "black on yellow"
                )
            self._render_stages["search_text"] = _line

        if stage in ["full", "search", "highlight"]:
            log("doing a highlight update")
            _line = self._render_stages["search_text"].copy()
            if self.highlight:
                _line.stylize(self._rich_style.background_style)

            self._render_stages["highlight"] = _line

        render_width = measure_renderables(
            self._console, self._render_settings, [self._render_stages["highlight"]]
        ).maximum
        self._max_width = max(self._max_width, render_width)
        segments = self._console.render_lines(
            self._render_stages["highlight"],
            options=self._render_settings.update_width(render_width),
        )

        # this should be cached too.
        self._lines = [Strip(segment, cell_length=render_width) for segment in segments]

        self._current_state = self.get_current_state()
        return old_line_length != self.line_count

    @property
    def lines(self) -> list[Strip]:
        self.update()
        return self._lines

    @property
    def line_count(self) -> int:
        return len(self._lines)

    @property
    def max_width(self) -> int:
        return self._max_width


class LineCache:
    def __init__(self, console: Console, highlight_style: Style) -> None:
        self._log_data: list[LogData] = []
        self._log_lines: list[Strip] = []

        # A list which is kept in sync with the above _log_lines list.
        # The list indices correspond to the log_lines. The value
        # corresponds to the index of the log_data list

        # idx   value
        # 0     1  -> logline 0 corresponds with log_data 1
        # 1     1  -> logline 1 corresponds with log_data 1
        # 2     2  -> logline 2 corresponds with log_data 2
        #
        # Using the above example it is easy to get the logdata
        # based on the provided log_line_index.
        self._log_lines_idx__log_data_idx: list[int] = []

        self._max_width: int = 0
        self._console = console
        self._render_options: ConsoleOptions = console.options.update(
            overflow="ignore", no_wrap=True
        )

        self._highlight_style = highlight_style

    def __getitem__(self, key: int) -> LogData:
        return self._log_data[key]

    @property
    def line_count(self) -> int:
        """Return the amount of lines/Strips"""
        return len(self._log_lines)

    @property
    def log_data_count(self) -> int:
        return len(self._log_data)

    def line(self, line_idx: int) -> Strip:
        return self._log_lines[line_idx]

    def log_data_index_from_line_index(self, log_line_index: int) -> int:
        """Return the index of the logdata list based on a provided line_index."""

        log_data_index = self._log_lines_idx__log_data_idx[log_line_index]
        return log_data_index

    def update_log_data(self, log_data_idx: int) -> Size:
        log_data = self._log_data[log_data_idx]

        needs_re_indexing = log_data.update()
        if needs_re_indexing:
            self._re_index_from(log_data_idx)
        else:
            # just update the loglines corresponding to this log_data item
            start_idx = log_data.line_index
            for idx, line in enumerate(log_data.lines):
                self._log_lines[start_idx + idx] = line
        return Size(self._max_width, len(self._log_lines))

    def _re_index_from(self, log_data_idx: int) -> None:
        """Reindex the log lines.

        A logdata has changed its line-count. As a result all following logdata items and lines
        are not valid anymore."""
        log_data = self._log_data[log_data_idx]
        valid_log_lines = self._log_lines[: log_data.line_index]
        valid_log_lines_idx__log_data_idx = self._log_lines_idx__log_data_idx[
            : log_data.line_index
        ]

        for idx, log_data in enumerate(self._log_data[log_data_idx:]):
            log_data.line_index = len(valid_log_lines)
            valid_log_lines.extend(log_data._lines)

            valid_log_lines_idx__log_data_idx.extend(
                log_data.line_count * [idx + log_data_idx]
            )

        self._log_lines = valid_log_lines
        self._log_lines_idx__log_data_idx = valid_log_lines_idx__log_data_idx

    async def add_log_events(self, log_events: list[LogEvent]) -> Size:

        return self._update_lines(
            [
                LogData(
                    event,
                    self._console,
                    render_settings=self._render_options,
                    highligh_style=self._highlight_style,
                )
                for event in log_events
            ]
        )

    def _update_lines(self, log_datas: list[LogData]) -> Size:
        last_log_data_index = self.log_data_count
        for idx, log_data in enumerate(log_datas):
            log_data.line_index = len(self._log_lines)

            self._log_lines.extend(log_data.lines)
            self._log_lines_idx__log_data_idx.extend(
                log_data.line_count * [last_log_data_index + idx]
            )
            self._log_data.append(log_data)

            self._max_width = max(self._max_width, log_data.max_width)
        return Size(self._max_width, len(self._log_lines))


class LogOutput(ScrollView, can_focus=True):
    BINDINGS = [
        ("x", "expand", "Expand"),
        Binding("down", "cursor_down", "Cursor Down", show=False),
        Binding("up", "cursor_up", "Cursor Up", show=False),
    ]

    COMPONENT_CLASSES = {"logoutput--highlight"}

    DEFAULT_CSS = """
    LogOutput .logoutput--highlight {
        background: $secondary 20%;
    }
    """
    current_row: Reactive[int] = Reactive(-1)
    _line_cache: LineCache

    def __init__(self, reader: LogReader) -> None:
        super().__init__()
        self._reader = reader

    def on_mount(self, event: Any) -> None:
        self._rich_style = self.get_component_rich_style("logoutput--highlight")
        self._line_cache = LineCache(self.app.console, self._rich_style)
        asyncio.create_task(self._watch_log())

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

    def _scroll_cursor_into_view(self, animate: bool = False) -> None:
        """When the cursor is at a boundary of the LogOutput and moves out
        of view, this method handles scrolling to ensure it remains visible."""
        log_data = self._line_cache[self.current_row]

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

        if old_row > -1:
            self._line_cache[old_row].highlight = False
            self._line_cache.update_log_data(old_row)

        self._line_cache[new_row].highlight = True
        self._line_cache.update_log_data(new_row)
        self._scroll_cursor_into_view()

    def action_cursor_down(self) -> None:
        if self.current_row == self._line_cache.log_data_count - 1:
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
        self.current_row = self._line_cache.log_data_index_from_line_index(
            corresponding_line_index
        )
        # meta = event.style.meta
        # if "line" in meta:
        #     cursor_line = meta["line"]
        #     if meta.get("toggle", False):
        #         node = self.get_node_at_line(cursor_line)
        #         if node is not None:
        #             self._toggle_node(node)

        #     else:
        #         self.cursor_line = cursor_line
        #         await self.run_action("select_cursor")

    def render_line(self, y: int) -> Strip:
        scroll_x, scroll_y = self.scroll_offset

        strip = self._render_line(scroll_y + y, scroll_x, self.size.width)
        return strip

    def _render_line(self, y: int, scroll_x: int, width: int) -> Strip:
        if y >= self._line_cache.line_count:
            return Strip.blank(width)

        line = self._line_cache.line(y)
        return line.crop(scroll_x, scroll_x + width)

    async def add_item(self, log_events: list[LogEvent]) -> None:
        size = await self._line_cache.add_log_events(log_events)

        self.virtual_size = size

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
                await self.add_item(log_items)

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

    # def action_expand(self) -> None:
    #     if self.current_row is None:
    #         return

    #     _corresponding_data = self._log_cache[self.current_row]
    #     _corresponding_data.expanded = not _corresponding_data.expanded

    #     _corresponding_data.update(highlight_text="")

    #     self.data_table.rows[self.current_row].height = _corresponding_data.row_count

    #     self.data_table.update_cell(
    #         column_key=self._columns[0],
    #         row_key=self.current_row,
    #         value=_corresponding_data,
    #         update_width=True,
    #     )

    # def highlight_text(self, text: str) -> None:
    #     for row_key, data in self._log_cache.items():
    #         data.update(highlight_text=text)
    #         self.data_table.update_cell(
    #             column_key=self._columns[0], row_key=row_key, value=data
    #         )

    # def clear_log(self) -> None:
    #     self._log_cache = []
    #     self._log_lines = []
    #     self._max_width = 0
    #     self.virtual_size = Size(self._max_width, len(self._log_lines))


class LogViewer(Static, can_focus=True):
    BINDINGS = [
        ("ctrl+l", "start_logging", "Start logging"),
        ("ctrl+s", "stop_logging", "Stop logging"),
    ]

    def __init__(self, reader: LogReader) -> None:
        super().__init__()
        self.reader = reader
        self._log_control = LogControl(reader)
        self._log_output = LogOutput(self.reader)

    def compose(self) -> ComposeResult:
        yield self._log_control
        yield self._log_output

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "startlog":
            await self.action_start_logging()
        elif event.button.id == "stoplog":
            await self.action_stop_logging()
        elif event.button.id == "clearlog":
            self.action_clear_log()

    async def on_input_changed(self, event: Input.Changed) -> None:
        event.stop()
        if event.input.id == "search":
            self._log_output.highlight_text(event.value)

    async def _check_reading(self) -> bool:
        if self.reader.is_reading:
            _continue = await show_dialog(self.app, StopLoggingScreen())
            if _continue == DialogResult.YES:
                await self.reader.stop()
                return True
            else:
                return False
        return True

    async def start(self, pod: Pod) -> None:
        if await self._check_reading():
            self.reader.pod = pod.name
            self.reader.namespace = pod.namespace

            self.reader.start()
            # self.query_one("#log_output").focus()

    async def action_start_logging(self) -> None:
        if await self._check_reading():
            self.reader.start()
            # self.query_one("#log_output").focus()

    async def action_stop_logging(self) -> None:
        await self.reader.stop()

    def action_clear_log(self) -> None:
        self._log_output.clear_log()

    async def on_unmount(self) -> None:
        await self.reader.stop()
