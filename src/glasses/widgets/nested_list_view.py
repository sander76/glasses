import asyncio

from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Input, Label, ListItem, ListView

from glasses.namespace_provider import BaseK8, Cluster, Commands


class NestedListView(Widget):
    def __init__(self, tree_data: Cluster) -> None:
        super().__init__()
        self.history: list[BaseK8] = [tree_data]
        self._updateable_list_view = UpdateableListView(tree_data, id="nested_list")

    def compose(self) -> ComposeResult:
        yield self._updateable_list_view

    async def on_mount(self) -> None:
        await self.update_view(refresh=True)

    async def update_view(self, refresh: bool = True) -> None:
        await self._updateable_list_view.update(self.history[-1], refresh)

    async def _navigate_back(self) -> None:
        if len(self.history) == 1:
            return
        self.history.pop()
        await self.update_view()

    async def _new_view(self, item_id: str) -> None:
        new_view = self.history[-1].items[item_id]
        self.history.append(new_view)
        await self.update_view()

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        id = event.item.id
        assert isinstance(id, str)
        if id == "update_view":
            await self.update_view(refresh=True)
        elif id == "navigate_back":
            await self._navigate_back()
        elif self.history[-1].items and id in self.history[-1].items:
            await self._new_view(id)
        elif Commands[id] in self.history[-1].commands:
            await self.post_message(
                NestedListView.Command(self, data=self.history[-1], id=Commands[id])
            )
            print("sent")
        else:
            print("nothing found.")

    class Selected(Message):
        def __init__(self, sender: "NestedListView", data: BaseK8, id: str) -> None:
            super().__init__(sender)
            self.data = data
            self.id = id

    class Command(Message):
        def __init__(
            self, sender: "NestedListView", data: BaseK8, id: Commands
        ) -> None:
            super().__init__(sender)
            self.data = data
            self.id = id


class UpdateableListView(Widget):
    DEFAULT_CSS = """
    UpdateableListView {
        layout: vertical;
        overflow-y: auto;
    }
    """

    def __init__(self, item: BaseK8, id: str) -> None:
        super().__init__(id=id)
        self._listview = ListView()
        self._filter = Input(placeholder="filter text")
        self._title = Label("no title")

        self._item: BaseK8 = item
        self._delay_update_task: asyncio.Task | None = None

    async def on_show(self) -> None:
        self._listview.focus()

    def compose(self) -> ComposeResult:
        yield self._title
        yield self._filter
        yield self._listview

    async def update(self, view_item_data: BaseK8, refresh: bool = True) -> None:
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
            self._listview.append(ListItem(Label(item.label), id=item.name))
        for cmd in self._item.commands:
            self._listview.append(
                ListItem(Label(f" \[{cmd.value}]"), id=cmd.name)  # noqa
            )

    def update_with_delay(self) -> None:
        """Update the ui after a delay

        Prevent updating the UI too much when enter keys into the filter.
        """
        if self._delay_update_task:
            self._delay_update_task.cancel()

        async def delayed_update() -> None:
            try:
                await asyncio.sleep(0.4)
                await self._update()
            except asyncio.CancelledError:
                pass

        self._delay_update_task = asyncio.create_task(delayed_update())

    async def on_input_changed(self, event: Input.Changed) -> None:
        if self._item.filter_text == event.value:
            return

        self._item.filter_text = event.value

        self.update_with_delay()

    async def on_unmount(self) -> None:
        if self._delay_update_task:
            self._delay_update_task.cancel()

    def on_mount(self) -> None:
        self._listview.focus()
