"""Test glasses functionality on a minikube cluster.

Follow these instructions up to part 3 so you have a
web app running including external access:

https://www.digitalocean.com/community/tutorials/how-to-use-minikube-for-local-kubernetes-development-and-testing

"""
import asyncio

from glasses.controllers.log_provider import K8LogReader

WEB_SERVICE_URL = "http://192.168.49.2:30417"
POD_NAME = "web-84fb9498c7-kl7m7"
POD_NAME_SPACE = "default"


async def printer(logger: K8LogReader) -> None:
    try:
        async for itm in logger.read():
            print(itm.raw)
    except asyncio.CancelledError:
        print("stop reading")


async def run_logger() -> None:
    logger = K8LogReader()
    logger.namespace = POD_NAME_SPACE
    logger.pod = POD_NAME

    logger.start()

    print_task = asyncio.create_task(printer(logger))
    await asyncio.sleep(120)

    # stop everything
    await logger.stop()
    print_task.cancel()
    await print_task


if __name__ == "__main__":
    asyncio.run(run_logger())
