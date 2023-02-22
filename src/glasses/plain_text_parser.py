import logging

from lark import Lark, LarkError, Token
from rich.text import Text

_logger = logging.getLogger(__name__)

# for lark cheatsheet go here: https://github.com/lark-parser/lark/blob/master/docs/_static/lark_cheatsheet.pdf

parser = Lark(
    r"""
    start:  _line+ // find the rule 1 or more times.

    _line: WARN | ERROR | SPACES | WORDS // the underscore tells lark to inline the rule (no nested tree)

    WARN: "warn" | "warning" | /\[[\s]*warn[\w]*[\s]*\]/
    ERROR: "err" | "error" | /\[[\s]*err[\w]*[\s]*\]/
    WORDS.-100: /[\S]+/  // has a priority of -100 (the lowest)
    SPACES: WS+

    %import common.WS

""",
    start="start",
)


def parse(input: str) -> Text:
    try:
        tokens = parser.parse(input)
    except LarkError:
        _logger.exception("failed to tokenize input %s", input)
        return Text(input)

    output: list[Text | str] = []

    for token in tokens.children:
        assert isinstance(token, Token)
        if token.type == "WARN":
            output.append(Text(token.value, "yellow"))
        elif token.type == "ERROR":
            output.append(Text(token.value, "red"))
        else:
            output.append(token.value)

    result = Text.assemble(*output)
    return result
