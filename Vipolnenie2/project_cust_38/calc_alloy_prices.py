import statistics
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.CRITICAL)
# ============================================================
# КОНСТАНТЫ
# ============================================================

class MaterialType(IntEnum):
    SOURCE = 1   # источник элементов (лом, ферросплав, чистый металл)
    ALLOY = 2    # готовый сплав (только для аналогов)
    IGNORE = 3   # нешихтовые (смола, песок, огнеупор)

NON_SIGNIFICANT_ELEMENTS = {'C', 'P', 'S'}

@dataclass(slots=True)
class Config:
    # Классификация
    MIN_PRICING_PERCENT: float = 10.0
    MIN_SIGNIFICANT_PERCENT: float = 5.0
    PURE_MATERIAL_PERCENT: float = 99.0
    FERROALLOY_MAIN_PERCENT: float = 40.0
    MAX_SIGNIFICANT_FOR_SOURCE: int = 2

    # Поиск аналогов
    ANALOG_THRESHOLD: float = 3.0

    # Ключевые слова для лома/возврата
    SCRAP_KEYWORDS: tuple = ('ЛОМ', 'ВСП', 'ВОЗВРАТ', 'СКРАП', 'ОБРЕЗЬ')

    # Ручные переопределения
    # code -> {'material_type': ..., 'pricing_elements': [...]}
    MANUAL_OVERRIDES: dict = field(default_factory=dict)


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def safe_float(val) -> float:
    """Безопасное приведение к float."""
    if isinstance(val, (int, float)):
        return float(val)

    if isinstance(val, str):
        val = val.replace(',', '.').replace(' ', '').strip()
        try:
            return float(val)
        except ValueError:
            return 0.0

    return 0.0


def parse_composition(raw: str) -> dict[str, float]:
    """
    'Fe: 97,71%; C: 0,45%' ->
    {'Fe': 97.71, 'C': 0.45}
    """
    comp = {}

    if not raw:
        return comp

    for part in raw.split(';'):
        part = part.strip()

        if not part or ':' not in part:
            continue

        elem, val = part.split(':', 1)

        elem = elem.strip()
        val = val.strip().replace('%', '').replace(',', '.').strip()

        try:
            comp[elem] = float(val)
        except ValueError:
            pass

    return comp


def normalize_composition(comp: dict[str, float]) -> dict[str, float]:
    """Нормализует состав до 100%."""
    total = sum(comp.values())

    if total == 0 or abs(total - 100) < 0.01:
        return comp

    return {
        k: round(v / total * 100, 2)
        for k, v in comp.items()
    }


def weighted_euclidean_distance(
    target: dict[str, float],
    comp: dict[str, float],
    weights: dict[str, float]
) -> float:
    """
    Взвешенное евклидово расстояние.
    Веса нормированы так, что weight[Fe] = 1.0.
    Лишние элементы тоже штрафуются.
    """
    all_elems = set(target) | set(comp)
    dist = 0.0
    for elem in all_elems:
        t_val = target.get(elem, 0.0)
        m_val = comp.get(elem, 0.0)
        w = weights.get(elem, 1.0)
        dist += w * (m_val - t_val) ** 2
    return round(dist ** 0.5, 4)


def format_composition(comp: dict[str, float]) -> str:
    """Словарь состава -> читаемая строка."""
    parts = [
        f"{elem}: {val:.2f}%"
        for elem, val in sorted(comp.items())
    ]

    return " | ".join(parts)


# ============================================================
# КЛАССИФИКАЦИЯ
# ============================================================

@dataclass(slots=True)
class ClassificationResult:
    material_type: MaterialType
    confidence: float
    reason: str = ''


def classify_material(name: str, comp_norm: dict[str, float], cfg: Config) -> ClassificationResult:
    name_upper = name.upper()

    # 1. Лом/возврат
    if any(kw in name_upper for kw in cfg.SCRAP_KEYWORDS):
        return ClassificationResult(MaterialType.SOURCE, 0.95, 'Лом/возврат')
    main_elem = max(comp_norm, key=comp_norm.get)
    main_percent = comp_norm[main_elem]
    # Значимые элементы (исключая C, P, S)
    significant = sum(
        1 for elem, v in comp_norm.items()
        if v > cfg.MIN_SIGNIFICANT_PERCENT
        and elem not in NON_SIGNIFICANT_ELEMENTS
        and (elem != 'Fe' or main_elem == 'Fe')  # Fe учитываем только если он главный
    )


    # 2. Чистый металл: ≥95% И только один значимый элемент
    if main_percent >= cfg.PURE_MATERIAL_PERCENT and significant <= 1:
        return ClassificationResult(MaterialType.SOURCE, 0.99, f'Чистый: {main_elem}≥95%')

    # 3. Сплав на основе Fe ≥ 85% (не лом/возврат)
    if main_elem == 'Fe' and main_percent >= 85:
        return ClassificationResult(MaterialType.ALLOY, 0.90, f'Сплав на основе Fe: {main_percent}%')

    # 4. Ферросплав
    if significant <= cfg.MAX_SIGNIFICANT_FOR_SOURCE and main_percent >= cfg.FERROALLOY_MAIN_PERCENT:
        return ClassificationResult(MaterialType.SOURCE, 0.85, f'Ферросплав: значимых={significant}')

    # 5. Сложный сплав
    if significant >= 3:
        return ClassificationResult(MaterialType.ALLOY, 0.90, f'Сложный сплав: значимых={significant}')


    # 6. По умолчанию
    return ClassificationResult(MaterialType.ALLOY, 0.70, 'По умолчанию')
# ============================================================
# НОРМАЛИЗАЦИЯ МАТЕРИАЛОВ
# ============================================================

def normalize_materials(
    raw_data: list[dict],
    cfg: Config
) -> list[dict]:
    """
    Подготавливает материалы:
    - парсинг состава
    - нормализация
    - классификация
    - pricing_elements
    """

    materials = []

    for mat in raw_data:

        comp_raw = parse_composition(
            mat.get('ХимСоставНоменклатуры', '')
        )

        if not comp_raw:
            continue

        # ====================================================
        # IGNORE
        # ====================================================

        if 'IGNORE' in comp_raw:
            materials.append({
                'code': mat.get('Код', ''),
                'name': mat.get('НоменклатураНаименование', ''),
                'price': 0.0,
                'comp_raw': comp_raw,
                'comp_norm': comp_raw,
                'material_type': MaterialType.IGNORE,
                'confidence': 1.0,
                'reason': 'IGNORE',
                'pricing_elements': [],
            })

            continue

        # ====================================================
        # NORMAL
        # ====================================================

        comp_norm = normalize_composition(comp_raw)

        name = mat.get('НоменклатураНаименование', '')

        classification = classify_material(
            name,
            comp_norm,
            cfg
        )

        # Ручные overrides
        code = mat.get('Код', '')

        if code in cfg.MANUAL_OVERRIDES:

            override = cfg.MANUAL_OVERRIDES[code]

            if 'material_type' in override:
                classification.material_type = override['material_type']
                classification.confidence = 1.0
                classification.reason = 'Ручное переопределение'

        # Ценообразующие элементы
        pricing_elements = []

        if classification.material_type == MaterialType.SOURCE:

            main_elem = max(comp_norm, key=comp_norm.get)

            if comp_norm[main_elem] >= cfg.MIN_PRICING_PERCENT:
                pricing_elements = [main_elem]

            # override pricing_elements
            if (
                code in cfg.MANUAL_OVERRIDES
                and 'pricing_elements' in cfg.MANUAL_OVERRIDES[code]
            ):
                pricing_elements = cfg.MANUAL_OVERRIDES[code]['pricing_elements']

        materials.append({
            'code': code,
            'name': name,
            'price': safe_float(mat.get('Цена', 0)),
            'comp_raw': comp_raw,
            'comp_norm': comp_norm,
            'material_type': classification.material_type,
            'confidence': classification.confidence,
            'reason': classification.reason,
            'pricing_elements': pricing_elements,
        })

    return materials


def compute_weights(element_prices: dict[str, float]) -> dict[str, float]:
    """
    Вес элемента = цена_элемента / цена_Fe.
    Fe = 1.0, Ni = 1435/19 ≈ 75, Cr = 300/19 ≈ 16.
    Если цены Fe нет — все веса = 1.0.
    """
    fe_price = element_prices.get('Fe', 1.0)
    if fe_price <= 0:
        fe_price = 1.0

    weights = {}
    for elem, price in element_prices.items():
        weights[elem] = price / fe_price
    return weights

# ============================================================
# ИЗВЛЕЧЕНИЕ ЦЕН ЭЛЕМЕНТОВ
# ============================================================

class ElementPriceExtractor:
    """
    Извлекает цены элементов из SOURCE материалов.
    """

    def __init__(self, sources: list[dict]):

        self.estimates: dict[str, list[dict]] = {}
        self.prices: dict[str, float] = {}

        self._extract(sources)

    def _extract(self, sources: list[dict]):

        for m in sources:

            if m['price'] <= 0:
                continue

            for elem in m['pricing_elements']:

                percent = m['comp_norm'].get(elem, 0)

                if percent < 10:
                    continue

                pure_price = m['price'] / (percent / 100.0)

                if elem not in self.estimates:
                    self.estimates[elem] = []

                self.estimates[elem].append({
                    'material': m['name'],
                    'pure_price': round(pure_price, 2),
                    'source_percent': percent,
                    'material_price': m['price'],
                })

        # медиана
        for elem, srcs in self.estimates.items():

            prices = [s['pure_price'] for s in srcs]

            self.prices[elem] = round(
                statistics.median(prices),
                2
            )

    def get_price(self, elem: str) -> Optional[float]:
        return self.prices.get(elem)

    def get_explain(self, elem: str) -> list[dict]:
        return self.estimates.get(elem, [])

    def get_all_prices(self) -> dict[str, float]:
        return self.prices


# ============================================================
# ОСНОВНАЯ ФУНКЦИЯ
# ============================================================

def calc_alloy_price(
    data_mats_prices: list[dict],
    alloy_composition: list[dict],
    analog_threshold:float = 3.0,
    config: Optional[Config] = None
) -> tuple[Optional[float], list[str]]:

    cfg = config or Config()
    if analog_threshold:
        cfg.ANALOG_THRESHOLD = analog_threshold
    # ========================================================
    # ЦЕЛЕВОЙ СОСТАВ
    # ========================================================

    target: dict[str, float] = {}

    for row in alloy_composition:

        elem = row.get('Элемент', '')
        val = row.get('ПроцентСодержания', 0)

        if elem:
            target[elem] = safe_float(val)

    if not target:
        return None, ['Целевой состав отсутствует']

    target = normalize_composition(target)

    # ========================================================
    # МАТЕРИАЛЫ
    # ========================================================

    materials = normalize_materials(
        data_mats_prices,
        cfg
    )

    sources = [
        m for m in materials
        if m['material_type'] == MaterialType.SOURCE
    ]

    alloys = [
        m for m in materials
        if m['material_type'] == MaterialType.ALLOY
    ]
    logger.info("=== КЛАССИФИКАЦИЯ МАТЕРИАЛОВ ===")
    for m in materials:
        logger.info(
            f"  {m['name']}: type={m['material_type'].name}, reason={m['reason']}, pricing={m['pricing_elements']}")

    logger.info(f"  ALLOY: {len([m for m in materials if m['material_type'] == MaterialType.ALLOY])} шт")
    logger.info(f"  SOURCE: {len([m for m in materials if m['material_type'] == MaterialType.SOURCE])} шт")
    logger.info(f"  IGNORE: {len([m for m in materials if m['material_type'] == MaterialType.IGNORE])} шт")
    # ========================================================
    # АНАЛОГИ
    # ========================================================

    # Извлекаем цены элементов из source-материалов
    extractor = ElementPriceExtractor(sources)
    element_prices = extractor.get_all_prices()
    # Считаем веса на основе цен элементов
    weights = compute_weights(element_prices) if element_prices else {}

    # Аналоги — только ALLOY, расстояние взвешенное
    best = None
    if alloys:
        for m in alloys:
            m['distance'] = weighted_euclidean_distance(target, m['comp_norm'], weights)
        alloys.sort(key=lambda x: x['distance'])
        best = alloys[0]

    # ========================================================
    # ОТЧЕТ
    # ========================================================

    report: list[str] = []

    report.append("КАЛЬКУЛЯЦИЯ ЦЕНЫ СПЛАВА")
    report.append("=" * 60)

    report.append(f"Целевой состав: {format_composition(target)}")
    report.append(f"Порог расстояния: {cfg.ANALOG_THRESHOLD}")
    if weights:
        fe_price = element_prices.get('Fe', 1)
        report.append(f"Цена Fe (база весов): {fe_price:.0f} руб/кг")
        weight_parts = [f"{e}:×{w:.0f}" for e, w in sorted(weights.items(), key=lambda x: -x[1]) if w > 1.5]
        if weight_parts:
            report.append(f"Веса: {' | '.join(weight_parts)}")
    report.append("")

    # ========================================================
    # МЕТОД 1
    # ========================================================

    if best is not None:

        exact = [
            m for m in alloys
            if m['distance'] <= 0.0001
        ]

        if exact:

            m = exact[0]

            report.append("[МЕТОД 1] ТОЧНОЕ СОВПАДЕНИЕ")
            report.append(
                f"  Материал: {m['name']} (код: {m['code']})"
            )

            report.append(
                f"  Цена: {m['price']:.2f} руб/кг"
            )

            report.append(
                f"  Состав: {format_composition(m['comp_norm'])}"
            )

            return m['price'], report

    # ========================================================
    # МЕТОД 2
    # ========================================================

    if (
        best is not None
        and best['distance'] <= cfg.ANALOG_THRESHOLD
    ):

        report.append(
            f"[МЕТОД 2] БЛИЖАЙШИЙ АНАЛОГ "
            f"(расстояние = {best['distance']:.4f})"
        )

        report.append(
            f"  Материал: {best['name']} "
            f"(код: {best['code']})"
        )

        report.append(
            f"  Цена: {best['price']:.2f} руб/кг"
        )

        report.append(
            f"  Состав: {format_composition(best['comp_norm'])}"
        )

        report.append("")
        report.append("Топ-5 ближайших:")

        for i, m in enumerate(alloys[:5]):

            marker = " <- ВЫБРАН" if i == 0 else ""

            report.append(
                f"  {i + 1}. {m['name']} | "
                f"расст={m['distance']:.4f} | "
                f"цена={m['price']:.2f}{marker}"
            )

        return best['price'], report

    # ========================================================
    # МЕТОД 3
    # ========================================================

    report.append("[МЕТОД 3] РАСЧЕТ ЧЕРЕЗ ЭЛЕМЕНТЫ")

    if best is not None:

        report.append(
            f"  Ближайший аналог превысил порог расстояния: "
            f"{best['name']} "
            f"(расст={best['distance']:.4f} > "
            f"{cfg.ANALOG_THRESHOLD})"
        )

        report.append(
            f"  Его цена, справочно: "
            f"{best['price']:.2f} руб/кг"
        )

    else:
        report.append("  Аналогов в базе нет")

    report.append("")

    # ========================================================
    # ЦЕНЫ ЭЛЕМЕНТОВ
    # ========================================================



    report.append("Источники цен элементов:")

    for elem in sorted(element_prices.keys()):

        src_list = extractor.get_explain(elem)

        if src_list:

            bs = src_list[0]

            report.append(
                f"  {elem}: "
                f"{element_prices[elem]:.2f} "
                f"<- {bs['material']} "
                f"({bs['source_percent']:.1f}%)"
            )

        else:

            report.append(
                f"  {elem}: "
                f"{element_prices[elem]:.2f} "
                f"<- нет источника"
            )

    report.append("")

    # ========================================================
    # РАСЧЕТ ЦЕНЫ
    # ========================================================

    calculated_price = 0.0

    breakdown = []
    missing = []

    for elem, percent in sorted(
        target.items(),
        key=lambda x: -x[1]
    ):

        if elem in element_prices:

            cost = (
                (percent / 100.0)
                * element_prices[elem]
            )

            calculated_price += cost

            breakdown.append(
                f"  {elem:4s}: "
                f"{percent:6.2f}% x "
                f"{element_prices[elem]:8.2f} = "
                f"{cost:8.2f} руб"
            )

        else:
            missing.append(elem)

    report.append("Разбор цены по элементам:")

    report.extend(breakdown)

    if missing:
        report.append(
            f"  ! Нет цены для: {', '.join(missing)}"
        )

    report.append("  " + "-" * 40)

    report.append(
        f"  ИТОГО: "
        f"{calculated_price:29.2f} руб/кг"
    )

    report.append("")

    # ========================================================
    # СРАВНЕНИЕ С АНАЛОГОМ
    # ========================================================

    if best is not None and best['price'] > 0:

        diff = calculated_price - best['price']
        str_diff = 'НИЖЕ'
        if diff > 0:
            str_diff = 'ВЫШЕ'

        report.append(
            f"  + Расчетная цена {str_diff} ближайшего аналога "
            f"({best['name']}) "
            f"на {abs(diff):.2f} руб/кг"
        )

    # ========================================================
    # TOP-5
    # ========================================================

    if alloys:

        report.append("")
        report.append("Топ-5 ближайших (справочно):")

        for i, m in enumerate(alloys[:5]):

            report.append(
                f"  {i + 1}. {m['name']} | "
                f"расст={m['distance']:.4f} | "
                f"цена={m['price']:.2f}"
            )

    return round(calculated_price, 2), report