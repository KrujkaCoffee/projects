import typing



class WorkerInfo:
    def __init__(self, data):
        self.__data = data

    def naryads_by_code(self, code):
        code = int(code)
        for item in self.__data:
            tr_code = item['']

    @classmethod
    def make_worker_info(
            cls,
            list_fio: typing.Iterable[str],
            start_period: str,
            end_period: str
    ) -> tuple["WorkerInfo"]:
        ...