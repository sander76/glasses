from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Input, Label


class InputWithLabel(Horizontal):
    DEFAULT_CSS = """
    InputWithLabel {
        height: auto;
        width: 100%;
    }
    #label {
        width: 30%;
        border: none;
    }
    #input {
        width: 60%;
        height: 1;
        border: none;
        background: blue;
    }"""

    def __init__(
        self,
        *,
        id: str,
        label_text: str,
        initial_input_value: str | None = None,
        placeholder: str = ""
    ) -> None:
        super().__init__(id=id)
        self.label = label_text
        self.initial_input_value = initial_input_value
        self._placeholder = placeholder
        self._input = Input(
            value=self.initial_input_value, placeholder=self._placeholder, id="input"
        )

    def compose(self) -> ComposeResult:
        yield Label(self.label, id="label")
        yield self._input

    @property
    def value(self) -> str:
        return self._input.value
