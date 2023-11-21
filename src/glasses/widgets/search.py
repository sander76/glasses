from functools import cached_property

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label


class Search(Horizontal):
    DEFAULT_CLASSES = "search"

    search_count = reactive(0)

    def compose(self) -> ComposeResult:
        yield Label("Search")
        yield Input("", id="search_input")
        yield Label(id="result_count")
        yield Button(">", id="next")
        yield Button("<", id="previous")

    @cached_property
    def count_label(self) -> Label:
        return self.query_one("#result_count", expect_type=Label)

    def _watch_search_count(self, value: int) -> None:
        self.count_label.update(str(value))
