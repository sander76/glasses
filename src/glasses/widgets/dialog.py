from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Grid
from textual.screen import Screen
from textual.widgets import Button, Static


class QuitScreen(Screen):
    BINDINGS = [
        Binding("y", "yes", "YES", show=False),
        Binding("n", "no", "No", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield Grid(
            Static("Are you sure you want to quit?", id="question"),
            Button("[Y]es", variant="error", id="quit"),
            Button("[N]o", variant="primary", id="cancel"),
            id="dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "quit":
            self.action_yes()
        else:
            self.action_no()

    def action_no(self) -> None:
        self.app.pop_screen()

    def action_yes(self) -> None:
        self.app.exit()
