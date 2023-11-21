from textual.app import ComposeResult
from textual.binding import Binding
from textual.widget import Widget
from textual.widgets import Label


class ModalView(Widget):
    DEFAULT_CSS = """
    ModalView {
        align: center middle;
        height: 100%;
        width: 100%;
        background: red;
    }
    """

    def __init__(self) -> None:
        super().__init__(id="modal_view")

    def compose(self) -> ComposeResult:
        yield HelpView([])


class HelpView(Widget, can_focus=True):
    DEFAULT_CSS = """
    HelpView {
        background: black;
        layer: modal;
        height: 100%;
        width: 100%;
        overflow-y: auto;
    }
    """

    BINDINGS = [
        ("c", "close_view", "close view"),
    ]

    def __init__(self, bindings: list[tuple[str, str, str] | Binding]) -> None:
        super().__init__()
        # self._binding = bindings

        self._short_cut_keys: list[str] = []
        for binding in bindings:
            if isinstance(binding, Binding):
                self._short_cut_keys.append(f"{binding.key:<40}{binding.description}")
            else:
                self._short_cut_keys.append(f"{binding[0]:<40}{binding[2]}")

    def compose(self) -> ComposeResult:
        yield from (Label(shortcut) for shortcut in self._short_cut_keys)

    def on_mount(self) -> None:
        self.focus()

    def action_close_view(self) -> None:
        self.remove()
