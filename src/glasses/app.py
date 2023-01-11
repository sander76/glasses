import argparse
from typing import TypeVar

from textual.app import App, ComposeResult
from textual.widget import Widget
from textual.widgets import Footer

from glasses import dependencies
from glasses.log_viewer import LogViewer
from glasses.namespace_provider import Cluster, Commands, NameSpace, Pod
from glasses.nested_list_view import SlideView
from glasses.settings import LogCollectors, NameSpaceProvider, settings

ID_BTN_REFRESH = "refresh"

Provider = TypeVar("Provider", NameSpace, Cluster)


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

    # async def on_slide_view_command(self, event: SlideView.Command) -> None:
    #     pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--demo_mode",
        help="run this in demo mode.",
        action=argparse.BooleanOptionalAction,
        default=False,
    )

    args = parser.parse_args()
    demo_mode = args.demo_mode
    app = Viewer(demo_mode=demo_mode)
    app.run()
