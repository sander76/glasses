from typing import TypeVar

from textual.app import App, ComposeResult
from textual.message import Message, MessageTarget
from textual.widget import Widget
from textual.widgets import Footer

from glasses import dependencies
from glasses.log_viewer import LogViewer
from glasses.namespace_provider import BaseK8, Cluster, Commands, NameSpace, Pod
from glasses.nested_list_view import SlideView
from glasses.settings import LogCollectors, NameSpaceProvider, settings

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
        yield SlideView(
            dependencies.get_namespace_provider(settings.namespace_provider)
        )


class Viewer(App):
    """An app to view logging."""

    CSS_PATH = "layout.css"
    BINDINGS = [("d", "toggle_dark", "Toggle dark mode")]

    def __init__(self, demo_mode=False) -> None:
        super().__init__()
        if demo_mode:
            settings.logcollector = LogCollectors.DUMMY_LOG_COLLECTOR
            settings.namespace_provider = NameSpaceProvider.DUMMY_NAMESPACE_PROVIDER

        self._log_viewer = LogViewer(dependencies.get_log_reader(settings.logcollector))

    def compose(self) -> ComposeResult:
        yield SideBar()
        yield self._log_viewer
        yield Footer()

    def action_toggle_dark(self) -> None:
        self.dark = not self.dark

    async def on_slide_view_selected(self, event: SlideView.Selected) -> None:
        if event.id == Commands.VIEW_LOG:
            log_reader = self._log_viewer.reader

            pod = event.data
            assert isinstance(pod, Pod)
            podname = pod.name
            namespace = pod.namespace
            log_reader.pod = podname
            log_reader.namespace = namespace

            self._log_viewer.update_ui()


if __name__ == "__main__":

    app = Viewer(demo_mode=False)
    app.run()
