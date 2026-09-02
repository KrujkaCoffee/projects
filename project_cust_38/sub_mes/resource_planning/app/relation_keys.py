from __future__ import annotations

import hashlib
import json
import re
import unicodedata


_CYRILLIC_TRANSLITERATION = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
    'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch',
    'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
    'і': 'i', 'ї': 'yi', 'є': 'ye', 'ґ': 'g',
}


def _readable_slug(value: str, *, limit: int = 40) -> str:
    text = unicodedata.normalize('NFKC', str(value or '').strip()).casefold()
    text = ''.join(_CYRILLIC_TRANSLITERATION.get(char, char) for char in text)
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'[^a-z0-9_]+', '_', text)
    text = re.sub(r'_+', '_', text).strip('_')
    return (text[:limit].rstrip('_') or 'table')


def build_relation_key(source_table_key: str, target_table_key: str) -> str:
    """Вернуть читаемый и устойчивый ключ для направленной пары таблиц."""

    source = str(source_table_key or '').strip()
    target = str(target_table_key or '').strip()
    payload = json.dumps([source, target], ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    digest = hashlib.blake2b(payload, digest_size=8).hexdigest()
    return f'rel_{_readable_slug(source)}__{_readable_slug(target)}__{digest}'


def relation_key_owns_endpoints(
    existing_source: str,
    existing_target: str,
    source_table_key: str,
    target_table_key: str,
) -> bool:
    """Проверить, что существующий ключ остаётся у той же направленной пары."""

    return (
        str(existing_source or '').strip() == str(source_table_key or '').strip()
        and str(existing_target or '').strip() == str(target_table_key or '').strip()
    )
