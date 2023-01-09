import asyncio

import pytest
from kubernetes_asyncio import client, config
from kubernetes_asyncio.client.api_client import ApiClient


@pytest.mark.asyncio
async def test_get_namespaces():
    cfg = await config.load_kube_config()

    # async with ApiClient() as api:
    #     v1 = client.CoreV1Api(api)

    #     # resp = await v1.
    contexts = cfg.list_contexts()
    print(contexts)
    # print(cfg)
    # {'cluster': 'api-ocp-01-prd-ahcaws-com:6443', 'namespace': 'ogi-kcn-acc', 'user': 'AL24374/api-ocp-01-prd-ahcaws-com:6443'}
