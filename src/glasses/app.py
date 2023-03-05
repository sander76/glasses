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
from glasses.widgets.dialog import (
    DialogResult,
    QuitScreen,
    StopLoggingScreen,
    show_dialog,
)
from glasses.widgets.log_viewer import LogViewer
from glasses.widgets.modal import HelpView
from glasses.widgets.nested_list_view import NestedListView

ID_BTN_REFRESH = "refresh"

Provider = TypeVar("Provider", NameSpace, Cluster)

# TODO: change background color of selected logitem
# TODO: Logviewer: Add checkbox to enable/disable autoscroll.
# TODO: When starting new logger, ask whether to stop the previous one first.
# TODO: Remove first layer from app as it is not needed anymore. (modal screens are displayed in another, more direct way.)


class SideBar(Widget):
    """Namespaces view."""

    def compose(self) -> ComposeResult:
        yield NestedListView(dependencies.get_namespace_provider())


class TheApp(Widget):
    BINDINGS = [
        Binding("ctrl+b", "toggle_sidebar", "Toggle sidebar"),
    ]

    show_sidebar = var(True)

    def watch_show_sidebar(self, show_sidebar: bool) -> None:
        """Called when show_sidebar var value has changed."""
        self.set_class(show_sidebar, "-show-sidebar")

    def __init__(self) -> None:
        super().__init__()
        self._log_viewer = LogViewer(dependencies.get_log_reader())
        self._sidebar = SideBar(id="sidebar")

    def compose(self) -> ComposeResult:
        yield self._sidebar
        yield self._log_viewer
        yield Footer()

    async def on_nested_list_view_command(self, event: NestedListView.Command) -> None:
        if event.id == Commands.VIEW_LOG:
            log_reader = dependencies.get_log_reader()

            pod = event.data
            assert isinstance(pod, Pod)

            if log_reader.is_reading:
                _continue = await show_dialog(self.app, StopLoggingScreen())
                if _continue == DialogResult.YES:
                    await log_reader.stop()
                else:
                    return

            log_reader.pod = pod.name
            log_reader.namespace = pod.namespace

            start_button = self.query_one("#startlog")
            start_button.focus()

    def action_toggle_sidebar(self) -> None:
        self.show_sidebar = not self.show_sidebar


class Viewer(App):
    """An app to view logging."""

    CSS_PATH = "app.css"
    BINDINGS = [
        Binding("d", "toggle_dark", "Toggle dark mode", show=False),
        ("h", "view_help", "help"),
    ]

    def compose(self) -> ComposeResult:
        yield TheApp()

    def action_toggle_dark(self) -> None:
        self.dark = not self.dark

    def action_view_help(self) -> None:
        self.mount(HelpView(bindings=self.BINDINGS))

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
