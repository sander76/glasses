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
        yield Button("<", id="previous")
        yield Button(">", id="next")

    @cached_property
    def count_label(self) -> Label:
        return self.query_one("#result_count", expect_type=Label)

    @cached_property
    def _search_input(self) -> Input:
        return self.query_one("#search_input", expect_type=Input)

    def _watch_search_count(self, value: int) -> None:
        self.count_label.update(str(value))

    def on_show(self) -> None:
        self._search_input.focus()
