import asyncio

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.message import Message
from textual.widgets import Input, Label, ListItem, ListView

from glasses import dependencies
from glasses.namespace_provider import BaseK8, Pod


class NestedListView(Vertical):
    _resource: BaseK8
    _delay_update_task: asyncio.Task | None = None

    BINDINGS = [Binding("b", "back", "back"), Binding("f", "filter", "filter")]

    def compose(self) -> ComposeResult:
        yield Label("main", id="title")
        yield Input(placeholder="filter text", id="filter")
        yield ListView(classes="focusable", id="resources")

    async def on_mount(self) -> None:
        resource = dependencies.get_namespace_provider()
        await self.update_view(resource, refresh=True)

    async def on_show(self) -> None:
        self.query_one("#resources").focus()

    async def update_view(self, resource: BaseK8, refresh: bool = True) -> None:
        """Update the view with the latest resource data.

        Args:
            resource: a k8 resource, like a namespace or pod.
            refresh: query the api to refresh the resource. Defaults to True.
        """
        self._resource = resource
        _list_view = self.query_one("#resources", expect_type=ListView)

        if refresh:
            await resource.refresh()

        (self.query_one("#title", expect_type=Label)).update(resource.name)
        (self.query_one("#filter", expect_type=Input)).value = resource.filter_text

        await _list_view.clear()

        for item in resource.filter_items():
            _list_view.append(ListItem(Label(item.label), id=item.name, classes="item"))

    async def action_filter(self) -> None:
        self.query_one("#filter").focus()

    async def action_back(self) -> None:
        if self._resource.parent is None:
            return
        await self.update_view(self._resource.parent)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """User pressed enter inside the filter input.

        Focus on the list view again."""
        (self.query_one("#resources", expect_type=ListView)).focus()

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        """User has selected a resource.

        Checking whether it is a selection to use or whether to get the children and proceed.
        """
        id = event.item.id

        selected_resource = self._resource.items[id]

        if isinstance(selected_resource, Pod):
            self.post_message(NestedListView.Selected(data=selected_resource))
            print("sent")
        else:
            await self.update_view(selected_resource, refresh=True)

        event.stop()

    def _update_with_delay(self) -> None:
        """Update the ui after a delay

        Prevent updating the UI too much when enter keys into the filter.
        """
        if self._delay_update_task:
            self._delay_update_task.cancel()

        async def delayed_update() -> None:
            try:
                await asyncio.sleep(0.1)
                await self.update_view(resource=self._resource, refresh=False)
            except asyncio.CancelledError:
                pass

        self._delay_update_task = asyncio.create_task(delayed_update())

    async def on_input_changed(self, event: Input.Changed) -> None:
        if self._resource.filter_text == event.value:
            # filter not changed. Do nothing
            return

        self._resource.filter_text = event.value

        self._update_with_delay()
        event.stop()

    async def on_unmount(self) -> None:
        if self._delay_update_task:
            self._delay_update_task.cancel()

    class Selected(Message):
        def __init__(self, data: Pod) -> None:
            self.data = data
            super().__init__()
