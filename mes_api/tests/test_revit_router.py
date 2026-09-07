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


def _load_router_with_stubs():
    fastapi = types.ModuleType("fastapi")
    fastapi.APIRouter = _Router
    fastapi.HTTPException = _HttpException
    pydantic = types.ModuleType("pydantic")
    pydantic.BaseModel = _BaseModel
    pydantic.Field = _field
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
    }
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


if __name__ == "__main__":
    unittest.main()
