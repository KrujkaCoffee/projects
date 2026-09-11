import typing
from collections import UserString



class _ServerItem(UserString):
    alias: str                                  # "Naryad.db"
    absolute_path: str                          # "C://DB_srv//Naryad.db"
    port: typing.Union[int, str, None] = None   # 20002

    def __init__(self, alias: str, absolute_path: str = '', port: typing.Union[int, str, None] = None):
        super().__init__(f'SRV:{alias}')
        self.alias = alias
        self.absolute_path = absolute_path
        self.port = port
        self.attribute_name = None


class _ClassDict(type):
    def __init__(cls, name, bases, dct):
        super().__init__(name, bases, dct)
        if "__annotations__" in dct:
            annotations = dct["__annotations__"]
        else :
            import annotationlib
            annotate = annotationlib.get_annotate_from_class_namespace(dct)
            annotationlib.get_annotate_from_class_namespace(dct)
            annotations = annotationlib.call_annotate_function(
                annotate,
                format=annotationlib.Format.STRING,
            )
        cls._declared_attrs = {
            k: dct.get(k)
            for k in annotations
        }
        cls.__by_alias = {}
        cls.__iter = []
        cls.__by_name = {}
        for name, attr in cls._declared_attrs.items():
            if isinstance(attr, _ServerItem):
                cls.__by_alias[attr.alias] = attr
                cls.__iter.append(attr)
                attr.attribute_name = name
            cls.__by_name[name] = attr

    def __getitem__(cls, item):
        return cls.__by_alias.get(item) or cls.__by_name.get(item)

    def __iter__(self) -> typing.Iterator[_ServerItem]:
        return iter(self.__iter)

