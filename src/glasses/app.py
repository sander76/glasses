from decimal import FloatOperation
from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Button, ListView, Static, TextLog, Tree, Footer

from glasses.dependencies import get_name_space_provider
from glasses.namespace_provider import Pod
from glasses.widgets.input_with_label import InputWithLabel

ID_BTN_REFRESH = "refresh"


class NameSpacesView(Vertical):
    """A list of available namespaces."""

    BINDINGS = [("r", "refresh_namespace", "Refresh namespace")]

    def __init__(self, id: str) -> None:
        super().__init__(id=id)
        self.name_space_provider = get_name_space_provider()

    def compose(self) -> ComposeResult:
        yield Button("refresh", id=ID_BTN_REFRESH)
        self.namespaces = Tree("namespaces", data=self.name_space_provider)
        yield self.namespaces

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        pass
        # if event.button.id == ID_BTN_REFRESH:
        #     # list_view: ListView = self.query_one("#name_spaces_view")
        #     tree_view: Tree = self.query_one("#treeview")

        #     for namespace in await self.name_space_provider.refresh():
        #         tree_view.root.add(namespace.name, data=namespace)

    async def action_refresh_namespace(self):
        selected = self.namespaces.cursor_node
        data = selected.data
        print(selected)

    async def on_tree_node_expanded(self, event: Tree.NodeExpanded) -> None:

        node = event.node
        data = node.data
        if isinstance(data, Pod):
            # pod = node.add(item.name, data=item)
            for command in data.commands:
                node.add_leaf(command)
        else:
            for item in await data.refresh():
                node.add(item.name, data=item)


class SideBar(Static):
    """Namespaces view."""

    def compose(self) -> ComposeResult:
        # yield Vertical(Button("refresh"), Tree("namespaces"))
        yield NameSpacesView(id="namespacesview")


class Output(Vertical):
    def compose(self) -> ComposeResult:
        yield InputWithLabel(id="namespace", label_text="Namespace")
        yield InputWithLabel(id="podname", label_text="Pod name")
        yield TextLog(id="logoutput")


class Viewer(App):
    """An app to view logging."""

    CSS_PATH = "layout.css"
    BINDINGS = [("d", "toggle_dark", "Toggle dark mode")]

    def compose(self) -> ComposeResult:
        yield Output()
        yield SideBar(id="sidebar")
        yield Footer()

    def action_toggle_dark(self) -> None:
        self.dark = not self.dark

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        output = self.query_one(TextLog)

        if event.item.id == "name_spaces_view":
            output.write("found a name_spaces_view")
        else:
            output.write("nothing found")


if __name__ == "__main__":
    app = Viewer()
    app.run()
