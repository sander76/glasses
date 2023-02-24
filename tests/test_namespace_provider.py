from datetime import datetime
from unittest.mock import Mock

from glasses.namespace_provider import Pod

CURRENT_DATE = datetime.now()


def test_short_name():
    pod = Pod("short name", "irrelevant_namespace", Mock(), CURRENT_DATE)
    result = f"> short name                                         {CURRENT_DATE.strftime(Pod.DATETIME_OUTPUT)}"

    label = pod.label
    assert label.plain == result


def test_long_name():
    pod = Pod(
        "A long name that exceeds the left padding inside the fstring padding",
        "irrelevant_namespace",
        Mock(),
        CURRENT_DATE,
    )
    result = f"> A long name that exceeds the left padding inside the fstring padding {CURRENT_DATE.strftime(Pod.DATETIME_OUTPUT)}"

    label = pod.label
    assert label.plain == result
