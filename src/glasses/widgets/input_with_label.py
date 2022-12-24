from textual.containers import Horizontal
from textual.widgets import Input, Label


class InputWithLabel(Horizontal):
    CSS_PATH = "input_with_label.css"

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

    def compose(self):
        yield Label(self.label)
        yield Input(
            value=self.initial_input_value,
            placeholder=self._placeholder,
        )
