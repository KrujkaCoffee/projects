from dataclasses import dataclass
from typing import ClassVar, Dict, Optional, Any
import inspect


@dataclass(frozen=True)
class EmojiItem:
    """Класс для хранения информации об emoji"""
    symbol: str
    name: str
    category: str
    description: str

    def __str__(self) -> str:
        return self.symbol

    def __repr__(self) -> str:
        return f"EmojiItem('{self.symbol}', '{self.name}', '{self.category}', '{self.description}')"


class СтатусыПроизводства:
    """Категория статусов производства"""

    success: ClassVar[EmojiItem] = EmojiItem('✅', 'success', 'status', 'Успешное выполнение')
    checked: ClassVar[EmojiItem] = EmojiItem('☑️', 'checked', 'status', 'Отмечено')
    error: ClassVar[EmojiItem] = EmojiItem('❌', 'error', 'status', 'Ошибка или сбой')
    warning: ClassVar[EmojiItem] = EmojiItem('⚠️', 'warning', 'status', 'Предупреждение')
    info: ClassVar[EmojiItem] = EmojiItem('ℹ️', 'info', 'status', 'Информация')
    progress: ClassVar[EmojiItem] = EmojiItem('⏳', 'progress', 'status', 'В процессе выполнения')
    completed: ClassVar[EmojiItem] = EmojiItem('🎯', 'completed', 'status', 'Завершено')
    running: ClassVar[EmojiItem] = EmojiItem('🟢', 'running', 'status', 'Система работает')
    selected: ClassVar[EmojiItem] = EmojiItem('🔘', 'selected', 'status', 'Выбрано')
    uncertain: ClassVar[EmojiItem] = EmojiItem('🟠', 'uncertain', 'status', 'Неустойчивое состояние')
    stopped: ClassVar[EmojiItem] = EmojiItem('🔴', 'stopped', 'status', 'Система остановлена')
    idle: ClassVar[EmojiItem] = EmojiItem('🟡', 'idle', 'status', 'Ожидание')
    alert: ClassVar[EmojiItem] = EmojiItem('🚨', 'alert', 'status', 'Тревога')
    normal: ClassVar[EmojiItem] = EmojiItem('🟢', 'normal', 'status', 'Нормальный режим')
    ellipsis: ClassVar[EmojiItem] = EmojiItem('…', 'ellipsis', 'menu', 'Ещё / Дополнительно')
    vert_ellipsis: ClassVar[EmojiItem] = EmojiItem('⁞', 'vertEllipsis', 'menu', 'Ещё / Дополнительно')

class ОперацииПроизводства:
    """Категория производственных операций"""

    production: ClassVar[EmojiItem] = EmojiItem('🏭', 'production', 'operations', 'Производство')
    assembly: ClassVar[EmojiItem] = EmojiItem('🔧', 'assembly', 'operations', 'Сборка')
    quality: ClassVar[EmojiItem] = EmojiItem('📐', 'quality', 'operations', 'Контроль качества')
    packaging: ClassVar[EmojiItem] = EmojiItem('📦', 'packaging', 'operations', 'Упаковка')
    shipping: ClassVar[EmojiItem] = EmojiItem('🚚', 'shipping', 'operations', 'Отгрузка')
    maintenance: ClassVar[EmojiItem] = EmojiItem('🛠️', 'maintenance', 'operations', 'Техобслуживание')
    dse: ClassVar[EmojiItem] = EmojiItem('🔩', 'dse', 'operations', 'Деталь или материал')
    res: ClassVar[EmojiItem] = EmojiItem('📘', 'res', 'operations', 'Ресурсная спецификация')
    trd: ClassVar[EmojiItem] = EmojiItem('⏱️', 'trd', 'operations', 'Трудозатраты')


class ПоказателиМетрики:
    """Категория показателей и метрик"""

    kpi: ClassVar[EmojiItem] = EmojiItem('📊', 'kpi', 'metrics', 'KPI показатели')
    efficiency: ClassVar[EmojiItem] = EmojiItem('📈', 'efficiency', 'metrics', 'Эффективность')
    downtime: ClassVar[EmojiItem] = EmojiItem('📉', 'downtime', 'metrics', 'Простой оборудования')
    target: ClassVar[EmojiItem] = EmojiItem('🎯', 'target', 'metrics', 'Целевой показатель')
    deadline: ClassVar[EmojiItem] = EmojiItem('⏰', 'deadline', 'metrics', 'Срок выполнения')


class ОборудованиеИнструменты:
    """Категория оборудования и инструментов"""

    machine: ClassVar[EmojiItem] = EmojiItem('⚙️', 'machine', 'equipment', 'Оборудование')
    robot: ClassVar[EmojiItem] = EmojiItem('🤖', 'robot', 'equipment', 'Робот/автоматизация')
    sensor: ClassVar[EmojiItem] = EmojiItem('📡', 'sensor', 'equipment', 'Датчик')
    tool: ClassVar[EmojiItem] = EmojiItem('🛠️', 'tool', 'equipment', 'Инструмент')
    conveyor: ClassVar[EmojiItem] = EmojiItem('📦', 'conveyor', 'equipment', 'Конвейер')
    lock: ClassVar[EmojiItem] = EmojiItem('🔒', 'lock', 'control', 'Замок')

class ПерсоналРоли:
    """Категория персонала и ролей"""

    operator: ClassVar[EmojiItem] = EmojiItem('👨‍💼', 'operator', 'personnel', 'Оператор')
    engineer: ClassVar[EmojiItem] = EmojiItem('👨‍🔧', 'engineer', 'personnel', 'Инженер')
    supervisor: ClassVar[EmojiItem] = EmojiItem('👔', 'supervisor', 'personnel', 'Руководитель')
    team: ClassVar[EmojiItem] = EmojiItem('👥', 'team', 'personnel', 'Команда')
    training: ClassVar[EmojiItem] = EmojiItem('🎓', 'training', 'personnel', 'Обучение')


class ДокументыДанные:
    """Категория документов и данных"""
    document: ClassVar[EmojiItem] = EmojiItem('📄', 'document', 'documents', 'Документ')
    soon: ClassVar[EmojiItem] = EmojiItem('🔜', 'soon', 'documents', 'Скоро')
    folder: ClassVar[EmojiItem] = EmojiItem('📂', 'folder', 'documents', 'Папка')
    folder_closed: ClassVar[EmojiItem] = EmojiItem('📁', 'folder_closed', 'documents', 'Закрытая папка')
    folder_group: ClassVar[EmojiItem] = EmojiItem('🗂', 'folder_group', 'documents', 'Закрытая папка')
    report: ClassVar[EmojiItem] = EmojiItem('📋', 'report', 'documents', 'Отчет')
    database: ClassVar[EmojiItem] = EmojiItem('🗄️', 'database', 'documents', 'База данных')
    analysis: ClassVar[EmojiItem] = EmojiItem('📊', 'analysis', 'documents', 'Анализ данных')
    archive: ClassVar[EmojiItem] = EmojiItem('🗃️', 'archive', 'documents', 'Архив')
    expand: ClassVar[EmojiItem] = EmojiItem('🔽', 'expand', 'documents', 'Развернуть')
    collapse: ClassVar[EmojiItem] = EmojiItem('▶️', 'collapse', 'documents', 'Свернуть')
    refresh: ClassVar[EmojiItem] = EmojiItem('🔄', 'refresh', 'operations', 'Обновить / Пересчитать')
    plus: ClassVar[EmojiItem] = EmojiItem('➕', 'plus', 'documents', 'Развернуть')
    plus_circled: ClassVar[EmojiItem] = EmojiItem('⊕︎', 'plus_circled', 'documents', 'Развернуть')
    plus_squared: ClassVar[EmojiItem] = EmojiItem('⊞', 'plus_squared', 'documents', 'Развернуть')
    minus: ClassVar[EmojiItem] = EmojiItem('➖', 'minus', 'documents', 'Свернуть')
    minus_circled: ClassVar[EmojiItem] = EmojiItem('⊖︎', 'minus_circled', 'documents', 'Свернуть')
    minus_squared: ClassVar[EmojiItem] = EmojiItem('⊟', 'minus_squared', 'documents', 'Свернуть')
    pencil: ClassVar[EmojiItem] = EmojiItem('✏️', 'pencil', 'documents', 'Изменяемый')
    pencil2: ClassVar[EmojiItem] = EmojiItem('🖉', 'pencil2', 'documents', 'Изменяемый2')
    pencil2: ClassVar[EmojiItem] = EmojiItem('🖉', 'pencil2', 'documents', 'Изменяемый2')
    pencil_note: ClassVar[EmojiItem] = EmojiItem('📝', 'pencil_note', 'documents', 'Редактирование')

class EmojiMain:
    """
    Главный класс для работы с emoji в ERP/MES системах
    Использует статические классы для полных хинтов в PyCharm
    """

    # Прямой доступ к категориям как к классам
    Статусы = СтатусыПроизводства
    Операции = ОперацииПроизводства
    Метрики = ПоказателиМетрики
    Оборудование = ОборудованиеИнструменты
    Персонал = ПерсоналРоли
    Документы = ДокументыДанные

    # Полные имена для обратной совместимости
    СтатусыПроизводства = СтатусыПроизводства
    ОперацииПроизводства = ОперацииПроизводства
    ПоказателиМетрики = ПоказателиМетрики
    ОборудованиеИнструменты = ОборудованиеИнструменты
    ПерсоналРоли = ПерсоналРоли
    ДокументыДанные = ДокументыДанные

    # Словарь для динамического доступа
    _all_emoji: ClassVar[Dict[str, EmojiItem]] = {}

    @classmethod
    def _initialize(cls):
        """Инициализация словаря всех emoji"""
        if cls._all_emoji:
            return

        categories = [
            СтатусыПроизводства, ОперацииПроизводства, ПоказателиМетрики,
            ОборудованиеИнструменты, ПерсоналРоли, ДокументыДанные
        ]

        for category in categories:
            for attr_name in dir(category):
                if not attr_name.startswith('_'):
                    attr = getattr(category, attr_name)
                    if isinstance(attr, EmojiItem):
                        cls._all_emoji[attr_name] = attr

    @classmethod
    def get(cls, name: str, default: Optional[str] = None) -> str:
        """Получить emoji по названию"""
        cls._initialize()
        emoji_item = cls._all_emoji.get(name.lower())
        if emoji_item:
            return str(emoji_item)
        return default if default is not None else ''

    @classmethod
    def get_info(cls, name: str) -> Optional[EmojiItem]:
        """Получить полную информацию об emoji"""
        cls._initialize()
        return cls._all_emoji.get(name.lower())

    @classmethod
    def list_all(cls) -> Dict[str, EmojiItem]:
        """Получить все emoji"""
        cls._initialize()
        return cls._all_emoji.copy()


# Инициализируем при импорте
EmojiMain._initialize()

# Примеры использования
if __name__ == "__main__":
    # Теперь PyCharm будет показывать хинты!
    msg1 = f"Производственная линия {EmojiMain.Статусы.running} работает нормально"
    msg2 = f"Обнаружена {EmojiMain.Статусы.error} ошибка в системе"
    msg3 = f"{EmojiMain.Операции.assembly} Сборка продукта завершена {EmojiMain.Статусы.success}"
    msg4 = f"{EmojiMain.Персонал.operator} Оператор сообщает о {EmojiMain.Оборудование.machine} поломке оборудования"

    print(msg1)
    print(msg2)
    print(msg3)
    print(msg4)

    # Также доступны полные имена
    msg5 = f"KPI: {EmojiMain.ПоказателиМетрики.kpi} показатели в норме {EmojiMain.СтатусыПроизводства.normal}"
    msg6 = f"{EmojiMain.ОборудованиеИнструменты.robot} Автоматизация процесса {EmojiMain.Статусы.completed}"

    print(msg5)
    print(msg6)

    # Динамический доступ
    error_emoji = EmojiMain.get_info('error')
    print(f"\nИнформация об emoji ошибки: {error_emoji}")
    print(f"Описание: {error_emoji.description}")