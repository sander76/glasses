import asyncio
from enum import Enum, auto
from typing import Any

from rich.console import RenderableType
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, Input, Label, ListItem, ListView, Static

from glasses.controllers.log_provider import LogEvent, LogReader


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


class LogItem(ListItem):
    DEFAULT_CSS = """
    LogItem {
        width: auto;
        background: $background;
    }
    """
    highlight_text = reactive("")

    def __init__(self, log_item: LogEvent) -> None:
        super().__init__()
        # super().__init__(Label(log_item.parsed))
        self._log_item = log_item
        self.expanded: bool = False
        self._expand_data: Label | None = None

    def render(self) -> RenderableType:
        # create a copy of the original logline to add highlighting to it.
        # each time `highlight_text` property has changed, the old highlight is
        # removed by the copy and re-added during this call.
        new_line = self._log_item.parsed.copy()
        new_line.highlight_regex(self.highlight_text, "black on yellow")

        return new_line

    def toggle(self, expand: bool) -> None:
        if expand:
            if self._expand_data is None:
                self._expand_data = Label(self._log_item.raw)
                self.mount(self._expand_data)

            self._expand_data.visible = True
        else:
            # setting visibility to False does hide the expanded
            # data, but it does not resize the list item to remove the empty
            # space. This seems like a bug.
            if self._expand_data:
                self._expand_data.visible = False

        self.expanded = not self.expanded


class LogOutput(Vertical):
    BINDINGS = [("x", "expand", "Expand")]

    DEFAULT_CSS = """
    LogOutput {
        width: 100%;
        height: 100%;
    }
    LogOutput ListView {
        overflow-x: scroll;
        background: $background;
    }
    """

    def __init__(self, reader: LogReader) -> None:
        super().__init__()
        self._reader = reader
        self._list_view = ListView()
        self._reader.subscribe("highlight_text", self.highlight_text)

    def action_expand(self) -> None:
        item = self._list_view.highlighted_child
        assert isinstance(item, LogItem)
        item.toggle(not item.expanded)

    def compose(self) -> ComposeResult:
        yield self._list_view

    def on_mount(self, event: Any) -> None:
        asyncio.create_task(self._watch_log())

    async def _watch_log(self) -> None:
        async for line in self._reader.read():
            log_item = LogItem(line)
            self._list_view.append(log_item)

    def highlight_text(self, value: str) -> None:
        for item in self._list_view.children:

            item.highlight_text = value  # type: ignore

    def clear_log(self) -> None:
        self._list_view.clear()


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
            self.action_start_logging()
        elif event.button.id == "stoplog":
            await self.action_stop_logging()
        elif event.button.id == "clearlog":
            self.action_clear_log()

    def action_start_logging(self) -> None:
        self.reader.start()

    async def action_stop_logging(self) -> None:
        await self.reader.stop()

    def action_clear_log(self) -> None:
        self._log_output.clear_log()

    async def on_unmount(self) -> None:
        await self.reader.stop()
