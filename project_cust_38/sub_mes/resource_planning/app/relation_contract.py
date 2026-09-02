from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


SUPPORTED_CARDINALITIES = ('many_to_one', 'one_to_one', 'one_to_many')
SUPPORTED_JOIN_TYPES = ('LEFT JOIN', 'INNER JOIN')
SUPPORTED_MISSING_POLICIES = ('none', 'empty', 'raise', 'drop', 'default')
SUPPORTED_ON_MANY_POLICIES = ('error', 'first', 'last', 'list')
SUPPORTED_PAIR_ROLES = ('direct',)
SUPPORTED_PAIR_OPERATORS = ('=',)


@dataclass(frozen=True)
class ContractIssue:
    field: str
    message: str
    blocking: bool = True


@dataclass(frozen=True)
class ContractValidation:
    issues: tuple[ContractIssue, ...]

    @property
    def valid(self) -> bool:
        return not any(issue.blocking for issue in self.issues)

    @property
    def errors(self) -> tuple[ContractIssue, ...]:
        return tuple(issue for issue in self.issues if issue.blocking)

    @property
    def warnings(self) -> tuple[ContractIssue, ...]:
        return tuple(issue for issue in self.issues if not issue.blocking)

    def message(self) -> str:
        return '\n'.join(issue.message for issue in self.issues)


def _enabled(value) -> bool:
    if isinstance(value, str):
        return value.strip().lower() not in {'', '0', 'false', 'no', 'off'}
    return bool(value)


def _unsupported(
    issues: list[ContractIssue],
    relation: dict,
    field: str,
    supported: Iterable[str],
    label: str,
) -> None:
    value = str(relation.get(field) or '').strip()
    supported = tuple(supported)
    if value in supported:
        return
    active = _enabled(relation.get('is_enabled', 1))
    suffix = '' if active else ' Отключённую связь можно сохранить как экспериментальную.'
    issues.append(
        ContractIssue(
            field,
            f'{label} «{value or "пусто"}» не исполняется текущим ORM. Допустимо: {", ".join(supported)}.{suffix}',
            blocking=active,
        )
    )


def validate_relation_contract(relation: dict, pairs: list[dict]) -> ContractValidation:
    issues: list[ContractIssue] = []
    active = _enabled(relation.get('is_enabled', 1))
    required = (
        ('relation_key', 'Нужен ключ связи.'),
        ('source_table_key', 'Нужна левая таблица.'),
        ('target_table_key', 'Нужна правая таблица.'),
    )
    for field, message in required:
        if not str(relation.get(field) or '').strip():
            issues.append(ContractIssue(field, message))

    _unsupported(issues, relation, 'cardinality', SUPPORTED_CARDINALITIES, 'Кардинальность')
    _unsupported(issues, relation, 'join_type', SUPPORTED_JOIN_TYPES, 'JOIN')
    _unsupported(issues, relation, 'missing_policy', SUPPORTED_MISSING_POLICIES, 'missing_policy')
    _unsupported(issues, relation, 'on_many_policy', SUPPORTED_ON_MANY_POLICIES, 'on_many_policy')

    if not pairs:
        issues.append(
            ContractIssue(
                'pairs',
                'Для включённой связи нужна хотя бы одна пара полей.' if active else 'У связи нет пар полей.',
                blocking=active,
            )
        )
        return ContractValidation(tuple(issues))

    source = str(relation.get('source_table_key') or '').strip()
    target = str(relation.get('target_table_key') or '').strip()
    endpoints = {source, target}
    seen: set[tuple[str, str, str, str]] = set()
    for index, pair in enumerate(pairs, 1):
        prefix = f'Пара {index}'
        left_table = str(pair.get('left_table_key') or '').strip()
        left_field = str(pair.get('left_field_name') or '').strip()
        right_table = str(pair.get('right_table_key') or '').strip()
        right_field = str(pair.get('right_field_name') or '').strip()
        for field, value, label in (
            ('left_table_key', left_table, 'левая таблица'),
            ('left_field_name', left_field, 'левое поле'),
            ('right_table_key', right_table, 'правая таблица'),
            ('right_field_name', right_field, 'правое поле'),
        ):
            if not value:
                issues.append(
                    ContractIssue(
                        f'pairs[{index - 1}].{field}',
                        f'{prefix}: не заполнено {label}.',
                        blocking=active,
                    )
                )
        if left_table and right_table and {left_table, right_table} != endpoints:
            issues.append(
                ContractIssue(
                    f'pairs[{index - 1}]',
                    f'{prefix}: таблицы пары должны совпадать с концами связи.',
                    blocking=active,
                )
            )
        role = str(pair.get('role') or '').strip()
        operator = str(pair.get('operator') or '').strip()
        pair_join_type = str(pair.get('pair_join_type') or '').strip()
        if role not in SUPPORTED_PAIR_ROLES:
            issues.append(
                ContractIssue(
                    f'pairs[{index - 1}].role',
                    f'{prefix}: поддерживается только role=direct.',
                    blocking=active,
                )
            )
        if operator not in SUPPORTED_PAIR_OPERATORS:
            issues.append(
                ContractIssue(
                    f'pairs[{index - 1}].operator',
                    f'{prefix}: поддерживается только operator==.',
                    blocking=active,
                )
            )
        if pair_join_type:
            issues.append(
                ContractIssue(
                    f'pairs[{index - 1}].pair_join_type',
                    f'{prefix}: pair_join_type должен быть пустым.',
                    blocking=active,
                )
            )
        identity = (left_table, left_field, right_table, right_field)
        if all(identity):
            if identity in seen:
                issues.append(
                    ContractIssue(
                        f'pairs[{index - 1}]',
                        f'{prefix}: дублирует предыдущую пару.',
                        blocking=active,
                    )
                )
            seen.add(identity)
    return ContractValidation(tuple(issues))
