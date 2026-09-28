import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_mes as CMS
import project_cust_38.Cust_SQLite as CSQ
PRJCT = CMS.CFG.Config.project

class FileDXF(CMS._ImportDb):

    def __init__(self,pathf_or_dict:str|None=None):
        """naryad_composit_files"
        "naryad_composit_parts_dse"""
        self.id: int | None = None
        self.id_dse: int | None = None
        self.name: str | None = None
        self.count: int | None = None
        self._dirty: bool = False

        if isinstance(pathf_or_dict,str):
            path_o: F.Cust_path = F.Cust_path(pathf_or_dict)
            self.name:str = path_o.name
            self.count:int|None = None
            self.calc_count()
            self._dirty = True

        if isinstance(pathf_or_dict,dict):
            self.parce_row_dict(pathf_or_dict)

    def save_db(self)->bool:
        if not self._dirty:
            return True

        if self.id:
            upd_dict = {'id': self.id,
             'id_dse': self.id_dse,
             'name': self.name,
             'count': self.count}

            rez = CSQ.custom_request_c(PRJCT.db_naryad,f"""UPDATE naryad_composit_parts_files SET 
                            ({', '.join(upd_dict.keys())})
                        = ({CSQ.questions_for_mask(list(upd_dict.values()))})
                                WHERE id = {self.id} ;""",list_of_lists_c=[list(upd_dict.values())])
            if not rez:
                return False
            self._dirty = False
            return True
        else:
            ins_dict = {
                        'id_dse': self.id_dse,
                        'name': self.name,
                        'count': self.count}

            rez = CSQ.custom_request_c(PRJCT.db_naryad, f"""INSERT INTO 
                        naryad_composit_parts_files ({', '.join(ins_dict.keys())})
                                            VALUES ({CSQ.questions_for_mask(list(ins_dict.values()))}) RETURNING id ;""",
                                       list_of_lists_c=[list(ins_dict.values())],rez_dict=True,one=True)
            if not rez:
                return False
            if rez:
                self.id = rez['id']
            self._dirty = False
            return True


    def set_count(self,value:int|None=None):
        self.count = value
        self._dirty = True

    def calc_count(self):
        if 'шт' not in self.name:
            return
        str_count = self.name.split('шт')[0].split(' ')[-1]
        if F.is_numeric(str_count):
            self.count = int(str_count)

    def check_to_serialize(self)->tuple[bool,list[dict]]:
        if self.count is None or not self.count:
            return False,[{'err':f'{self.name} - Количество не определено'}]
        return True,[]

    def set_dirty(self):
        self._dirty = True

class  ConnectionDSE(CMS._ImportDb):
    ALIASES = {
        'id':'_id',
        'name':'Наименование',
        'nn':'НН',
        'izdel':'Изделие',
        'link_to_docs_object':'Docs ссылка',
        'erp_code':'Код ERP',
        'raw_dir':'Путь до файлов',
        'raw_dir_nn':'_raw_dir_nn',
        'raw_dir_name':'_raw_dir_name',
    }
    def __init__(self):
        self.id:int|None = None
        self.name:str|None = None
        self.nn:str|None = None
        self.izdel:str|None = None
        self.link_to_docs_object:str|None = None
        self.erp_code:str|None = None
        self.raw_dir:str|None = None
        self.raw_dir_nn:str|None = None
        self.raw_dir_name:str|None = None

        self.files_dxf:dict[int,FileDXF] = dict()
        self._dirty:bool = False


    @property
    def raw_dir_str(self)->str:
        if self.raw_dir_nn is None:
            return ''
        if self.raw_dir_name is None:
            return ''
        return f'{self.raw_dir_nn} {self.raw_dir_name}'
    @classmethod
    def from_db(cls,item:dict,list_files:list[dict])->'ConnectionDSE':
        conn_o = cls()
        conn_o.parce_row_dict(item)

        for it in list_files:
            file_dxf = FileDXF(it)
            conn_o.add_file(file_dxf)
        return conn_o

    def template(self)->dict:
        dict_attrs = F.get_all_attrs(self)
        row = {'':CMS.CEMOJ.ОперацииПроизводства.dse.symbol}
        row.update({k:v for k,v in dict_attrs.items() if k not in ['files_dxf','_dirty']})
        return row
    def save_db(self)->tuple[bool,list[dict]]:

        if self._dirty:

            fl_new = False

            if self.id:
                upd_dict = {
                'id':self.id,
                'name':self.name,
                'nn':self.nn,
                'izdel':self.izdel,
                'link_to_docs_object':self.link_to_docs_object,
                'erp_code':self.erp_code,
                'raw_dir':self.raw_dir,
                'raw_dir_nn':self.raw_dir_nn,
                'raw_dir_name':self.raw_dir_name,
                }

                rez = CSQ.custom_request_c(PRJCT.db_naryad, f"""UPDATE naryad_composit_parts_dse SET 
                                ({', '.join(upd_dict.keys())})
                            = ({CSQ.questions_for_mask(list(upd_dict.values()))})
                                    WHERE id = {self.id} ;""", list_of_lists_c=[list(upd_dict.values())])
                if not rez:
                    return False , [{'err':f'Ошибка сохранения в БД'}]

            else:
                ins_dict = {
                'name':self.name,
                'nn':self.nn,
                'izdel':self.izdel,
                'link_to_docs_object':self.link_to_docs_object,
                'erp_code':self.erp_code,
                'raw_dir':self.raw_dir,
                'raw_dir_nn':self.raw_dir_nn,
                'raw_dir_name':self.raw_dir_name,
                }

                rez = CSQ.custom_request_c(PRJCT.db_naryad, f"""INSERT INTO 
                            naryad_composit_parts_dse ({', '.join(ins_dict.keys())})
                                                VALUES ({CSQ.questions_for_mask(list(ins_dict.values()))}) RETURNING id ;""",
                                           list_of_lists_c=[list(ins_dict.values())], rez_dict=True, one=True)
                if not rez:

                    return False , [{'err':f'Ошибка сохранения в БД'}]
                if rez:
                    self.id = rez['id']
                for file_dxf in self.files_dxf.values():
                    file_dxf.id_dse = self.id
                fl_new = True


        for file_dxf in self.files_dxf.values():
            rez = file_dxf.save_db()
            if not rez:
                if fl_new:
                    self._rollback()
                return False,[{'err':f'{file_dxf.name} - ошибка сохранения в БД'}]

        self._dirty = False
        return True, []

    def _rollback(self):
        CSQ.custom_request_c(PRJCT.db_naryad, f"""DELETE FROM naryad_composit_parts_dse WHERE id = {self.id} ;""")
        self._delete_all_files_db()
        self._dirty = True

    def _delete_all_files_db(self):
        CSQ.custom_request_c(PRJCT.db_naryad, f"""DELETE FROM naryad_composit_parts_files WHERE id_dse = {self.id} ;""")
        [_.set_dirty() for _ in self.files_dxf.values()]

    def check_to_serialize(self)->tuple[bool,list[dict]]:
        if self.raw_dir is None:
            return False,[{'err':f'Не указан каталог для DXF'}]
        if self.name is None:
            return False,[{'err':f'Не выбраны ДСЕ'}]
        errs_files = []
        for file_dxf in self.files_dxf.values():
            suc ,errs = file_dxf.check_to_serialize()
            if not suc:
                errs_files.extend(errs)
        if errs_files:
            return False, errs_files
        if CSQ.custom_request_c(PRJCT.db_naryad, f"""SELECT name , nn FROM naryad_composit_parts_dse 
            WHERE name = '{self.name}' AND nn = '{self.nn}';""",rez_dict=True,one=True):
            return False, [{'err': f'ДСЕ с таким именем и номером уже зарегистрирована ранее'}]

        return  True,[]

    def clear_dse(self):
        self.name = None
        self.nn = None
        self.izdel = None
        self.link_to_docs_object = None
        self.erp_code = None
        self._dirty = True
    def add_dse(self,name:str,nn:str,izdel:str,link_to_docs_object:str,erp_code:str):
        self.name = name
        self.nn = nn
        self.izdel = izdel
        self.link_to_docs_object = link_to_docs_object
        self.erp_code = erp_code
        self._dirty = True
    def _clear_raw_dir_name(self):
        self.raw_dir = None
        self.raw_dir_nn = None
        self.raw_dir_name = None
        self._dirty = True
    def add_raw_dir_name(self,pathd:str)->tuple[bool,str]:
        path_o = F.Cust_path(pathd)
        name = path_o.name
        self.raw_dir = None
        self.raw_dir_nn = None
        self.raw_dir_name = None
        if ' ' not in name:
            return False, 'Имя папки не содержит пробелов'
        list_words = name.split(' ')
        if '.' in list_words[0]:
            self.raw_dir_nn = list_words[0]
            self.raw_dir_name = ' '.join(list_words[1:])
        if '.' in list_words[-1]:
            self.raw_dir_nn = list_words[-1]
            self.raw_dir_name = ' '.join(list_words[:-1])

        if self.raw_dir_nn is None:
            return False, 'Имя папки не содержит точек в начале или конце'
        self.raw_dir = str(path_o)
        self._dirty = True
        return True, ''

    def clear_dir_selected(self):
        self._files_reset()
        self._clear_raw_dir_name()

    def _files_reset(self):
        self.files_dxf:dict[int,FileDXF] = dict()
        self._dirty = True
    def add_file(self,file_o:FileDXF):
        id = 0
        if self.files_dxf:
            id = max(self.files_dxf.keys())+1
        self.files_dxf[id] = file_o
        file_o.id_dse = self.id

    def get_template_files_edit(self):
        return  [{'_id':id, 'Количество':_.count if _.count else '','Название':_.name} for id,_ in self.files_dxf.items()]


    def __repr__(self):
        return f"ConnectionDSE(name='{self.name}', nn='{self.nn}', izdel='{self.izdel}')"

    def __str__(self):
        return f"'{self.name}' '{self.nn}'"

class ConnectionsDSE():
    def __init__(self):
        self.dict_dst:dict[tuple[str,str],ConnectionDSE] = dict()

    def load_from_db(self):
        self.dict_dst = dict()
        data  = CSQ.custom_request_c(PRJCT.db_naryad,f"SELECT * FROM naryad_composit_parts_dse",rez_dict=True)
        data_files =  CSQ.custom_request_c(PRJCT.db_naryad,f"SELECT * FROM naryad_composit_parts_files",rez_dict=True)
        for item in data:
            conn_o = ConnectionDSE.from_db(item,[_ for _ in data_files if _['id_dse'] == item['id']])
            self.dict_dst[(conn_o.nn,conn_o.name)] = conn_o

    def find(self,id:int)->ConnectionDSE|None:
        for conn in self.dict_dst.values():
            if conn.id == id:
                return conn
    def template(self)->list[dict]:
        return [_.template() for _ in self.dict_dst.values()]