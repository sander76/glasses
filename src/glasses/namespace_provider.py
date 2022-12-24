class Pod:
    def __init__(self, name: str, namespace: str):
        self.name = name
        self.namespace = namespace

        self.commands: list[str] = ["log"]

    async def refresh(self):
        pass

    # async def refresh(self) -> list[str]:
    #     raise NotImplementedError()


class NameSpace:
    def __init__(self, name: str) -> None:
        self.name = name

    async def refresh(self) -> list[Pod]:

        raise NotImplementedError()


class NameSpaceProvider:
    async def refresh(self) -> list[NameSpace]:
        raise NotImplementedError()


class DummyPod(Pod):
    ...
    # async def refresh(self) -> list[str]:
    #     await asyncio.sleep(1)
    #     return ["log"]


class DummyNameSpace(NameSpace):
    async def refresh(self) -> list[DummyPod]:
        return [
            DummyPod(name="pod_1", namespace=self.name),
            DummyPod(name="pod_2", namespace=self.name),
        ]


class DummyNameSpaceProvider(NameSpaceProvider):
    async def refresh(self) -> list[NameSpace]:
        return [
            DummyNameSpace(name="a_dummy_namespace"),
            DummyNameSpace(name="another namespace"),
        ]
