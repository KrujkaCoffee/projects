from __future__ import annotations
import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_mes as CMS
import project_cust_38.Cust_SQLite as CSQ
from project_cust_38 import Cust_config as CFG
from docxtpl import DocxTemplate
from pathlib import Path
from typing import TYPE_CHECKING
import classes as CLSS
if TYPE_CHECKING:
    from vipoln import mywindow

class PathValidator():
    def __init__(self, raw_path: str):
        self.raw_path = raw_path
        self._path = None
        self._normalize()
        self._ensure_dirs()
    @property
    def path(self):
        return str(self._path)
    def _normalize(self):
        if not isinstance(self.raw_path, str):
            raise TypeError("Путь должен быть строкой")

        cleaned = self.raw_path.strip().strip('"').strip("'")
        if not cleaned:
            raise ValueError("Пустой путь")

        self._path = Path(cleaned)

        root = Path(self._path.anchor)
        if not root.exists():
            raise FileNotFoundError(f"Корневой путь не существует: {root}")

        return self

    def exists(self) -> bool:
        self._ensure_normalized()
        return self._path.exists()

    def is_file(self) -> bool:
        self._ensure_normalized()
        return self._path.is_file()

    def is_dir(self) -> bool:
        self._ensure_normalized()
        return self._path.is_dir()

    def validate(self, expect: str | None = None) -> bool:
        self._ensure_normalized()

        if not self._path.exists():
            return False

        if expect == "file" and not self._path.is_file():
            return False

        if expect == "dir" and not self._path.is_dir():
            return False

        return True

    def _ensure_normalized(self):
        if self._path is None:
            raise RuntimeError("Сначала вызови normalize()")

    def _ensure_dirs(self):
        self._ensure_normalized()

        p = self._path

        root = Path(p.anchor)
        if not root.exists():
            raise FileNotFoundError(f"Корневой путь не существует: {root}")

        # если есть расширение — считаем, что это файл
        if p.suffix:
            target_dir = p.parent
        else:
            target_dir = p

        if target_dir == root:
            return

        if not target_dir.exists():
            target_dir.mkdir(parents=True, exist_ok=True)

class InterDoc():
    _name_template_file = None
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls._name_template_file is None:
            raise TypeError(
                f"{cls.__name__} обязан определить _name_template_file"
            )
    def __init__(self,path:str,name_new_file):
        self._name_new_file:str = name_new_file
        if F.sep() in name_new_file or '.' not in name_new_file:
            raise ValueError(f'Не корректное имя файла')
        self._path:PathValidator = PathValidator(path)

    def toDict(self):
        res = {}
        for attr,val in F.get_all_attrs_with_properties(self).items():
            res[attr] = val
        return res

class InterNaryad(InterDoc):
    _name_template_file = 'NaryadDescr_templ.docx'
    def __init__(self,path,name_new_file,
                        nom_nar,
                         sozdan,
                         proj,
                         zp,
                         vrem,
                         mk,
                         fio,
                         fio2,
                         zadanie):
        super().__init__(path=path, name_new_file=name_new_file)

        self.nom_nar: int | str | None = nom_nar
        self.sozdan: None | str = sozdan
        self.proj: None | str = proj
        self.zp: None | str = zp
        self.vrem: None | str = vrem
        self.mk: None | str = mk
        self.fio: None | str = fio
        self.fio2: None | str = fio2
        self.zadanie: None | str = zadanie

class DocEngine():
    DIR_TEMPLATES = f'docs'
    def __init__(self,handle:InterNaryad):
        self.handle = handle
        self.obj = DocxTemplate(F.sep().join((self.DIR_TEMPLATES, self.handle._name_template_file)))
        self.pathf = F.sep().join((self.handle._path.path,self.handle._name_new_file))
    def generate(self):
        self.obj.render(self.handle.toDict())
        self.obj.save(self.pathf)

    def open(self):
        if F.existence_file_c(self.pathf):
            F.run_file_c(self.pathf,proverka=False)
        else:
            print(f'File {self.pathf} not found')
def print_out_naryad(nar_info:CLSS.Naryad_info):
    name = f'Наряд {nar_info.nom_nar}.docx'

    doc = DocEngine(InterNaryad(F.tmp_dir_win(),name,
                                nom_nar=nar_info.nom_nar,
                                sozdan=nar_info.sozdan,
                                proj=nar_info.proj,
                                zp=nar_info.zp,
                                vrem=nar_info.vrem,
                                mk=nar_info.mk,
                                fio=nar_info.fio,
                                fio2=nar_info.fio2,
                                zadanie=nar_info.zadanie
                                ))
    if F.existence_file_c(doc.pathf): # 03.03.2026
        if CQT.msgboxgYN('Наряд уже был распечатан ранее. Обновить?'):
            try:
                doc.generate()
            except PermissionError as e:
                return CQT.msgbox('Ошибка. Документ, который вы хотите перезаписать открыт. \nЗапись невозможна!')
    else:
        doc.generate()
    doc.open()


