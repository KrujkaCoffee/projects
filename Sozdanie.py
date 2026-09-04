import datetime
import os
import importlib
import pathlib
import sys
import unittest
import contextlib
from unittest.mock import Mock, patch

with patch('project_cust_38.Cust_Functions.name_of_executable_file_c', return_value="Viewer.py"):
    # CFG.Config.app = CFG.AppConfig()
    # CFG.Config.place = CFG.Place(organization_name='Пауэрз')
    from project_cust_38 import Cust_SQLite as CSQ
    from project_cust_38 import Cust_mes as CMS
    from project_cust_38 import Cust_config as CFG
    from project_cust_38 import report_ci


def remove_pg_mark_imports():
    os.environ.pop('PG_CONN', None)
    importlib.reload(CSQ)
    importlib.reload(CMS.CSQ)

def create_pg_mark_imports():
    os.environ['PG_CONN'] = '1'
    importlib.reload(CSQ)
    importlib.reload(CMS.CSQ)


@unittest.skip("Cust_mes набор тестов")
class TestCustMesFunctions(unittest.TestCase):

    def setUp(self):
        CFG.Config.place.poki = 1
        self.test_fio_worker = 'Юсупов Шерзод Эркинович'
        self.test_date = self.test_end_date = (datetime.datetime.now() - datetime.timedelta(days=423)).strftime("%Y-%m-%d %H:%M:%S")
        self.test_date = self.test_start_date = (datetime.datetime.now() - datetime.timedelta(days=410)).strftime("%Y-%m-%d %H:%M:%S")

    def test_journal_pairs(self):
        remove_pg_mark_imports()
        result = CMS.get_start_stop_journal_pairs(
            between_stop_datetime=(datetime.datetime.now() - datetime.timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S"),
            between_start_datetime=(datetime.datetime.now() - datetime.timedelta(days=15)).strftime("%Y-%m-%d %H:%M:%S"),
        )
        create_pg_mark_imports()

        result2 = CMS.get_start_stop_journal_pairs(
            between_stop_datetime=(datetime.datetime.now() - datetime.timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S"),
            between_start_datetime=(datetime.datetime.now() - datetime.timedelta(days=15)).strftime("%Y-%m-%d %H:%M:%S"),
        )
        assert len(result2) == len(result), "неравное количество записей"
        # assert result == result2, "записи неравны"

    def test_opened_groups_naryad(self):
        remove_pg_mark_imports()
        result_sqlite = CMS.find_not_close_groups()
        create_pg_mark_imports()
        result_postgres = CMS.find_not_close_groups()
        assert isinstance(result_postgres, list) == isinstance(result_sqlite, list)

    def test_napr_types(self):
        remove_pg_mark_imports()
        result_sqlite = CMS.TypesWorkingByDirections().get_old_view_response()
        create_pg_mark_imports()
        result_postgres = CMS.TypesWorkingByDirections().get_old_view_response()
        assert isinstance(result_postgres, list) == isinstance(result_sqlite, list)
        assert len(result_postgres) == len(result_sqlite)
        # assert result_postgres == result_sqlite

    def test_list_dolgn_etap(self):
        date_format = "%Y-%m-%d %H:%M:%S"
        string_date_view = (datetime.datetime.now() - datetime.timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")

        remove_pg_mark_imports()
        result_sqlite = CMS.list_dolgn_etap(string_date_view, date_format)
        create_pg_mark_imports()
        result_postgres = CMS.list_dolgn_etap(string_date_view, date_format)
        assert isinstance(result_postgres, list) == isinstance(result_sqlite, list)
        assert len(result_postgres) == len(result_sqlite)
        assert result_postgres == result_sqlite

    def test_etap_by_fio(self):
        remove_pg_mark_imports()
        result_sqlite = CMS.ETAP_BY_FIO(CFG.Config.project.db_users, CFG.Config.project.db_naryad)
        create_pg_mark_imports()
        result_postgres = CMS.ETAP_BY_FIO(CFG.Config.project.db_users, CFG.Config.project.db_naryad)
        assert isinstance(result_postgres, list) == isinstance(result_sqlite, list)
        assert len(result_postgres) == len(result_sqlite)
        assert result_postgres == result_sqlite

    def test_VID_RABOT_PO_EMPL(self):
        remove_pg_mark_imports()
        result_sqlite = CMS.VID_RABOT_PO_EMPL(CFG.Config.project.db_users)
        create_pg_mark_imports()
        result_postgres = CMS.VID_RABOT_PO_EMPL(CFG.Config.project.db_users)
        assert isinstance(result_postgres, list) == isinstance(result_sqlite, list)
        assert len(result_postgres) == len(result_sqlite)
        assert result_postgres == result_sqlite

    def test_time_by_repo_card_c(self):
        remove_pg_mark_imports()
        result_sqlite = CMS.time_by_repo_card_c(self.test_fio_worker, self.test_date)
        create_pg_mark_imports()
        result_postgres = CMS.time_by_repo_card_c(self.test_fio_worker, self.test_date)
        assert isinstance(result_postgres, list) == isinstance(result_sqlite, list)
        assert len(result_postgres) == len(result_sqlite)
        assert result_postgres == result_sqlite


class TestReportCi(unittest.TestCase):
    def setUp(self):
        self.viewer_path = (pathlib.Path() / 'Viewer').resolve(True)
        sys.path.insert(0, str(self.viewer_path))
        # self.patches = (
        #     patch("Viewer.SafeApplication.exec", return_value=0),
        #     patch("PyQt5.SafeApplication.exec", return_value=0),
        #     patch("Viewer.sys.exit"),
        #     patch("Viewer.QMainWindow.show"),
        #     patch(
        #         "project_cust_38.Cust_application.SafeApplication.exec",
        #         return_value=0,
        #     ),
        #     patch("sys.exit"),
        #     patch("sys"),
        #     patch(
        #         "project_cust_38.Cust_application.SafeApplication.exec",
        #         return_value=0,
        #     ),
        #
        # )
        # self.mock_qt_exec, self.mock_sys_exit, self.mock_show = (
        #     patcher.start()
        #     for patcher in self.patches
        # )
        self.target_project = 'ПУ00-000067 | 2503086 | ПР | B1-14 | 6480 | 44.8'
        self.department = 'Сборочный цех Производства'

        from Viewer import mywindow
        self.viewer = mywindow()
        self.test_fio_worker = 'Юсупов Шерзод Эркинович'
        self.test_date = self.test_end_date = (datetime.datetime.now() - datetime.timedelta(days=423)).strftime("%Y-%m-%d %H:%M:%S")
        self.test_date = self.test_start_date = (datetime.datetime.now() - datetime.timedelta(days=410)).strftime("%Y-%m-%d %H:%M:%S")
        # self.mock_qt_exec, self.mock_sys_exit, self.mock_show = (
        #     self.addCleanup(patcher.stop)
        #     for patcher in self.patches
        # )

    def test__report_by_proj(self):
        remove_pg_mark_imports()
        result_sqlite = report_ci.report_by_proj(self.viewer, '', '', self.target_project)
        create_pg_mark_imports()
        result_postgres = report_ci.report_by_proj(self.viewer, '', '', self.target_project)
        assert isinstance(result_postgres, list) == isinstance(result_sqlite, list)
        assert len(result_postgres) == len(result_sqlite)
        assert result_postgres == result_sqlite

    def test__report_of_load_machine(self):
        remove_pg_mark_imports()
        result_sqlite = report_ci.report_of_load_machine(self.viewer, self.test_start_date, self.test_end_date)
        create_pg_mark_imports()
        result_postgres = report_ci.report_of_load_machine(self.viewer, self.test_start_date, self.test_end_date)
        assert isinstance(result_postgres, list) == isinstance(result_sqlite, list)
        assert len(result_postgres) == len(result_sqlite)
        assert result_postgres == result_sqlite

    def test__virabotka_ceha(self):
        remove_pg_mark_imports()
        result_sqlite = report_ci.virabotka_ceha(self.viewer, self.test_start_date, self.test_end_date)
        create_pg_mark_imports()
        result_postgres = report_ci.virabotka_ceha(self.viewer, self.test_start_date, self.test_end_date)
        assert isinstance(result_postgres, list) == isinstance(result_sqlite, list)
        assert len(result_postgres) == len(result_sqlite)
        assert result_postgres == result_sqlite

    def test__ispoln_pl_month(self):
        remove_pg_mark_imports()
        result_sqlite = report_ci.ispoln_pl_month_all(
            self.viewer, CFG.Config.project.db_kplan, CFG.Config.project.db_resxml, CFG.Config.project.db_naryad, CFG.Config.project.db_users, self.viewer.Data.DICT_PROFESSIONS,
                                   self.viewer.Data.DICT_VID_RABOT, 'Сборочный цех производства')
        create_pg_mark_imports()
        result_postgres = report_ci.ispoln_pl_month_all(
            self.viewer, CFG.Config.project.db_kplan, CFG.Config.project.db_resxml, CFG.Config.project.db_naryad, CFG.Config.project.db_users, self.viewer.Data.DICT_PROFESSIONS,
                                   self.viewer.Data.DICT_VID_RABOT, 'Сборочный цех производства')
        assert isinstance(result_postgres, list) == isinstance(result_sqlite, list)
        assert len(result_postgres) == len(result_sqlite)
        assert result_postgres == result_sqlite

    def test__statistic_normoweight_MK_c(self):
        remove_pg_mark_imports()
        result_sqlite = report_ci.statistic_normoweight_MK_c(self.viewer, self.test_start_date, self.test_end_date)
        create_pg_mark_imports()
        result_postgres = report_ci.statistic_normoweight_MK_c(self.viewer, self.test_start_date, self.test_end_date)
        assert isinstance(result_postgres, list) == isinstance(result_sqlite, list)
        assert len(result_postgres) == len(result_sqlite)
        assert result_postgres == result_sqlite

    def test__trudozatraty(self):
        remove_pg_mark_imports()
        result_sqlite = report_ci.trudozatraty(self.viewer, self.test_start_date, self.test_end_date)
        create_pg_mark_imports()
        result_postgres = report_ci.trudozatraty(self.viewer, self.test_start_date, self.test_end_date)
        assert isinstance(result_postgres, list) == isinstance(result_sqlite, list)
        assert len(result_postgres) == len(result_sqlite)
        assert result_postgres == result_sqlite

    def test__min_za_den_tabel(self):
        remove_pg_mark_imports()
        result_sqlite = report_ci.trudozatraty(self.viewer, self.test_start_date, self.test_end_date)
        create_pg_mark_imports()
        result_postgres = report_ci.trudozatraty(self.viewer, self.test_start_date, self.test_end_date)
        assert isinstance(result_postgres, list) == isinstance(result_sqlite, list)
        assert len(result_postgres) == len(result_sqlite)
        assert result_postgres == result_sqlite

    def test__diver_trdz_1c_mes(self):
        remove_pg_mark_imports()
        result_sqlite, func = report_ci.diver_trdz_1c_mes(self.viewer, self.test_start_date, self.test_end_date)
        create_pg_mark_imports()
        result_postgres, func = report_ci.diver_trdz_1c_mes(self.viewer, self.test_start_date, self.test_end_date)
        assert isinstance(result_postgres, list) == isinstance(result_sqlite, list)
        assert len(result_postgres) == len(result_sqlite)
        assert result_postgres == result_sqlite
        assert callable(func)

    def test__get_plan_vneplan_data(self):
        remove_pg_mark_imports()
        result_sqlite = report_ci.get_plan_vneplan_data(self.viewer, self.test_start_date, self.test_end_date)
        create_pg_mark_imports()
        result_postgres = report_ci.get_plan_vneplan_data(self.viewer, self.test_start_date, self.test_end_date)
        assert isinstance(result_postgres, list) == isinstance(result_sqlite, list)
        assert len(result_postgres) == len(result_sqlite)
        assert result_postgres == result_sqlite

    def test__udel_trud_sort_c(self):
        remove_pg_mark_imports()
        result_sqlite = report_ci.get_plan_vneplan_data(self.viewer, self.test_start_date, self.test_end_date)
        create_pg_mark_imports()
        result_postgres = report_ci.get_plan_vneplan_data(self.viewer, self.test_start_date, self.test_end_date)
        assert isinstance(result_postgres, list) == isinstance(result_sqlite, list)
        assert len(result_postgres) == len(result_sqlite)
        assert result_postgres == result_sqlite

    def test__divergence_of_date_proj(self):
        remove_pg_mark_imports()
        result_sqlite = report_ci.divergence_of_date_proj(self.viewer, self.test_start_date, self.test_end_date)
        create_pg_mark_imports()
        result_postgres = report_ci.divergence_of_date_proj(self.viewer, self.test_start_date, self.test_end_date)
        assert isinstance(result_postgres, list) == isinstance(result_sqlite, list)
        assert len(result_postgres) == len(result_sqlite)
        assert result_postgres == result_sqlite

    def test__calc_tehpodgotovka_per_month(self):
        remove_pg_mark_imports()
        result_sqlite = report_ci.calc_tehpodgotovka_per_month(
        bd_naryad=CFG.Config.project.db_naryad, bd_users=CFG.Config.project.db_users, db_resxml=CFG.Config.project.db_resxml, db_dse=CFG.Config.project.db_dse, data_nach=self.test_start_date, data_kon=self.test_end_date, tip='за год')
        create_pg_mark_imports()
        result_postgres = report_ci.calc_tehpodgotovka_per_month(
        bd_naryad=CFG.Config.project.db_naryad, bd_users=CFG.Config.project.db_users, db_resxml=CFG.Config.project.db_resxml, db_dse=CFG.Config.project.db_dse, data_nach=self.test_start_date, data_kon=self.test_end_date, tip='за год')
        assert isinstance(result_postgres, list) == isinstance(result_sqlite, list)
        assert len(result_postgres) == len(result_sqlite)
        assert result_postgres == result_sqlite

    def test__plan_fact_grafic_mes(self):
        remove_pg_mark_imports()
        result_sqlite = report_ci.plan_fact_grafic_mes(self.viewer, self.test_start_date, self.test_end_date)
        create_pg_mark_imports()
        result_postgres = report_ci.plan_fact_grafic_mes(self.viewer, self.test_start_date, self.test_end_date)
        assert isinstance(result_postgres, list) == isinstance(result_sqlite, list)
        assert len(result_postgres) == len(result_sqlite)
        assert result_postgres == result_sqlite

    def test__virabotka_ceha_ponaryadno(self):
        remove_pg_mark_imports()
        result_sqlite = report_ci.virabotka_ceha_ponaryadno(self.viewer, self.test_start_date, self.test_end_date)
        create_pg_mark_imports()
        result_postgres = report_ci.virabotka_ceha_ponaryadno(self.viewer, self.test_start_date, self.test_end_date)
        assert isinstance(result_postgres, list) == isinstance(result_sqlite, list)
        assert len(result_postgres) == len(result_sqlite)
        assert result_postgres == result_sqlite

    def test__virabotka_sotr(self):
        remove_pg_mark_imports()
        result_sqlite = report_ci.virabotka_sotr(self.viewer, self.test_start_date, self.test_end_date, self.test_fio_worker)
        create_pg_mark_imports()
        result_postgres = report_ci.virabotka_sotr(self.viewer, self.test_start_date, self.test_end_date, self.test_fio_worker)
        assert isinstance(result_postgres, list) == isinstance(result_sqlite, list)
        assert len(result_postgres) == len(result_sqlite)
        assert result_postgres == result_sqlite

    def test__get_jur_brak(self):
        remove_pg_mark_imports()
        result_sqlite = report_ci.get_jur_brak(CFG.Config.project.db_naryad, self.test_start_date, self.test_end_date)
        create_pg_mark_imports()
        result_postgres = report_ci.get_jur_brak(CFG.Config.project.db_naryad, self.test_start_date, self.test_end_date)
        assert isinstance(result_postgres, list) == isinstance(result_sqlite, list)
        assert len(result_postgres) == len(result_sqlite)
        assert result_postgres == result_sqlite

    def test__vir_otgr(self):
        remove_pg_mark_imports()
        result_sqlite = report_ci.vir_otgr(self.viewer, self.test_start_date, self.test_end_date, '', '', '')
        create_pg_mark_imports()
        result_postgres = report_ci.vir_otgr(self.viewer, self.test_start_date, self.test_end_date, '', '', '')
        assert isinstance(result_postgres, list) == isinstance(result_sqlite, list)
        assert len(result_postgres) == len(result_sqlite)
        assert result_postgres == result_sqlite

    def test__rasch_posesh(self):
        remove_pg_mark_imports()
        result_sqlite = report_ci.rasch_posesh(self.viewer, self.test_start_date, self.test_end_date, '', '', '')
        create_pg_mark_imports()
        result_postgres = report_ci.rasch_posesh(self.viewer, self.test_start_date, self.test_end_date, '', '', '')
        assert isinstance(result_postgres, list) == isinstance(result_sqlite, list)
        assert len(result_postgres) == len(result_sqlite)
        assert result_postgres == result_sqlite # 54

    def test__jurnal_rabot(self):
        remove_pg_mark_imports()
        result_sqlite = report_ci.jurnal_rabot(self.viewer, self.test_start_date, self.test_end_date)
        create_pg_mark_imports()
        result_postgres = report_ci.jurnal_rabot(self.viewer, self.test_start_date, self.test_end_date)
        assert isinstance(result_postgres, list) == isinstance(result_sqlite, list)
        assert len(result_postgres) == len(result_sqlite)
        assert result_postgres == result_sqlite # 54

    def test__vneplan_rabot(self):
        remove_pg_mark_imports()
        result_sqlite = report_ci.vneplan_rabot(self.viewer, self.test_start_date, self.test_end_date)
        create_pg_mark_imports()
        result_postgres = report_ci.vneplan_rabot(self.viewer, self.test_start_date, self.test_end_date)
        assert isinstance(result_postgres, list) == isinstance(result_sqlite, list)
        assert len(result_postgres) == len(result_sqlite)
        assert result_postgres == result_sqlite # 54

    def test__tekush_raboty(self):
        remove_pg_mark_imports()
        result_sqlite = report_ci.tekush_raboty(self.viewer, self.test_start_date, self.test_end_date)
        create_pg_mark_imports()
        result_postgres = report_ci.tekush_raboty(self.viewer, self.test_start_date, self.test_end_date)
        assert isinstance(result_postgres, list) == isinstance(result_sqlite, list)
        assert len(result_postgres) == len(result_sqlite)
        assert result_postgres == result_sqlite # 54

    def test__report_c_selector_2(self):
        remove_pg_mark_imports()
        result_sqlite = report_ci.report_c_selector_2(self.viewer, self.test_start_date, self.test_end_date, '')
        create_pg_mark_imports()
        result_postgres = report_ci.report_c_selector_2(self.viewer, self.test_start_date, self.test_end_date, '')
        assert isinstance(result_postgres, list) == isinstance(result_sqlite, list)
        assert len(result_postgres) == len(result_sqlite)
        assert result_postgres == result_sqlite # 54

    def test__sravn_nv_napr(self):
        remove_pg_mark_imports()
        result_sqlite = report_ci.sravn_nv_napr(self.viewer, self.test_start_date, self.test_end_date)
        create_pg_mark_imports()
        result_postgres = report_ci.sravn_nv_napr(self.viewer, self.test_start_date, self.test_end_date)
        assert isinstance(result_postgres, list) == isinstance(result_sqlite, list)
        assert len(result_postgres) == len(result_sqlite)
        assert result_postgres == result_sqlite # 54

    def test__ready_procent_ver2(self):
        remove_pg_mark_imports()
        result_sqlite = report_ci.sravn_nv_napr(self.viewer, self.test_start_date, self.test_end_date)
        create_pg_mark_imports()
        result_postgres = report_ci.sravn_nv_napr(self.viewer, self.test_start_date, self.test_end_date)
        assert isinstance(result_postgres, list) == isinstance(result_sqlite, list)
        assert len(result_postgres) == len(result_sqlite)
        assert result_postgres == result_sqlite # 54

    def test__analysis_effectiv_work_per_minute(self):
        remove_pg_mark_imports()
        result_sqlite = report_ci.analysis_effectiv_work_per_minute(self.viewer, self.test_start_date, self.test_end_date)
        create_pg_mark_imports()
        result_postgres = report_ci.analysis_effectiv_work_per_minute(self.viewer, self.test_start_date, self.test_end_date)
        assert isinstance(result_postgres, list) == isinstance(result_sqlite, list)
        assert len(result_postgres) == len(result_sqlite)
        assert result_postgres == result_sqlite # 54

    def test__analysis_vneplan_by_vid_rab(self):
        remove_pg_mark_imports()
        result_sqlite = report_ci.analysis_vneplan_by_vid_rab(self.viewer, self.test_start_date, self.test_end_date)
        create_pg_mark_imports()
        result_postgres = report_ci.analysis_vneplan_by_vid_rab(self.viewer, self.test_start_date, self.test_end_date)
        assert isinstance(result_postgres, list) == isinstance(result_sqlite, list)
        assert len(result_postgres) == len(result_sqlite)
        assert result_postgres == result_sqlite # 54

    def test__virabotka_sotr_za_mes(self):
        remove_pg_mark_imports()
        result_sqlite = report_ci.virabotka_sotr_za_mes(self.viewer, self.test_start_date, self.test_end_date)
        create_pg_mark_imports()
        result_postgres = report_ci.virabotka_sotr_za_mes(self.viewer, self.test_start_date, self.test_end_date)
        assert isinstance(result_postgres, list) == isinstance(result_sqlite, list)
        assert len(result_postgres) == len(result_sqlite)
        assert result_postgres == result_sqlite # 54

    def test__neosv_ves_po_sozd_nar(self):
        remove_pg_mark_imports()
        result_sqlite = report_ci.neosv_ves_po_sozd_nar(self.viewer, self.department)
        create_pg_mark_imports()
        result_postgres = report_ci.neosv_ves_po_sozd_nar(self.viewer, self.department)
        assert isinstance(result_postgres, list) == isinstance(result_sqlite, list)
        assert len(result_postgres) == len(result_sqlite)
        assert result_postgres == result_sqlite # 54

    def test__norm_mat_po_zav_nar(self):
        remove_pg_mark_imports()
        result_sqlite = report_ci.norm_mat_po_zav_nar(self.viewer, self.test_start_date, self.test_end_date)
        create_pg_mark_imports()
        result_postgres = report_ci.norm_mat_po_zav_nar(self.viewer, self.test_start_date, self.test_end_date)
        assert isinstance(result_postgres, list) == isinstance(result_sqlite, list)
        assert len(result_postgres) == len(result_sqlite)
        assert result_postgres == result_sqlite # 54

    def test__jurnal_tk(self):
        remove_pg_mark_imports()
        result_sqlite = report_ci.jurnal_tk(self.viewer, self.test_start_date, self.test_end_date)
        create_pg_mark_imports()
        result_postgres = report_ci.jurnal_tk(self.viewer, self.test_start_date, self.test_end_date)
        assert isinstance(result_postgres, list) == isinstance(result_sqlite, list)
        assert len(result_postgres) == len(result_sqlite)
        assert result_postgres == result_sqlite # 54

    def test__dinam_proizv_sotr(self):
        remove_pg_mark_imports()
        result_sqlite = report_ci.jurnal_tk(self.viewer, self.test_start_date, self.test_end_date)
        create_pg_mark_imports()
        result_postgres = report_ci.jurnal_tk(self.viewer, self.test_start_date, self.test_end_date)
        assert isinstance(result_postgres, list) == isinstance(result_sqlite, list)
        assert len(result_postgres) == len(result_sqlite)
        assert result_postgres == result_sqlite # 54

    def test__not_upload_erp_nar(self):
        remove_pg_mark_imports()
        result_sqlite = report_ci.not_upload_erp_nar(self.viewer, self.test_start_date, self.test_end_date)
        create_pg_mark_imports()
        result_postgres = report_ci.not_upload_erp_nar(self.viewer, self.test_start_date, self.test_end_date)
        assert isinstance(result_postgres, list) == isinstance(result_sqlite, list)
        assert len(result_postgres) == len(result_sqlite)
        assert result_postgres == result_sqlite # 54

    def test__report_by_open_naryads(self):
        remove_pg_mark_imports()
        result_sqlite = report_ci.report_by_open_naryads(self.viewer, self.test_start_date, self.test_end_date)
        create_pg_mark_imports()
        result_postgres = report_ci.report_by_open_naryads(self.viewer, self.test_start_date, self.test_end_date)
        assert isinstance(result_postgres, list) == isinstance(result_sqlite, list)
        assert len(result_postgres) == len(result_sqlite)
        assert result_postgres == result_sqlite # 54

    def test__gr_ud_proizv_cexa(self):
        remove_pg_mark_imports()
        result_sqlite = report_ci.report_by_open_naryads(self.viewer, self.test_start_date, self.test_end_date)
        create_pg_mark_imports()
        result_postgres = report_ci.report_by_open_naryads(self.viewer, self.test_start_date, self.test_end_date)
        assert isinstance(result_postgres, list) == isinstance(result_sqlite, list)
        assert len(result_postgres) == len(result_sqlite)
        assert result_postgres == result_sqlite # 54


if __name__ == '__main__':
    unittest.main(verbosity=2)
    from PyQt5.QtWidgets import QApplication