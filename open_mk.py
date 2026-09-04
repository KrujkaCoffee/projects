from project_cust_38 import Cust_SQLite as CSQ
from project_cust_38 import Cust_config as CFG


u = CSQ.custom_request_c(CFG.Config.project.db_naryad, 'UPDATE mk SET Дата_завершения = "", Статус = "Открыта" WHERE Пномер IN (10571)')
print(u)