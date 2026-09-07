import project_cust_38.Cust_SQLite as CSQ

class Remark:
    '''создан как адаптер для jurnal_zamech из report_ci '''
    def __init__(self, start, stop) -> None:
        self.bd_naryad = 'SRV:Naryad.db'
        self.db_users = 'C:\DB_srv\BD_users.db'
        self.get_requests_to_db(start, stop)

    def preparate_date_forman(self, date):
        return f'{date} 00:00:00'

    def get_requests_to_db(self, nach, konec):
        stmt_full_remark = f"""SELECT * FROM zamech where date(Дата_создания) BETWEEN  date('{self.preparate_date_forman(nach)}') AND  date('{self.preparate_date_forman(konec)}') """
        stmt_division = '''SELECT Код, Имя FROM rab_c'''
        stmt_kod_zamech = '''SELECT * FROM kod_zamech'''
        stmt_kod_vp = '''SELECT * FROM kod_zamech_vp'''


        pre_kod_zamech = CSQ.custom_request_c(self.bd_naryad, stmt_kod_zamech, rez_dict=True)
        pre_kod_vp = CSQ.custom_request_c(self.bd_naryad, stmt_kod_vp,  rez_dict=True)
        self.full_remark = CSQ.custom_request_c(self.bd_naryad, stmt_full_remark,  rez_dict=True)
        pre_division = CSQ.custom_request_c(self.db_users, stmt_division,  rez_dict=False)


        self.kod_zamech = {val['Пномер']:val['Имя'] for val in pre_kod_zamech}
        self.kod_vp = {val['Пномер']:val['Имя'] for val in pre_kod_vp}
        self.division = {val[0]:val[1] for val in pre_division}

    def get_result_labels_values(self, is_kod_zamech=False, is_kod_vp=False, is_full=False):
        if is_full:
            headers = list(self.full_remark[0].keys())
            full = [headers]
            for one_r in self.full_remark:
                one_remark = []
                for val_name in headers:
                    one_remark.append(one_r[val_name])
                full.append(one_remark)
            return full
        
        result_remarks = {}
        for remark in self.full_remark:
            if is_kod_zamech:
                divisin_name = self.kod_zamech.get(remark['Код_вп'])
            elif is_kod_vp:
                divisin_name = self.kod_vp.get(remark['Код_вп'])
            else:
                divisin_name = self.division.get(remark['Виновное_подразделение'])
            if divisin_name:
                if result_remarks.get(divisin_name):
                    result_remarks[divisin_name] += 1
                else:
                    result_remarks[divisin_name] = 1
        return self.get_labels_values(result_remarks)

    # def get_full_remarks(self):
    #     full_li = []
    #     full_li.append(self.get_result_labels_values())
    #     full_li.append(self.get_result_labels_values(is_kod_vp=True))
    #     full_li.append(self.get_result_labels_values(is_kod_zamech=True))
    #     return full_li

            
    def get_labels_values(self, dict):
        labels = []
        values = []
        for label, value in dict.items():
            labels.append(label)
            values.append(value)
        return labels, values



if __name__ == "__main__":
    r = Remark()
    r.jurnal_zamech('2023-01-02', '2023-10-05')