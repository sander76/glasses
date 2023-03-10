import asyncio
from asyncio import Event
from enum import Enum
from typing import Awaitable

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import Button, Static


class DialogResult(Enum):
    YES = "YES"
    NO = "NO"


class QuestionDialog(Screen):

    DEFAULT_CLASSES = "dialog"
    BINDINGS = [
        Binding("y", "yes", "YES", show=False),
        Binding("n", "no", "No", show=False),
    ]

    def __init__(
        self, name: str | None = None, id: str | None = None, classes: str | None = None
    ) -> None:
        self._result: DialogResult | None = None
        self._event = Event()
        super().__init__(name, id, classes)

    async def result(self) -> DialogResult | None:
        await self._event.wait()
        return self._result

    def compose(self) -> ComposeResult:
        yield Static(self._question, id="question")
        yield Horizontal(
            Button("[Y]es", variant="error", id="quit"),
            Button("[N]o", variant="primary", id="cancel"),
            id="buttons",
        )

    @property
    def _question(self) -> str:
        return "Unknown question"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "quit":
            self.action_yes()
        else:
            self.action_no()
        self._event.set()

    def action_no(self) -> None:
        self.app.pop_screen()

    def action_yes(self) -> None:
        raise NotImplementedError()


def show_dialog(app: App, dialog: QuestionDialog) -> Awaitable[None | DialogResult]:
    app.push_screen(dialog)
    loop = asyncio.get_running_loop()
    return loop.create_task(dialog.result())
    # return asyncio.create_task(dialog.result())


class QuitScreen(QuestionDialog):
    @property
    def _question(self) -> str:
        return "Are you sure you want to quit?"

    def action_yes(self) -> None:
        self.app.exit()


class StopLoggingScreen(QuestionDialog):
    @property
    def _question(self) -> str:
        return "Another log action is active. Need to stop it first. Stop it?"

    def action_yes(self) -> None:
        self._result = DialogResult.YES
        self.app.pop_screen()
