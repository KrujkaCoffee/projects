from __future__ import annotations

from PyQt5.QtCore import QRegularExpression
from PyQt5.QtGui import QFont, QSyntaxHighlighter, QTextCharFormat

from app.theme import ThemeDefinition, current_theme, theme_color


class SqlHighlighter(QSyntaxHighlighter):
    KEYWORDS = (
        "SELECT",
        "FROM",
        "WHERE",
        "JOIN",
        "LEFT",
        "RIGHT",
        "FULL",
        "INNER",
        "OUTER",
        "ON",
        "AS",
        "WITH",
        "RECURSIVE",
        "INSERT",
        "INTO",
        "VALUES",
        "UPDATE",
        "SET",
        "DELETE",
        "RETURNING",
        "CREATE",
        "ALTER",
        "DROP",
        "TRUNCATE",
        "GROUP",
        "BY",
        "ORDER",
        "HAVING",
        "LIMIT",
        "OFFSET",
        "UNION",
        "ALL",
        "DISTINCT",
        "CASE",
        "WHEN",
        "THEN",
        "ELSE",
        "END",
        "AND",
        "OR",
        "NOT",
        "NULL",
        "IS",
        "TRUE",
        "FALSE",
        "EXPLAIN",
        "ANALYZE",
    )

    def __init__(self, document) -> None:
        super().__init__(document)
        self._rules: list[tuple[QRegularExpression, QTextCharFormat]] = []
        self.apply_theme(current_theme())

    def apply_theme(self, theme: ThemeDefinition) -> None:
        keyword = QTextCharFormat()
        keyword.setForeground(theme_color("focus", theme))
        keyword.setFontWeight(QFont.Bold)
        string = QTextCharFormat()
        string.setForeground(theme_color("saved", theme))
        comment = QTextCharFormat()
        comment.setForeground(theme_color("muted", theme))
        comment.setFontItalic(True)
        number = QTextCharFormat()
        number.setForeground(theme_color("draft", theme))
        self._rules = [
            (
                QRegularExpression(
                    r"\b(?:" + "|".join(self.KEYWORDS) + r")\b",
                    QRegularExpression.CaseInsensitiveOption,
                ),
                keyword,
            ),
            (QRegularExpression(r"'(?:''|[^'])*'"), string),
            (QRegularExpression(r"\b\d+(?:\.\d+)?\b"), number),
            (QRegularExpression(r"--[^\n]*"), comment),
        ]
        self.rehighlight()

    def highlightBlock(self, text: str) -> None:
        for expression, char_format in self._rules:
            iterator = expression.globalMatch(text)
            while iterator.hasNext():
                match = iterator.next()
                self.setFormat(
                    match.capturedStart(),
                    match.capturedLength(),
                    char_format,
                )


__all__ = ["SqlHighlighter"]
