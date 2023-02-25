from datetime import datetime
from unittest.mock import Mock

from glasses.namespace_provider import Pod

CURRENT_DATE = datetime.now()


def test_pod_label():
    pod = Pod("short name", "irrelevant_namespace", Mock(), CURRENT_DATE)
    result = f"> short name  [{CURRENT_DATE.strftime(Pod.DATETIME_OUTPUT)}]"

    label = pod.label
    assert label.plain == result
