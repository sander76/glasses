import pytest

from glasses.log_parsers import plain_text_parser
from glasses.log_parsers.json_parser import _parse


def test_message__parse__returns_valid_string():
    log_message = {
        "@timestamp": "2022-12-27T11:04:22.329Z",
        "log.level": "info",
        "message": "A log message",
        "ecs": {"version": "1.6.0"},
        "extra": "test",
        "logger": "__main__",
    }

    log_line = _parse(log_message)
    expected_plain = "2022-12-27 12:04:22 [info      ] A log message                            [__main__] ecs={'version': '1.6.0'} extra=test"
    assert log_line.plain == expected_plain


def test_message_no_logger__returns_valid_string():
    log_message = {
        "@timestamp": "2022-12-27T11:04:22.329Z",
        "log.level": "info",
        "message": "A log message",
        "ecs": {"version": "1.6.0"},
        "extra": "test",
    }

    log_line = _parse(log_message)
    expected_plain = "2022-12-27 12:04:22 [info      ] A log message                            ecs={'version': '1.6.0'} extra=test"
    assert log_line.plain == expected_plain


def test_message_with_long_message__returns_valid_string():
    log_message = {
        "@timestamp": "2022-12-27T11:04:22.329Z",
        "log.level": "info",
        "message": 5 * "A log message ",  # 5 times.
        "ecs": {"version": "1.6.0"},
        "extra": "test",
    }

    log_line = _parse(log_message)
    expected_plain = "2022-12-27 12:04:22 [info      ] A log message A log message A log message A log message A log message  ecs={'version': '1.6.0'} extra=test"
    assert log_line.plain == expected_plain


@pytest.mark.parametrize(
    "input,output",
    [
        (
            "this has warn message",
            "this has [yellow]warn[/yellow] message",
        ),
        (
            "2023-02-19T07:32:56.254753Z this is a [ warning ] message",
            "2023-02-19T07:32:56.254753Z this is a [yellow][ warning ][/yellow] message",
        ),
    ],
)
def test_message__plain_parser__returns_valid_string(input, output):

    result = plain_text_parser.parse(input)

    assert result.markup == output
