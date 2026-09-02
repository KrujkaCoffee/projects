from __future__ import annotations

import re
from dataclasses import dataclass


class SqlSafetyError(ValueError):
    pass


@dataclass(frozen=True)
class SqlAnalysis:
    statement: str
    command: str
    is_write: bool
    stream_results: bool


_READ_COMMANDS = frozenset({"SELECT", "TABLE", "VALUES", "SHOW"})
_WRITE_COMMANDS = frozenset(
    {
        "INSERT",
        "UPDATE",
        "DELETE",
        "MERGE",
        "CREATE",
        "ALTER",
        "DROP",
        "TRUNCATE",
        "COMMENT",
        "GRANT",
        "REVOKE",
        "CALL",
        "DO",
        "REFRESH",
        "ANALYZE",
    }
)
_ROOT_COMMANDS = _READ_COMMANDS | _WRITE_COMMANDS | {"EXPLAIN"}
_FORBIDDEN_COMMANDS = frozenset(
    {
        "BEGIN",
        "START",
        "COMMIT",
        "ROLLBACK",
        "SAVEPOINT",
        "RELEASE",
        "SET",
        "RESET",
        "DISCARD",
        "COPY",
        "LISTEN",
        "UNLISTEN",
        "NOTIFY",
        "LOAD",
        "PREPARE",
        "EXECUTE",
        "DEALLOCATE",
        "DECLARE",
        "FETCH",
        "MOVE",
        "CLOSE",
        "VACUUM",
        "CLUSTER",
        "REINDEX",
    }
)
_INCOMPATIBLE_PREFIXES = frozenset(
    {
        ("CREATE", "DATABASE"),
        ("CREATE", "TABLESPACE"),
        ("DROP", "DATABASE"),
        ("DROP", "TABLESPACE"),
        ("ALTER", "SYSTEM"),
    }
)
_DOLLAR_TAG = re.compile(r"\$(?:[A-Za-z_][A-Za-z0-9_]*)?\$")


def analyze_sql(text: str) -> SqlAnalysis:
    statements = split_sql_statements(text)
    if not statements:
        raise SqlSafetyError("SQL-запрос пуст")
    if len(statements) != 1:
        raise SqlSafetyError(
            "За один запуск разрешена одна SQL-команда. Выделите нужный statement отдельно."
        )
    statement = statements[0]
    words = _top_level_words(statement)
    if not words:
        raise SqlSafetyError("Не удалось определить SQL-команду")
    command = _root_command(words)
    if command in _FORBIDDEN_COMMANDS:
        raise SqlSafetyError(
            f"Команда {command} отключена: она управляет общей сессией, транзакцией или курсором."
        )
    first_two = tuple(word for word, depth in words if depth == 0)[:2]
    if first_two in _INCOMPATIBLE_PREFIXES:
        raise SqlSafetyError(
            f"Команда {' '.join(first_two)} не выполняется внутри безопасной транзакции SQL Tools."
        )

    top_level = [word for word, depth in words if depth == 0]
    explain_write = command == "EXPLAIN" and any(
        word in _WRITE_COMMANDS for word in top_level[1:]
    )
    data_modifying_cte = top_level[0] == "WITH" and any(
        word in {"INSERT", "UPDATE", "DELETE", "MERGE"} for word, _depth in words[1:]
    )
    select_into = command == "SELECT" and "INTO" in top_level[1:]
    is_write = (
        explain_write
        or data_modifying_cte
        or select_into
        or command not in (_READ_COMMANDS | {"EXPLAIN"})
    )
    stream_results = not is_write and command in {"SELECT", "TABLE", "VALUES"}
    return SqlAnalysis(statement, command, is_write, stream_results)


def split_sql_statements(text: str) -> list[str]:
    statements: list[str] = []
    current: list[str] = []
    state = "normal"
    dollar_tag = ""
    single_backslash_escapes = False
    block_depth = 0
    i = 0
    while i < len(text):
        char = text[i]
        following = text[i + 1] if i + 1 < len(text) else ""

        if state == "line_comment":
            current.append(char)
            if char == "\n":
                state = "normal"
            i += 1
            continue
        if state == "block_comment":
            if char == "/" and following == "*":
                block_depth += 1
                current.extend((char, following))
                i += 2
                continue
            if char == "*" and following == "/":
                block_depth -= 1
                current.extend((char, following))
                i += 2
                if block_depth == 0:
                    state = "normal"
                continue
            current.append(char)
            i += 1
            continue
        if state == "single_quote":
            current.append(char)
            if single_backslash_escapes and char == "\\" and following:
                current.append(following)
                i += 2
                continue
            if char == "'" and following == "'":
                current.append(following)
                i += 2
                continue
            if char == "'":
                state = "normal"
            i += 1
            continue
        if state == "double_quote":
            current.append(char)
            if char == '"' and following == '"':
                current.append(following)
                i += 2
                continue
            if char == '"':
                state = "normal"
            i += 1
            continue
        if state == "dollar_quote":
            if text.startswith(dollar_tag, i):
                current.append(dollar_tag)
                i += len(dollar_tag)
                state = "normal"
            else:
                current.append(char)
                i += 1
            continue

        if char == "-" and following == "-":
            current.extend((char, following))
            i += 2
            state = "line_comment"
            continue
        if char == "/" and following == "*":
            current.extend((char, following))
            i += 2
            block_depth = 1
            state = "block_comment"
            continue
        if char == "'":
            current.append(char)
            single_backslash_escapes = _is_escape_string_prefix(text, i)
            state = "single_quote"
            i += 1
            continue
        if char == '"':
            current.append(char)
            state = "double_quote"
            i += 1
            continue
        if char == "$":
            match = _DOLLAR_TAG.match(text, i)
            if match:
                dollar_tag = match.group(0)
                current.append(dollar_tag)
                i = match.end()
                state = "dollar_quote"
                continue
        if char == ";":
            fragment = "".join(current).strip()
            if _contains_code(fragment):
                statements.append(fragment)
            current.clear()
            i += 1
            continue
        current.append(char)
        i += 1

    fragment = "".join(current).strip()
    if _contains_code(fragment):
        statements.append(fragment)
    return statements


def _contains_code(text: str) -> bool:
    return bool(
        _top_level_words(text) or re.search(r"[0-9'\"$]", _without_comments(text))
    )


def _without_comments(text: str) -> str:
    return re.sub(r"--[^\n]*|/\*.*?\*/", " ", text, flags=re.DOTALL)


def _root_command(words: list[tuple[str, int]]) -> str:
    top_level = [word for word, depth in words if depth == 0]
    if not top_level:
        return ""
    first = top_level[0]
    if first != "WITH":
        return first
    for word in top_level[1:]:
        if word in _ROOT_COMMANDS:
            return word
    return "WITH"


def _top_level_words(text: str) -> list[tuple[str, int]]:
    result: list[tuple[str, int]] = []
    state = "normal"
    dollar_tag = ""
    single_backslash_escapes = False
    block_depth = 0
    paren_depth = 0
    i = 0
    while i < len(text):
        char = text[i]
        following = text[i + 1] if i + 1 < len(text) else ""
        if state == "line_comment":
            if char == "\n":
                state = "normal"
            i += 1
            continue
        if state == "block_comment":
            if char == "/" and following == "*":
                block_depth += 1
                i += 2
            elif char == "*" and following == "/":
                block_depth -= 1
                i += 2
                if block_depth == 0:
                    state = "normal"
            else:
                i += 1
            continue
        if state == "single_quote":
            escaped_character = single_backslash_escapes and char == "\\" and following
            doubled_quote = char == "'" and following == "'"
            if escaped_character or doubled_quote:
                i += 2
            else:
                if char == "'":
                    state = "normal"
                i += 1
            continue
        if state == "double_quote":
            if char == '"' and following == '"':
                i += 2
            else:
                if char == '"':
                    state = "normal"
                i += 1
            continue
        if state == "dollar_quote":
            if text.startswith(dollar_tag, i):
                i += len(dollar_tag)
                state = "normal"
            else:
                i += 1
            continue
        if char == "-" and following == "-":
            state = "line_comment"
            i += 2
            continue
        if char == "/" and following == "*":
            state = "block_comment"
            block_depth = 1
            i += 2
            continue
        if char == "'":
            single_backslash_escapes = _is_escape_string_prefix(text, i)
            state = "single_quote"
            i += 1
            continue
        if char == '"':
            state = "double_quote"
            i += 1
            continue
        if char == "$":
            match = _DOLLAR_TAG.match(text, i)
            if match:
                dollar_tag = match.group(0)
                state = "dollar_quote"
                i = match.end()
                continue
        if char == "(":
            paren_depth += 1
            i += 1
            continue
        if char == ")":
            paren_depth = max(0, paren_depth - 1)
            i += 1
            continue
        if char.isalpha() or char == "_":
            end = i + 1
            while end < len(text) and (text[end].isalnum() or text[end] in {"_", "$"}):
                end += 1
            result.append((text[i:end].upper(), paren_depth))
            i = end
            continue
        i += 1
    return result


def _is_escape_string_prefix(text: str, quote_index: int) -> bool:
    if quote_index < 1 or text[quote_index - 1] not in {"e", "E"}:
        return False
    before = text[quote_index - 2] if quote_index >= 2 else ""
    return not (before.isalnum() or before in {"_", "$"})


__all__ = ["SqlAnalysis", "SqlSafetyError", "analyze_sql", "split_sql_statements"]
