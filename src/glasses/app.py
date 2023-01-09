from typing import Awaitable, Callable, Generic, Protocol, TypeVar

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message, MessageTarget
from textual.widget import Widget
from textual.widgets import Button, Footer, Label, ListItem, ListView, Static, Tree

from glasses.dependencies import get_k8_client, get_log_reader
from glasses.log_viewer import LogViewer
from glasses.namespace_provider import BaseK8, Cluster, Commands, NameSpace, Pod
from glasses.nested_list_view import SlideView
from glasses.settings import settings
from glasses.widgets.input_with_label import InputWithLabel
from typing import TypeVar, Generic

ID_BTN_REFRESH = "refresh"

Provider = TypeVar("Provider", NameSpace, Cluster)


class ChangeView(Message):
    """A message."""

    def __init__(self, sender: MessageTarget, new_data: BaseK8) -> None:
        super().__init__(sender)

        self.new_data = new_data


class SideBar(Widget):
    """Namespaces view."""

    def compose(self) -> ComposeResult:
        yield SlideView()


class Viewer(App):
    """An app to view logging."""

    CSS_PATH = "layout.css"
    BINDINGS = [("d", "toggle_dark", "Toggle dark mode")]

    def compose(self) -> ComposeResult:
        yield SideBar()
        yield LogViewer()
        yield Footer()

    def action_toggle_dark(self) -> None:
        self.dark = not self.dark

    async def on_slide_view_selected(self, event: SlideView.Selected) -> None:
        if event.id == Commands.VIEW_LOG:
            log_data = get_log_reader(settings.logcollector)

            pod: Pod = event.data
            podname = pod.name
            namespace = pod.namespace
            log_data.pod = podname
            log_data.namespace = namespace
            log_viewer = self.query_one("LogViewer")
            log_viewer.update_ui()


if __name__ == "__main__":
    app = Viewer()
    app.run()
