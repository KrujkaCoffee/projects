class SingletonMeta(type):
    __instances = {}

    def __call__(cls, *args, **kwargs):

        if getattr(cls, "_singleton", True) is False: # если помечен _singleton = False  то не синглтон)
            return super().__call__(*args, **kwargs)
        if cls not in cls.__instances:
            instance = super().__call__(*args, **kwargs)
            cls.__instances[cls] = instance
        return cls.__instances[cls]

    @classmethod
    def clear_instance(mcs, cls):
        """Удаляет сохранённый экземпляр класса"""
        if cls in mcs.__instances:
            del mcs.__instances[cls]

class DictForResource:
    # etaps = CSQ.custom_request_c(db_users,
    #                              f"""SELECT etaps.name as etaps_name, rab_c."Код" , rab_c."Имя" FROM rab_c 
    #         INNER JOIN etaps ON 
    #         etaps.s_num = rab_c.etaps_num 
    #         WHERE rab_c.poki = {poki}""",
    #                              attach_dbs=db_naryad, rez_dict=True)
    # dict_etaps = F.deploy_dict_c(etaps, 'Код')

    # F.deploy_dict_c(
    #     CSQ.custom_request_c(CFG.Config.project.db_users,
    #                          """SELECT *
    #                             FROM professions
    #                                      LEFT JOIN vid_rab_po_dolg
    #                                                ON professions.вид_работ = vid_rab_po_dolg.Вид_работ""",
    #                          rez_dict=True),
    #     'код')
    
    def __init__(self,
            DICT_ETAPS_RC_BY_CODE:dict,
            DICT_PROF_BY_CODE:dict,
           
    ):
        self.DICT_ETAPS_RC_BY_CODE = DICT_ETAPS_RC_BY_CODE
        self.DICT_PROF_BY_CODE = DICT_PROF_BY_CODE
    
    
      
class DictForMarshrutCard:
    # etaps = CSQ.custom_request_c(db_users,
    #                              f"""SELECT etaps.name as etaps_name, rab_c."Код" , rab_c."Имя" FROM rab_c 
    #         INNER JOIN etaps ON 
    #         etaps.s_num = rab_c.etaps_num 
    #         WHERE rab_c.poki = {poki}""",
    #                              attach_dbs=db_naryad, rez_dict=True)
    # dict_etaps = F.deploy_dict_c(etaps, 'Код')
    
    def __init__(self,
            DICT_ETAPS_RC_BY_CODE:dict,
           
    ):
        self.DICT_ETAPS_RC_BY_CODE = DICT_ETAPS_RC_BY_CODE

    
class DictForNaryad:
    def __init__(self,
            DICT_DOLGN_ETAP:dict,
            DICT_OPERS:dict,
            DICT_EMPL:dict,
            DICT_DATA_DOLGN_ETAP:dict,
    ):
        self.DICT_DOLGN_ETAP = DICT_DOLGN_ETAP
        self.DICT_OPERS = DICT_OPERS
        self.DICT_EMPL = DICT_EMPL
        self.DICT_DATA_DOLGN_ETAP = DICT_DATA_DOLGN_ETAP

    def __repr__(self):
        return f"""DictForNaryad(dict_dolgn_etap={'Loaded' if self.DICT_DOLGN_ETAP is not None else 'None'},dict_opers={'Loaded' if self.DICT_OPERS is not None else 'None'}, dict_empl={'Loaded' if self.DICT_EMPL is not None else 'None'}, dict_data_dolgn_etap={'Loaded' if self.DICT_DATA_DOLGN_ETAP is not None else 'None'})"""

class Packs(metaclass=SingletonMeta):
    DATA_NARYAD_PACK:DictForNaryad|None = None
    DATA_MK_PACK:DictForMarshrutCard|None = None
    DATA_RS_PACK:DictForResource|None = None
