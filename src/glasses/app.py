import argparse
from typing import Sequence, TypeVar

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widget import Widget
from textual.widgets import Footer

from glasses import dependencies
from glasses.namespace_provider import Cluster, Commands, NameSpace, Pod
from glasses.settings import LogCollectors, NameSpaceProvider, settings
from glasses.widgets.log_viewer import LogViewer
from glasses.widgets.modal import HelpView
from glasses.widgets.nested_list_view import NestedListView

ID_BTN_REFRESH = "refresh"

Provider = TypeVar("Provider", NameSpace, Cluster)


class SideBar(Widget):
    """Namespaces view."""

    def compose(self) -> ComposeResult:
        yield NestedListView(
            dependencies.get_namespace_provider(settings.namespace_provider)
        )


class TheApp(Widget):
    BINDINGS = [
        Binding("ctrl+right", "width(1)", "Increase Navigator", show=False),
        Binding("ctrl+left", "width(-1)", "Decrease Navigator", show=False),
    ]

    sidebar_width = 60
    sidebar_min_width = 10

    def __init__(self) -> None:
        super().__init__()

        self._log_viewer = LogViewer(dependencies.get_log_reader(settings.logcollector))
        self._sidebar = SideBar()
        self._sidebar.styles.width = self.sidebar_width

    def compose(self):
        yield self._sidebar
        yield self._log_viewer
        yield Footer()

    async def on_slide_view_command(self, event: NestedListView.Command) -> None:
        if event.id == Commands.VIEW_LOG:
            log_reader = self._log_viewer.reader

            pod = event.data
            assert isinstance(pod, Pod)
            podname = pod.name
            namespace = pod.namespace

            log_reader.pod = podname
            log_reader.namespace = namespace

            start_button = self.query_one("#startlog")
            start_button.focus()

    def action_width(self, by_val: int) -> None:
        if self.sidebar_width > self.sidebar_min_width or by_val > 0:
            self.sidebar_width += by_val
            self._sidebar.styles.width = self.sidebar_width


class Viewer(App):
    """An app to view logging."""

    CSS_PATH = "app.css"
    BINDINGS = [
        Binding("d", "toggle_dark", "Toggle dark mode", show=False),
        Binding("ctrl+right", "width(1)", "Increase Navigator", show=False),
        Binding("ctrl+left", "width(-1)", "Decrease Navigator", show=False),
        ("h", "view_help", "help"),
    ]

    def compose(self) -> ComposeResult:
        yield TheApp()

    def action_toggle_dark(self) -> None:
        self.dark = not self.dark

    def action_view_help(self) -> None:
        self.mount(HelpView(bindings=self.BINDINGS))


def _parse_args(argv: Sequence[str] | None = None):
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
        settings.logcollector = LogCollectors.DUMMY_LOG_COLLECTOR
        settings.namespace_provider = NameSpaceProvider.DUMMY_NAMESPACE_PROVIDER

    app = Viewer()

    app.run()


if __name__ == "__main__":
    run()
