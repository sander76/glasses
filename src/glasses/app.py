import argparse
import os
from pathlib import Path
from typing import Sequence, TypeVar

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import ContentSwitcher, Footer

from glasses import dependencies
from glasses.logger import setup_logging
from glasses.namespace_provider import Cluster, NameSpace
from glasses.settings import LogCollectors, NameSpaceProvider
from glasses.widgets.dialog import QuestionDialog
from glasses.widgets.log_viewer import LogViewer
from glasses.widgets.nested_list_view import NestedListView

Provider = TypeVar("Provider", NameSpace, Cluster)

# TODO: Logviewer: Add checkbox to enable/disable autoscroll.
# TODO: When starting new logger, ask whether to stop the previous one first.
# TODO: Remove first layer from app as it is not needed anymore. (modal screens are displayed in another, more direct way.)


class Viewer(App):
    """An app to view logging."""

    CSS_PATH = "app.tcss"
    BINDINGS = [
        Binding("d", "toggle_dark", "Toggle dark mode", show=False),
        Binding("n", "select_namespaces", "namespaces"),
    ]

    def compose(self) -> ComposeResult:
        with ContentSwitcher(initial="namespaces"):
            yield NestedListView(id="namespaces")
            yield LogViewer(dependencies.get_log_reader())
        yield Footer()  # contains the bindings.

    def action_toggle_dark(self) -> None:
        self.dark = not self.dark

    async def on_nested_list_view_selected(
        self, event: NestedListView.Selected
    ) -> None:
        self.query_one(ContentSwitcher).current = "log-viewer"
        viewer = self.query_one("LogViewer", expect_type=LogViewer)

        viewer.reader.pod = event.data.name
        viewer.reader.namespace = event.data.namespace
        await viewer.start()

    async def action_quit(self) -> None:
        def _exit(answer: bool) -> None:
            if answer:
                self.app.exit()

        self.push_screen(QuestionDialog("Quit?"), _exit)

    async def action_select_namespaces(self) -> None:
        self.query_one(ContentSwitcher).current = "namespaces"


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


if __name__ == "__main__":
    run()
    app = Viewer()
    app.run()
