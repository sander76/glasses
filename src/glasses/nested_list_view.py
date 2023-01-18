import asyncio

from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Input, Label, ListItem, ListView

from glasses.namespace_provider import BaseK8, Cluster, Commands

ListItems = dict[str, BaseK8]


class UpdateableListView(Widget):
    DEFAULT_CSS = """
    UpdateableListView {
        layout: vertical;
        overflow-y: auto;
    }
    """

    def __init__(self, item: BaseK8) -> None:
        super().__init__()
        self._listview = ListView()
        self._filter = Input(placeholder="filter text")
        self._title = Label("no title")
        self._item: BaseK8 = item
        # self._filter: str = ""
        self._delay_update_task: asyncio.Task | None = None

    def compose(self):
        yield self._title
        yield self._filter
        yield self._listview

    async def update(self, view_item_data: BaseK8, refresh: bool):
        self._item = view_item_data
        if refresh:
            await self._item.refresh()

        await self._update()

    async def _update(self) -> None:
        self._title.update(self._item.name)
        self._filter.value = self._item.filter_text

        await self._listview.clear()

        self._listview.append(ListItem(Label(" <Back"), id="navigate_back"))
        self._listview.append(ListItem(Label(" [Refresh]"), id="update_view"))

        for item in self._item.filter_items():
            print(item)
            self._listview.append(ListItem(Label(f"> {item.name}"), id=item.name))
        for cmd in self._item.commands:
            self._listview.append(
                ListItem(Label(f" \[{cmd.value}]"), id=cmd.name)  # noqa
            )

    async def delay_update(self):
        try:
            await asyncio.sleep(0.4)
            await self._update()
        except asyncio.CancelledError:
            pass

    async def on_input_changed(self, event: Input.Changed):
        if self._item.filter_text == event.value:
            return

        self._item.filter_text = event.value
        if self._delay_update_task:
            self._delay_update_task.cancel()
        self._delay_update_task = asyncio.create_task(self.delay_update())

    async def on_unmount(self):
        if self._delay_update_task:
            self._delay_update_task.cancel()


class SlideView(Widget):
    BINDINGS = [("b", "navigate_back", "Back")]

    def __init__(self, tree_data: Cluster) -> None:
        super().__init__()
        self.history: list[BaseK8] = [tree_data]
        self._updateable_list_view = UpdateableListView(tree_data)

    def compose(self) -> ComposeResult:
        yield self._updateable_list_view

    async def on_mount(self):
        await self.update_view()

    async def update_view(self, refresh: bool = False):
        await self._updateable_list_view.update(self.history[-1], refresh)

    async def action_navigate_back(self):
        await self._navigate_back()

    async def _navigate_back(self):
        if len(self.history) == 1:
            return
        self.history.pop()
        await self.update_view()

    async def _new_view(self, item_id: str):
        new_view = self.history[-1].items[item_id]
        self.history.append(new_view)
        await self.update_view()

    async def on_list_view_selected(self, event: ListView.Selected):
        id = event.item.id
        assert isinstance(id, str)
        if id == "update_view":
            await self.update_view(refresh=True)
        elif id == "navigate_back":
            await self._navigate_back()
        elif self.history[-1].items and id in self.history[-1].items:
            await self._new_view(id)
        elif Commands[id] in self.history[-1].commands:
            await self.emit(
                SlideView.Command(self, data=self.history[-1], id=Commands[id])
            )
        else:
            print("nothing found.")

    class Selected(Message):
        def __init__(self, sender: "SlideView", data: BaseK8, id: str) -> None:
            super().__init__(sender)
            self.data = data
            self.id = id

    class Command(Message):
        def __init__(self, sender: "SlideView", data: BaseK8, id: Commands) -> None:
            super().__init__(sender)
            self.data = data
            self.id = id
