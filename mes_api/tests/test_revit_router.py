import importlib.util
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


class _Router:
    def __init__(self, *args, **kwargs):
        pass

    def post(self, *args, **kwargs):
        return lambda function: function


class _HttpException(Exception):
    def __init__(self, status_code, detail):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class _BaseModel:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def dict(self):
        return dict(self.__dict__)


class _JsonResponse:
    def __init__(self, content, status_code=200):
        self.content = content
        self.status_code = status_code


def _field(default=None, default_factory=None, **kwargs):
    return default_factory() if default_factory is not None else default


def _load_router_with_stubs(real_http=False):
    fastapi = types.ModuleType("fastapi")
    fastapi.APIRouter = _Router
    fastapi.HTTPException = _HttpException
    pydantic = types.ModuleType("pydantic")
    pydantic.BaseModel = _BaseModel
    pydantic.Field = _field
    pydantic.StrictBool = bool
    starlette = types.ModuleType("starlette")
    starlette_responses = types.ModuleType("starlette.responses")
    starlette_responses.JSONResponse = _JsonResponse
    requests = types.ModuleType("requests")
    requests.exceptions = SimpleNamespace(RequestException=RuntimeError)

    project = types.ModuleType("project_cust_38")
    project.__path__ = []
    project.Cust_Functions = SimpleNamespace()
    project.Cust_config = SimpleNamespace()
    project.Cust_odata_erp = SimpleNamespace()
    project.Cust_resource_creator = SimpleNamespace()
    project.api_erp_commands = SimpleNamespace(USER_ERP="", PASS_ERP="")

    stubs = {
        "fastapi": fastapi,
        "pydantic": pydantic,
        "starlette": starlette,
        "starlette.responses": starlette_responses,
        "requests": requests,
        "project_cust_38": project,
        "revit_contract": __import__("mes_api.revit_contract", fromlist=["*"]),
    }
    if real_http:
        for name in ("fastapi", "pydantic", "starlette", "starlette.responses"):
            stubs.pop(name)
    module_name = "mes_api.revit_router_under_test"
    path = Path(__file__).resolve().parents[1] / "revit_router.py"
    with patch.dict(sys.modules, stubs):
        spec = importlib.util.spec_from_file_location(module_name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
        finally:
            sys.modules.pop(module_name, None)
    return module


class ResourceValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.router = _load_router_with_stubs()

    def _body(self):
        rows = [
            SimpleNamespace(
                row=1,
                source_row=7,
                erp_code="A",
                quantity="1,5 м",
                element_ids=[101],
                match_state="matched",
                stage="",
                unit="м",
                match_info="",
            ),
            SimpleNamespace(
                row=2,
                source_row=8,
                erp_code="B",
                quantity="2",
                element_ids=[102],
                match_state="matched",
                stage="",
                unit="шт",
                match_info="",
            ),
        ]
        return SimpleNamespace(
            action="upload_resource_map",
            contract_version=2,
            title="Тестовая ресурсная",
            creator="Иван Иванов",
            user="",
            start_date="2026-09-07",
            end_date="2026-09-08",
            comment="ПР:T:1",
            output_product=SimpleNamespace(code="OUT", name="Изделие", unit="шт"),
            schedule={"name": "Спецификация", "field_mapping_exact": True},
            rows=rows,
            skip_unmapped_rows=False,
            cost_article_ref=None,
        )

    def test_codes_are_checked_in_one_batch(self):
        body = self._body()
        title_client = SimpleNamespace(get_response=lambda *args, **kwargs: (200, []))
        self.router.COE = SimpleNamespace(OrdersComposit=lambda base: title_client)
        existing = {
            "out": {"Code": "OUT", "Name": "Изделие"},
            "a": {"Code": "A", "Name": "Материал A"},
            "b": {"Code": "B", "Name": "Материал B"},
        }
        with patch.object(self.router, "_fetch_nomenclature", return_value=existing) as fetch:
            fields, errors, rows, warnings = self.router._validate_resource_request(body)
        fetch.assert_called_once_with(["OUT", "A", "B"])
        self.assertEqual(fields, {})
        self.assertEqual(errors, [])
        self.assertEqual(len(rows), 2)
        self.assertEqual(warnings, [])

    def test_missing_code_error_keeps_revit_source_row(self):
        body = self._body()
        title_client = SimpleNamespace(get_response=lambda *args, **kwargs: (200, []))
        self.router.COE = SimpleNamespace(OrdersComposit=lambda base: title_client)
        existing = {
            "out": {"Code": "OUT", "Name": "Изделие"},
            "a": {"Code": "A", "Name": "Материал A"},
        }
        with patch.object(self.router, "_fetch_nomenclature", return_value=existing):
            _, errors, _, _ = self.router._validate_resource_request(body)
        self.assertEqual(errors, [
            {"row": 2, "source_row": 8, "msg": "Код номенклатуры не найден в 1С"}
        ])

    def test_upload_builds_one_specification_and_groups_stages(self):
        created = []

        class StageData:
            def __init__(self, **kwargs):
                self.materials = []

            def add_material(self, material):
                self.materials.append(material)

        class Specification:
            def __init__(self, header):
                self.stages = []
                created.append(self)

            def add_stage(self, stage):
                self.stages.append(stage)

            def send(self, **kwargs):
                return True, {"e1c_link": "e1c://created"}

        fake_crc = SimpleNamespace(
            SubdivisionsData=SimpleNamespace(
                _hnt_проектный_отдел_пкб_производственные_подразделения_пкб_пауэрз_00_000021=object()
            ),
            GroupResData=SimpleNamespace(
                _hnt_проектирование_пкб_пауэрз_00_010491=object()
            ),
            TheMethodOfAllocatingTheCostOfTheOutputProductsData=SimpleNamespace(
                _hnt_по_долям_стоимости_0=object()
            ),
            MainProduct=lambda *args: SimpleNamespace(args=args),
            CurrentUser=lambda name: SimpleNamespace(name=name),
            ResourceHeader=lambda **kwargs: SimpleNamespace(**kwargs),
            ArticulationArticlesData=SimpleNamespace(
                init_data=lambda: None,
                _hnt_основной_фот_none=object(),
            ),
            ArticulationArticles=lambda **kwargs: SimpleNamespace(**kwargs),
            MethodOfObtainingMaterialspecificationsData=SimpleNamespace(
                find_by_ref=lambda ref: object()
            ),
            StageData=StageData,
            Material=lambda *args: SimpleNamespace(args=args),
            Stage=lambda name, data: SimpleNamespace(name=name, data=data),
            ResourceSpecification=Specification,
        )
        body = self._body()
        body.rows.append(
            SimpleNamespace(
                row=3,
                source_row=9,
                erp_code="C",
                quantity="3",
                element_ids=[103],
                match_state="matched",
                stage="Монтаж",
                unit="шт",
                match_info="",
            )
        )
        body.rows[0].stage = "Заготовка"
        body.rows[1].stage = "Заготовка"
        normalized = [
            self.router.normalize_resource_row(row, index)
            for index, row in enumerate(body.rows, start=1)
        ]
        with patch.object(self.router, "CRC", fake_crc):
            response = self.router._upload_resource_once(body, normalized)

        self.assertEqual(response, {"e1c_link": "e1c://created"})
        self.assertEqual(len(created), 1)
        self.assertEqual([stage.name for stage in created[0].stages], ["Заготовка", "Монтаж"])
        self.assertEqual([len(stage.data.materials) for stage in created[0].stages], [2, 1])
        self.assertEqual(created[0].stages[0].data.materials[0].args[1], 1.5)

        body.cost_article_ref = "11111111-1111-1111-1111-111111111111"
        article = {"Ref_Key": body.cost_article_ref, "Description": "Сырье"}
        with patch.object(self.router, "CRC", fake_crc), patch.object(
            self.router, "_resolve_cost_article", return_value=article
        ):
            self.router._upload_resource_once(body, normalized)
        for stage in created[-1].stages:
            for material in stage.data.materials:
                selected = material.args[2]
                self.assertEqual(selected.ref_key, body.cost_article_ref)
                self.assertEqual(selected.name, "Сырье")
                self.assertEqual(selected.parent, self.router.COST_ARTICLE_PARENT)

    def test_partial_export_requires_opt_in_and_preserves_source_rows(self):
        body = self._body()
        body.rows[0].erp_code = ""
        body.rows[0].quantity = "bad"  # Ignored only when the whole row is skipped.
        self.router.COE = SimpleNamespace(OrdersComposit=lambda base: SimpleNamespace(
            get_response=lambda *args, **kwargs: (200, [])))
        existing = {"out": {"Code": "OUT"}, "b": {"Code": "B"}}
        with patch.object(self.router, "_fetch_nomenclature", return_value=existing) as fetch:
            _, errors, _, _ = self.router._validate_resource_request(body)
            self.assertTrue(any("код ERP" in row["msg"] for row in errors))
            body.skip_unmapped_rows = True
            fields, errors, rows, warnings = self.router._validate_resource_request(body)
            fetch.assert_called_with(["OUT", "B"])
        self.assertEqual((fields, errors), ({}, []))
        self.assertEqual([(row.row, row.source_row) for row in rows], [(2, 8)])
        self.assertEqual(warnings, ["Пропущено строк без кода 1C-ERP: 1"])
        self.assertEqual(self.router._export_summary(body), {
            "exported_rows": 1, "skipped_rows": 1, "skipped_source_rows": [7]})

    def test_article_query_is_parameterized_and_cache_is_reused(self):
        self.router._reference_cache.clear()
        captured = []

        class Refs:
            def __init__(self, query):
                self.query = query

            def add_ref(self, ref):
                captured.append(ref)

        article = {"Ref_Key": "11111111-1111-1111-1111-111111111111", "Description": "Сырье"}
        api = SimpleNamespace(Refs_wet=Refs, Ref_wet=lambda *args: args)
        with patch.object(self.router, "APIERP", api), patch.object(
            self.router, "_run_wet_query", return_value=[article]
        ) as query:
            self.assertEqual(self.router._load_cost_articles(), [article])
            self.assertEqual(self.router._resolve_cost_article(article["Ref_Key"]), article)
        query.assert_called_once()
        self.assertEqual(captured, [("Родитель", "Справочники.СтатьиКалькуляции",
                                    self.router.COST_ARTICLE_PARENT)])
        self.assertIn("СтатьиКалькуляции.Родитель = &Родитель", query.call_args.args[0])
        self.assertIn("ЭтоГруппа = ЛОЖЬ", query.call_args.args[0])
        self.assertIn("ПометкаУдаления = ЛОЖЬ", query.call_args.args[0])
        with self.assertRaises(ValueError):
            self.router._resolve_cost_article("22222222-2222-2222-2222-222222222222")
        with self.assertRaises(ValueError):
            self.router._resolve_cost_article("")

    def test_source_filters_keep_ancestors_and_do_not_leak_cached_results(self):
        import json
        ids = [f"00000000-0000-0000-0000-{index:012d}" for index in range(1, 6)]
        root, folder, first, second, deleted = ids
        rows = [
            {"Ref_Key": root, "Parent_Key": "", "Description": "Корень", "IsFolder": True},
            {"Ref_Key": folder, "Parent_Key": root, "Description": "Группа", "IsFolder": True},
            {"Ref_Key": first, "Parent_Key": folder, "Description": "Первый"},
            {"Ref_Key": second, "Parent_Key": folder, "Description": "Второй"},
            {"Ref_Key": deleted, "Parent_Key": root, "ПометкаУдаления": True},
        ]
        policy = {"main": {"exclude_refs": []},
                  "revit_mapping": {"include_refs": [first]},
                  "revit_output_product": {"exclude_refs": [folder]}}
        self.router._reference_cache.clear()
        with patch.dict(self.router.os.environ, {"REVIT_NOMENCLATURE_FILTERS": json.dumps(policy)}), \
                patch.object(self.router, "_run_wet_query", return_value=rows) as fetch:
            def refs(source):
                result = self.router.nomen_types(self.router.ActionRequest(source=source))
                return [row["Ref_Key"] for row in result]
            self.assertEqual(refs("revit_mapping"), [root, folder, first])
            self.assertEqual(refs("revit_output_product"), [root])
            self.assertEqual(refs("main"), [root, folder, first, second])
            self.assertEqual(refs("unknown"), refs("main"))
            self.assertEqual(refs(""), refs("main"))
            fetch.assert_called_once()
        self.assertEqual(rows[0]["Description"], "Корень")

    def test_empty_include_hides_all_and_invalid_filter_does_not_expose_all(self):
        with patch.dict(self.router.os.environ, {"REVIT_NOMENCLATURE_FILTERS": '{"main":{"include_refs":[]}}'}):
            self.assertEqual(self.router._filter_kinds_for_source([{"Ref_Key": "a"}], "main"), [])
        with patch.dict(self.router.os.environ, {"REVIT_NOMENCLATURE_FILTERS": '{"main":{"include_refs":"bad"}}'}):
            with self.assertRaises(_HttpException) as raised:
                self.router._filter_kinds_for_source([], "main")
        self.assertEqual(raised.exception.status_code, 503)


if __name__ == "__main__":
    unittest.main()
