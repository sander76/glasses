import asyncio

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Button, Footer, Input, Label, ListItem, ListView, Static

from glasses.dependencies import get_log_reader
from glasses.log_provider import LogEvent
from glasses.settings import settings
from glasses.widgets.input_with_label import InputWithLabel


class LogControl(Vertical):
    DEFAULT_CSS = """
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

    def __init__(self) -> None:
        super().__init__()
        self._reader = get_log_reader(settings.logcollector)

    # should this be done with reactive properties ?
    # I am not sure how to do reactive in combination with some kind
    # of MVC pattern. So for now I do a manual update of the UI when an
    # external change of the model is done.
    def update_ui(self):
        self.query_one("#namespace").value = self._reader.namespace
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
        yield Button("log", id="startlog")
        yield Button("stop", id="stoplog")

    async def on_button_pressed(self, event: Button.Pressed):
        reader = get_log_reader(settings.logcollector)

        if event.button.id == "startlog":
            reader.start(self._reader.namespace, pod=self._reader.pod)
        elif event.button.id == "stoplog":
            reader.stop()

    async def on_input_changed(self, event: Input.Changed):
        if event.input.id == "namespace":
            self._reader.namespace = event.input.value
        elif event.input.id == "pod_name":
            self._reader.pod = event.input.value


class LogItem(ListItem):
    def __init__(self, log_item: LogEvent, *args, **kwargs) -> None:

        super().__init__(Vertical(Label(log_item.parsed)), *args, **kwargs)
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
            self._expand_data.visible = False

        self.expanded = not self.expanded


class LogOutput(Vertical):
    BINDINGS = [("x", "expand", "Expand")]

    def action_expand(self):
        item = self.list_view.highlighted_child
        item.toggle(not item.expanded)

    def compose(self) -> ComposeResult:
        self.list_view = ListView()
        yield self.list_view

    def on_mount(self, event):
        asyncio.create_task(self._watch_log())

    async def _watch_log(self):
        reader = get_log_reader(settings.logcollector)
        async for line in reader.read():
            self.list_view.append(LogItem(line))


class LogViewer(Static):
    def __init__(self) -> None:
        super().__init__()
        self._log_control = LogControl()

    def compose(self) -> ComposeResult:
        yield self._log_control
        yield LogOutput()

    def update_ui(self):
        self._log_control.update_ui()


class LogViewer(Static):
    def compose(self) -> ComposeResult:
        yield LogControl(id="logcontrol")
        yield LogOutput()


class Viewer(App):
    """An app to view logging."""

    CSS_PATH = "log_viewer.css"
    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
    ]

    def compose(self) -> ComposeResult:
        yield LogViewer()
        yield Footer()

    def action_toggle_dark(self) -> None:
        self.dark = not self.dark


if __name__ == "__main__":
    app = Viewer()
    app.run()
