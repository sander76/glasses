import itertools
import json
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from rich import print
from rich.text import Text

# default UTC time based ecs timestamp.
TEXT_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
# 2022-12-27T11:04:22.329Z

DATETIME_OUTPUT = "%Y-%m-%d %H:%M:%S"


class ParseError(Exception):
    """A general parsing error"""


def _time(time: str) -> Text:
    utc_dt = datetime.strptime(time, TEXT_FORMAT).replace(tzinfo=timezone.utc)
    tz_aware = utc_dt.astimezone()
    return Text(f"{tz_aware.strftime(DATETIME_OUTPUT)}", "#999999")


def _level(level: str) -> Text:
    if level == "error":
        color = "red"
    elif level == "warning":
        color = "yellow"
    else:
        color = "green"
    return Text(f"[{level:<10}]", color)


def _logger(logger: str) -> Text:
    return Text(f"[{logger}]", "blue")


def _message(message: str) -> Text:
    return Text(f"{message:<40}")


def _parse_exception(value: str) -> Text:
    return Text(f"\n{value}")


def _parse_general(key: str, message: str | dict | list | int | float) -> Text:
    return Text.assemble(Text(key, "green"), "=", Text(str(message), "purple"))


def jsonparse(input: str) -> Text:
    try:
        _js = json.loads(input)
    except json.JSONDecodeError:
        raise ParseError(f"Unable to JSON parse incoming data {input}")
    return _parse(_js)


def _parse(_js: dict[Any, Any]) -> Text:
    parsed_items: dict[str, Text] = defaultdict(Text)
    for key, value in _js.items():
        if key == "@timestamp":
            parsed_items[key] = _time(value)
        elif key == "log.level":
            parsed_items[key] = _level(value)
        elif key == "message":
            parsed_items[key] = _message(value)
        elif key == "logger":
            parsed_items[key] = _logger(value)
        elif key == "exception":
            parsed_items[key] = _parse_exception(value)
        else:
            parsed_items[key] = _parse_general(key, value)

    first_values: list[str] = ["@timestamp", "log.level", "message", "logger"]
    last_values: list[str] = ["exception"]

    first_items = []
    for ordered_key in first_values:
        item = parsed_items.pop(ordered_key, None)
        if item:
            first_items.append(item)

    last_items = []
    for last_value in last_values:
        item = parsed_items.pop(last_value, None)
        if item:
            last_items.append(item)

    return Text(" ").join(
        itertools.chain(first_items, parsed_items.values(), last_items)
    )


if __name__ == "__main__":
    from glasses.controllers import log_provider

    log_data = log_provider.DummyLogReader.log_data()
    for line in range(5):
        log_line = next(log_data)
        print(jsonparse(log_line))
