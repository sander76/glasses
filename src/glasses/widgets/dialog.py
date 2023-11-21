from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label


class QuestionDialog(ModalScreen[bool]):
    DEFAULT_CLASSES = "dialog"

    BINDINGS = [
        Binding("y", "yes", "YES", show=False),
        Binding("n", "no", "No", show=False),
    ]

    def __init__(self, question: str) -> None:
        self._question = question
        super().__init__()

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label(self._question, id="question")
            with Container():
                yield Button("[Y]es", variant="error", id="yes")
                yield Button("[N]o", variant="primary", id="no")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "yes":
            self.dismiss(True)
        else:
            self.dismiss(False)


class IntegerDialog(ModalScreen[int | None]):
    DEFAULT_CLASSES = "dialog"
    BINDINGS = [
        Binding("esc", "cancel", "cancel", show=False),
    ]

    def __init__(self, label: str, default_value: int) -> None:
        self._label = label
        self._default_value = str(default_value)
        super().__init__()

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label(self._label, id="question")
            yield Input(self._default_value)
            with Container():
                yield Button("Cancel [ESC]", variant="error", id="cancel")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        _value = int(event.value)
        self.dismiss(_value)

    def on_button_pressed(self, _: Button.Pressed) -> None:
        self.dismiss(None)
