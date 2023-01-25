import asyncio
from enum import Enum, auto

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, Input, Label, ListItem, ListView, Static

from glasses.log_provider import LogEvent, LogReader


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

    def is_reading_changed(self, state):
        self.toggle_class("not_logging")
        self.toggle_class("logging")
        if state:
            self.state = State.LOGGING
        else:
            self.state = State.IDLE

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
        self.query_one("#namespace").value = self._reader.namespace

    def _update_pod(self, _: str) -> None:
        self.query_one("#pod_name").value = self._reader.pod

    def compose(self) -> ComposeResult:
        yield Horizontal(
            Label("namespace: "),
            Input(self._reader.namespace, id="namespace", classes="small_input"),
        )
        yield Horizontal(
            Label("pod name: "),
            Input(self._reader.pod, id="pod_name", classes="small_input"),
        )
        yield Horizontal(
            Button("log", id="startlog"),
            Button("stop", id="stoplog"),
            Button("clear log", id="clearlog"),
        )
        yield self._logging_state

    # async def on_input_changed(self, event: Input.Changed):
    #     if event.input.id == "namespace":
    #         self._reader.namespace = event.input.value
    #     elif event.input.id == "pod_name":
    #         self._reader.pod = event.input.value


class LogItem(ListItem):
    DEFAULT_CSS = """
    LogItem {
        width: auto;
        background: $background;
    }
    """

    def __init__(self, log_item: LogEvent, *args, **kwargs) -> None:

        super().__init__(Label(log_item.parsed), *args, **kwargs)
        self._log_item = log_item
        self.expanded: bool = False
        self._expand_data: Label | None = None

    def toggle(self, expand: bool):
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

    def action_expand(self):
        item = self.list_view.highlighted_child
        item.toggle(not item.expanded)

    def compose(self) -> ComposeResult:
        yield self._list_view

    def on_mount(self, event):
        asyncio.create_task(self._watch_log())

    async def _watch_log(self):
        async for line in self._reader.read():
            log_item = LogItem(line)
            self._list_view.append(log_item)

    def clear_log(self):
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

    async def on_button_pressed(self, event: Button.Pressed):

        if event.button.id == "startlog":
            self.action_start_logging()
        elif event.button.id == "stoplog":
            self.action_stop_logging()
        elif event.button.id == "clearlog":
            self.action_clear_log()

    def action_start_logging(self):
        self.reader.start()

    def action_stop_logging(self):
        self.reader.stop()

    def action_clear_log(self):
        self._log_output.clear_log()
