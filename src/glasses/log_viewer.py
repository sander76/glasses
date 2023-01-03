import asyncio

from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Button, Footer, Label, ListItem, ListView, Static

from glasses.dependencies import get_log_reader
from glasses.log_provider import LogEvent
from glasses.settings import settings
from glasses.widgets.input_with_label import InputWithLabel


class LogControl(Static):
    def compose(self) -> ComposeResult:
        yield InputWithLabel(id="namespace", label_text="namespace")
        yield InputWithLabel(id="resource_name", label_text="resource name")
        yield Button("log", id="startlog")
        yield Button("stop", id="stoplog")

    async def on_button_pressed(self, event: Button.Pressed):
        reader = get_log_reader(settings.logcollector)

        if event.button.id == "startlog":
            reader.start()
        elif event.button.id == "stoplog":
            reader.stop()


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


class LogOutput(Static):
    BINDINGS = [("x", "expand", "Expand")]

    def action_expand(self):
        item = self.list_view.highlighted_child
        item.toggle(not item.expanded)
        self.list_view

    def compose(self) -> ComposeResult:
        self.list_view = ListView()
        yield self.list_view

    def on_mount(self, event):
        asyncio.create_task(self._watch_log())

    async def _watch_log(self):
        reader = get_log_reader(settings.logcollector)
        async for line in reader.read():
            self.list_view.append(LogItem(line))
            # self.refresh()


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
