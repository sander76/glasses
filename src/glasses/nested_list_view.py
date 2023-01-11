from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Label, ListItem, ListView

from glasses.namespace_provider import BaseK8, Cluster, Commands


class UpdateableListView(Widget):
    DEFAULT_CSS = """
    UpdateableListView {
        layout: vertical;
        overflow-y: auto;

    }
    """
    BINDINGS = [("r", "update_view", "Update view")]

    def __init__(
        self,
    ) -> None:
        super().__init__()
        self._listview = ListView()
        self._title = Label("no title")

    def compose(self):
        yield self._title
        yield self._listview

    async def update(
        self,
        title: str,
        items: dict[str, BaseK8],
        commands: set[Commands],
        add_back_navigation: bool = True,
        can_refresh: bool = True,
    ):
        self._title.update(title)
        await self._listview.clear()
        if add_back_navigation:
            self._listview.append(ListItem(Label(" <Back"), id="navigate_back"))
        if can_refresh:
            self._listview.append(ListItem(Label(" [Refresh]"), id="update_view"))
        for item in items.values():
            self._listview.append(ListItem(Label(f"> {item.name}"), id=item.name))
        for cmd in commands:
            self._listview.append(
                ListItem(Label(f" \[{cmd.value}]"), id=cmd.name)  # noqa
            )


class SlideView(Widget):
    BINDINGS = [("b", "navigate_back", "Back")]

    def __init__(self, tree_data: Cluster) -> None:
        super().__init__()
        self.history: list[BaseK8] = [tree_data]
        self._updateable_list_view = UpdateableListView()

    def compose(self) -> ComposeResult:
        yield self._updateable_list_view

    async def on_mount(self):
        await self.update_view()

    async def update_view(self, refresh: bool = False):
        items = await self.get_items(refresh)
        await self._updateable_list_view.update(
            self.history[-1].name,
            items,
            self.history[-1].commands,
        )

    async def get_items(self, refresh: bool = False) -> dict[str, BaseK8]:
        if refresh:
            items = await self.history[-1].refresh()
        else:
            items = self.history[-1].items
        return items

    async def action_navigate_back(self):
        await self._navigate_back()

    async def _navigate_back(self):
        if len(self.history) == 1:
            return
        self.history.pop()
        await self.update_view()

    async def on_list_view_selected(self, event: ListView.Selected):
        id = event.item.id
        assert isinstance(id, str)
        if id == "update_view":
            await self.update_view(refresh=True)
        elif id == "navigate_back":
            await self._navigate_back()
        elif self.history[-1].items and id in self.history[-1].items:
            new_view = self.history[-1].items[id]
            self.history.append(new_view)
            await self.update_view()
        elif Commands[id] in self.history[-1].commands:
            await self.emit(
                SlideView.Selected(self, data=self.history[-1], id=Commands[id])
            )
        else:
            print("nothing found.")

    class Selected(Message):
        def __init__(self, sender: "SlideView", data: BaseK8, id: str) -> None:
            super().__init__(sender)
            self.data = data
            self.id = id
