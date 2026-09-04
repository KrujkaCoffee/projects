from project_cust_38 import Cust_Functions as F


class PageManager:
    """Менеджер постраничного просмотра в таблице"""

    def __init__(self, page_size: int = 100) -> None:
        page_size = F.valm(page_size)
        if page_size <= 0:
            raise ValueError("некорректно значение page_Size")

        self.page_size = page_size
        self.current_page = 1
        self.total_count = 0

        self.data = []
        self.user_data = None
        self.list_has_head = False

    @property
    def count_pages(self) -> int:
        if self.total_count == 0: return 0
        return (
                self.total_count + self.page_size - 1
        ) // self.page_size

    @property
    def shown_page(self):
        if self.total_count == 0: return 0
        return self.current_page

    @property
    def can_go_back(self):
        return False

    @property
    def can_go_forward(self):
        return False

    def set_data(self, data, user_data: typing.Any = None):
        ...

    def __validate_user_data(self):
        ...

    def bounds(self):
        ...

    def slice_data(self, data):
        ...

    def page_data(self):
        ...

    def first(self):
        ...

    def previous(self):
        ...

    def next(self):
        ...

    def last(self):
        ...

    def __set_current_page(self):
        ...