from __future__ import annotations

from typing import Iterable

from .relation_keys import relation_key_owns_endpoints


def _flag(value) -> int:
    if isinstance(value, str):
        return 0 if value.strip().lower() in {'', '0', 'false', 'no', 'off'} else 1
    return 1 if value else 0


def persist_relation(cur, relation: dict, pairs: Iterable[dict]) -> None:
    """Сохранить одну бинарную связь через уже открытую транзакцию."""

    relation_key = str(relation.get('relation_key') or '').strip()
    source = str(relation.get('source_table_key') or '').strip()
    target = str(relation.get('target_table_key') or '').strip()
    cur.execute(
        """
        SELECT source_table_key, target_table_key
        FROM public.admin_table_relations
        WHERE relation_key=%s
        FOR UPDATE
        """,
        [relation_key],
    )
    existing = cur.fetchone()
    if existing and not relation_key_owns_endpoints(
        existing.get('source_table_key'),
        existing.get('target_table_key'),
        source,
        target,
    ):
        raise ValueError(
            f'Ключ связи {relation_key} уже принадлежит '
            f"{existing.get('source_table_key')} → {existing.get('target_table_key')}. "
            'Для другой пары таблиц нужен новый ключ.'
        )
    cur.execute(
        """
        INSERT INTO public.admin_table_relations
            (relation_key, relation_name, source_table_key, target_table_key, cardinality, join_type,
             missing_policy, on_many_policy, select_prefix, is_enabled, is_generated, notes, updated_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,to_char(CURRENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS'))
        ON CONFLICT (relation_key) DO UPDATE SET
            relation_name=EXCLUDED.relation_name,
            source_table_key=EXCLUDED.source_table_key,
            target_table_key=EXCLUDED.target_table_key,
            cardinality=EXCLUDED.cardinality,
            join_type=EXCLUDED.join_type,
            missing_policy=EXCLUDED.missing_policy,
            on_many_policy=EXCLUDED.on_many_policy,
            select_prefix=EXCLUDED.select_prefix,
            is_enabled=EXCLUDED.is_enabled,
            is_generated=EXCLUDED.is_generated,
            notes=EXCLUDED.notes,
            updated_at=EXCLUDED.updated_at
        WHERE admin_table_relations.source_table_key=EXCLUDED.source_table_key
          AND admin_table_relations.target_table_key=EXCLUDED.target_table_key
        """,
        [
            relation_key,
            str(relation.get('relation_name') or '').strip() or relation_key,
            source,
            target,
            str(relation.get('cardinality') or ''),
            str(relation.get('join_type') or ''),
            str(relation.get('missing_policy') or ''),
            str(relation.get('on_many_policy') or ''),
            str(relation.get('select_prefix') or '').strip(),
            _flag(relation.get('is_enabled')),
            _flag(relation.get('is_generated')),
            str(relation.get('notes') or ''),
        ],
    )
    if cur.rowcount != 1:
        raise ValueError(
            f'Ключ связи {relation_key} одновременно заняла другая пара таблиц. '
            'Сохранение отменено; повторите создание связи.'
        )
    cur.execute(
        'DELETE FROM public.admin_relation_field_pairs WHERE relation_key=%s',
        [relation_key],
    )
    for index, pair in enumerate(pairs):
        cur.execute(
            """
            INSERT INTO public.admin_relation_field_pairs
                (relation_key, pair_no, left_table_key, left_field_name, right_table_key, right_field_name,
                 role, operator, pair_join_type)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            [
                relation_key,
                index,
                pair['left_table_key'],
                pair['left_field_name'],
                pair['right_table_key'],
                pair['right_field_name'],
                pair.get('role') or 'direct',
                pair.get('operator') or '=',
                pair.get('pair_join_type') or '',
            ],
        )


def persist_relation_batch(cur, drafts: Iterable[dict]) -> None:
    """Сохранить весь проверенный пакет внутри одной внешней транзакции."""

    for draft in drafts:
        persist_relation(
            cur,
            draft.get('relation') or {},
            list(draft.get('pairs') or []),
        )
