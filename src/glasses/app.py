import argparse
import os
from pathlib import Path
from typing import Sequence, TypeVar

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.reactive import var
from textual.widget import Widget
from textual.widgets import Footer

from glasses import dependencies
from glasses.logger import setup_logging
from glasses.namespace_provider import Cluster, Commands, NameSpace, Pod
from glasses.settings import LogCollectors, NameSpaceProvider
from glasses.widgets.dialog import QuitScreen
from glasses.widgets.log_viewer import LogViewer
from glasses.widgets.nested_list_view import NestedListView

Provider = TypeVar("Provider", NameSpace, Cluster)

# TODO: Logviewer: Add checkbox to enable/disable autoscroll.
# TODO: When starting new logger, ask whether to stop the previous one first.
# TODO: Remove first layer from app as it is not needed anymore. (modal screens are displayed in another, more direct way.)


class SideBar(Widget):
    """Sidebar view."""

    def compose(self) -> ComposeResult:
        yield NestedListView(dependencies.get_namespace_provider())


class Viewer(App):
    """An app to view logging."""

    show_sidebar = var(True)

    CSS_PATH = "app.css"
    BINDINGS = [
        Binding("d", "toggle_dark", "Toggle dark mode", show=False),
        Binding("ctrl+b", "toggle_sidebar", "Toggle sidebar"),
    ]

    def watch_show_sidebar(self, show_sidebar: bool) -> None:
        """Called when show_sidebar var value has changed."""
        self.set_class(show_sidebar, "-show-sidebar")
        if not self.show_sidebar:
            viewer = self.query_one("LogViewer", expect_type=LogViewer)
            viewer.log_output.focus()

    def compose(self) -> ComposeResult:
        yield SideBar(id="sidebar")
        yield LogViewer(dependencies.get_log_reader())
        yield Footer()

    def action_toggle_dark(self) -> None:
        self.dark = not self.dark

    async def on_nested_list_view_command(self, event: NestedListView.Command) -> None:
        if event.id == Commands.VIEW_LOG:

            pod = event.data
            assert isinstance(pod, Pod)
            viewer = self.query_one("LogViewer", expect_type=LogViewer)
            await viewer.start(pod)

    def action_toggle_sidebar(self) -> None:
        self.show_sidebar = not self.show_sidebar

    async def action_quit(self) -> None:
        self.push_screen(QuitScreen())


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--demo_mode",
        help="run this in demo mode.",
        action=argparse.BooleanOptionalAction,
        default=False,
    )

    args = parser.parse_args(argv)
    return args


app = Viewer()


def run(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    demo_mode = args.demo_mode

    if demo_mode:
        os.environ["logcollector"] = LogCollectors.DUMMY_LOG_COLLECTOR.value
        os.environ[
            "namespace_provider"
        ] = NameSpaceProvider.DUMMY_NAMESPACE_PROVIDER.value

    glasses_folder = Path.home() / ".config" / "glasses"
    glasses_folder.mkdir(exist_ok=True, parents=True)

    setup_logging(glasses_folder)

    app = Viewer()

    app.run()


if __name__ == "__main__":
    run()
