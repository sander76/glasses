from tkinter import Widget
from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import (
    Button,
    ListView,
    ListItem,
    Static,
    Footer,
    Label,
)
from textual.message import Message, MessageTarget
from glasses.log_viewer import LogViewer
from glasses.dependencies import get_cluster
from glasses.namespace_provider import BaseK8, NameSpace, Cluster, Pod
from glasses.widgets.input_with_label import InputWithLabel
from typing import TypeVar, Generic

ID_BTN_REFRESH = "refresh"

Provider = TypeVar("Provider", bound=BaseK8)


class LItem(ListItem):
    def __init__(
        self,
        data,
        *children: Widget,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(*children, name=name, id=id, classes=classes)
        self.data = data


class BaseK8View(Vertical, Generic[Provider]):
    def __init__(self, provider: Provider) -> None:
        super().__init__()
        self.provider = provider
        self.listview = ListView()

    def compose(self) -> ComposeResult:
        yield self.listview

    async def on_mount(self):
        await self.populate()

    async def update_view(self):
        await self.provider.refresh()
        await self.populate()

    async def populate(self):
        await self.listview.clear()
        for namespace in self.provider.items.values():
            self.listview.append(
                LItem(namespace, Label(namespace.name), id=namespace.name)
            )


class PodView(BaseK8View[Pod]):
    """A pod view.

    Contains functionality provided by a pod.
    """

    def compose(self):
        yield Label(f"POD: {self.provider.name}")
        yield from super().compose()


class NameSpaceView(BaseK8View[NameSpace]):
    """A View containing resources in a namespace.

    Like a pod or a chart.
    """

    def compose(self):
        yield Label(f"namespace: {self.provider.name}")
        yield from super().compose()


class ClusterView(BaseK8View[Cluster]):
    """A list of available namespaces."""

    def compose(self):
        yield Label("Cluster view")
        yield from super().compose()

    async def action_refresh(self):
        await self.update_view()

    # async def on_list_view_selected(self, event: ListView.Selected):
    #     namespace = event.item.id
    #     assert namespace is not None
    #     await self.emit(self.Selected(self, item=self._provider.namespaces[namespace]))

    # def enter(self):
    #     return ResourcesView()

    # class Selected(Message):
    #     def __init__(self, sender: MessageTarget, item) -> None:
    #         super().__init__(sender)
    #         self.item = item
    #         self.new_view = ResourcesView


class SideBar(Static):
    """Namespaces view."""

    BINDINGS = [("r", "update_view", "Update view"), ("b", "back", "back")]

    def __init__(self) -> None:
        super().__init__()
        self.provider = get_cluster()
        self._current_view: BaseK8View = ClusterView(provider=get_cluster())
        # self._tree: list[BaseK8View] = [ClusterView(provider=get_name_space_provider())]

    def compose(self) -> ComposeResult:
        yield Button("refresh", id=ID_BTN_REFRESH)
        yield self._current_view

    async def on_list_view_selected(self, event: ListView.Selected):
        data = event.item.data
        await self._new_view(data)

    def _view_from_data(self, data: BaseK8) -> BaseK8View:
        match data:
            case Pod():
                print("handle pod")
            case NameSpace():
                return NameSpaceView(provider=data)
            case Cluster():
                return ClusterView(provider=data)
            case _:
                raise ValueError("wrong data")

    async def _new_view(self, data: BaseK8):
        """Create a new view based on provided data."""
        new_view = self._view_from_data(data)
        await self._current_view.remove()
        self._current_view = new_view
        await self.mount(new_view)

    async def action_back(self):
        await self._previous_view()

    async def _previous_view(self):
        new_view = self._current_view.provider.parent
        await self._new_view(new_view)

    async def action_update_view(self):
        await self.update_view()

    async def update_view(self):
        await self._current_view.update_view()

    # async def action_refresh_view(self):
    #     selected = self.namespaces.cursor_node
    #     data = selected.data
    #     print(selected)


class Viewer(App):
    """An app to view logging."""

    CSS_PATH = "layout.css"
    BINDINGS = [("d", "toggle_dark", "Toggle dark mode")]

    def compose(self) -> ComposeResult:
        yield SideBar()
        yield LogViewer()
        yield Footer()

    def action_toggle_dark(self) -> None:
        self.dark = not self.dark


if __name__ == "__main__":
    app = Viewer()
    app.run()
