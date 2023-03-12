import asyncio
from enum import Enum, auto
from typing import Any
from uuid import uuid4

from rich.json import JSON
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, DataTable, Input, Label, Static
from textual.widgets.data_table import ColumnKey, RowKey

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


class LogData(Text):
    def __init__(self, log_event: LogEvent) -> None:
        self.log_event = log_event
        self.expanded: bool = False
        super().__init__()

    def update(self, highlight_text: str | None = None) -> int:
        """Update the output of the logdata

        Returns:
            the amount of highlight_text matches.
        """
        new_line = self.log_event.parsed.copy()
        if self.expanded:

            new_line.append("\n\n")
            raw = self.log_event.raw
            if isinstance(raw, JSON):
                raw = raw.text
            new_line.append(raw)

        matches = 0
        if highlight_text is not None:
            matches = new_line.highlight_regex(highlight_text, "black on yellow")

        self.plain = new_line.plain
        self.spans = new_line.spans

        return matches

    @property
    def row_count(self) -> int:
        return len(self.plain.split("\n"))


class LogOutput(Widget):
    BINDINGS = [("x", "expand", "Expand")]
    DEFAULT_CSS = """
    #log_output >  .datatable--cursor {
        background: $secondary-background-darken-1 ;
        color: $text;
    }
    """

    def __init__(self, reader: LogReader) -> None:
        super().__init__()
        self._reader = reader
        self.data_table = DataTable[LogData](id="log_output")
        self.data_table.cursor_type = "row"
        self._current_row_key: RowKey | None = None
        self._log_cache: dict[RowKey, LogData] = {}
        self._columns: list[ColumnKey] = []

    def on_mount(self, event: Any) -> None:
        self._columns = self.data_table.add_columns("log output")
        self.data_table.show_header = False  # unable to set this during datatable init.
        asyncio.create_task(self._watch_log())

    def compose(self) -> ComposeResult:
        yield self.data_table

    async def add_item(self, log_event: LogEvent) -> None:
        log_data = LogData(log_event)
        log_key = str(uuid4())

        log_data.update()

        row_key = self.data_table.add_row(
            log_data, key=log_key, height=log_data.row_count
        )
        self._log_cache[row_key] = log_data

    async def _watch_log(self) -> None:
        async for log_event in self._reader.read():
            await self.add_item(log_event)

    def on_data_table_row_selected(self, message: DataTable.RowSelected) -> None:
        message.stop()
        self.current_row = message.row_key

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        event.stop()
        self.current_row = event.row_key

    def action_expand(self) -> None:
        if self.current_row is None:
            return

        _corresponding_data = self._log_cache[self.current_row]
        _corresponding_data.expanded = not _corresponding_data.expanded

        _corresponding_data.update(highlight_text="")

        self.data_table.rows[self.current_row].height = _corresponding_data.row_count

        self.data_table.update_cell(
            column_key=self._columns[0],
            row_key=self.current_row,
            value=_corresponding_data,
            update_width=True,
        )

    def highlight_text(self, text: str) -> None:
        for row_key, data in self._log_cache.items():
            data.update(highlight_text=text)
            self.data_table.update_cell(
                column_key=self._columns[0], row_key=row_key, value=data
            )

    def clear_log(self) -> None:
        self._log_cache = {}
        self.data_table.clear()


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
            self.query_one("#log_output").focus()

    async def action_start_logging(self) -> None:
        if await self._check_reading():
            self.reader.start()
            self.query_one("#log_output").focus()

    async def action_stop_logging(self) -> None:
        await self.reader.stop()

    def action_clear_log(self) -> None:
        self._log_output.clear_log()

    async def on_unmount(self) -> None:
        await self.reader.stop()
