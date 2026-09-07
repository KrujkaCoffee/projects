from project_cust_38 import Cust_config as CFG
from project_cust_38 import context_admin as CADM


def iter_project_dbs():
    project = CFG.Config.project

    # typed aliases из ProjectConfig
    typed = {
        'db_naryad': project.db_naryad,
        'db_files': project.db_files,
        'db_kplan': project.db_kplan,
        'db_users': project.db_users,
        'db_resxml': project.db_resxml,
        'db_nomen': project.db_nomen,
        'db_dse': project.db_dse,
        'db_flet': project.db_flet,
        'db_act': project.db_act,
    }

    # доп. алиасы, которые ещё живут в CFG.cfg / F.bdcfg
    extra = {
        'DB_invest': CFG.Config.project['DB_invest'] if 'DB_invest' in CFG.Config.project.__dict__ else None,
        'DB_staff_placement': CFG.Config.project['DB_staff_placement'] if 'DB_staff_placement' in CFG.Config.project.__dict__ else None,
    }

    for db_key, db_path in {**typed, **extra}.items():
        if isinstance(db_path, str) and db_path.strip():
            yield db_key, db_path


def main():
    repo = CADM.ensure_admin_schema(CFG.Config.project.db_files)

    for db_key, db_path in iter_project_dbs():
        repo.bootstrap_tables_from_db(
            db_path='C://',
            db_key=db_key,
            include_fields=True,
            schema_enabled=1,
            cache_enabled=1,
            is_enabled=1,
            cache_lifetime_min=120,
            notes='bootstrap_all_project_dbs.py',
        )
        print(db_key, db_path)


if __name__ == '__main__':
    main()