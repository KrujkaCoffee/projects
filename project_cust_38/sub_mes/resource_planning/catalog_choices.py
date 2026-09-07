from dataclasses import dataclass

from project_cust_38.sub_mes.resource_planning import catalog_link as CL
from project_cust_38.sub_mes.resource_planning import attribute_binding as AB
from project_cust_38.sub_mes.resource_planning import planner_mes as PMES

@dataclass(frozen=True, slots=True)
class CatalogFieldChoice:
    endpoint: CL.CatalogLinkEndpoint
    source_caption: str = ''
    entity_caption: str = ''

    def __post_init__(self):
        if not isinstance(self.endpoint, CL.CatalogLinkEndpoint):
            raise TypeError('некорректный аргумент endpoint')
        if any(not isinstance(k, str) for k in (self.source_caption, self.entity_caption)):
            raise TypeError('Некорректный аргумент source_caption/entity_caption')

    @property
    def source_text(self) -> str:
        return self.source_caption or self.endpoint.source_key

    @property
    def entity_text(self) -> str:
        return self.entity_caption or self.endpoint.entity_key



def mes_choices_from_config(config: PMES.PlannerSourceConfig, admin_catalog: PMES.AdminCatalog) -> tuple[CatalogFieldChoice, ...]:
    source = config.source

    # if not source.is_enabled: # todo решить нужно ли блокировать по атрибуту админки
    #     return ()
    if PMES.SourceRole.ATTRIBUTE not in config.roles: # todo
        return ()
    table = None
    if isinstance(admin_catalog, PMES.AdminCatalog):
        table = admin_catalog.tables.get(source.table_key)

    entity_caption = table.table_name if table is not None else source.table_key
    selectable_requisites = sorted(
        (requisite for requisite in config.requisites if requisite.is_selectable),
        key=lambda requisite: (requisite.sort_order, requisite.caption.casefold(), requisite.field_name)
    ) # PMES.PlannerRequisite
    requisites_by_field = {
        requisite.field_name: requisite
        for requisite in selectable_requisites
    }
    fields = []
    if source.identity_field_name:
        identity_requisite = requisites_by_field.get(source.identity_field_name)
        fields.append((
            source.identity_field_name,
            (identity_requisite.caption if identity_requisite is not None else '')
        ))
    fields.extend(
        (requisite.field_name, requisite.caption)
        for requisite in selectable_requisites
    )
    result = []
    used_fields = set()

    for field_name, caption in fields:
        if field_name in used_fields:
            continue
        used_fields.add(field_name)
        field_meta = None
        if isinstance(admin_catalog, PMES.AdminCatalog):
            field_meta = admin_catalog.fields.get((
                source.table_key,
                field_name
            ))
        field_caption = ''
        if caption:
            field_caption = caption
        elif field_meta and field_meta.label:
            field_caption = field_meta.label
        elif field_name:
            field_caption = field_name

        result.append(CatalogFieldChoice(
            endpoint=CL.CatalogLinkEndpoint(
                provider=AB.SourceProvider.MES,
                source_key=source.source_key,
                entity_key=source.table_key,
                field_key=field_name,
                caption=field_caption
            ),
            source_caption=source.caption,
            entity_caption=entity_caption,
        )),
        entity_caption=entity_caption
    return tuple(result)


def load_mes_choices(mes_types: PMES.PlannerMesTypeCatalog) -> tuple[CatalogFieldChoice, ...]:
    runtime = mes_types.session.get_runtime()
    configs = runtime.list_sources(mes_types.subject_code, role=PMES.SourceRole.ATTRIBUTE)
    configs = sorted(configs, key=lambda config: (config.source.sort_order, config.source.caption.casefold(), config.source.source_key))
    result = []
    for config in configs:
        result.extend(mes_choices_from_config(config, runtime.catalog))
    return tuple(result)


if __name__ == '__main__':
    admin_catalog = PMES.AdminCatalog(
        tables={
            'plan': PMES.AdminTable(
                table_key='plan',
                db_key='plan',
                table_name='plan'
            ),
        },
        fields={
            ('plan', 'id'): PMES.AdminField(
                table_key='plan',
                field_name='id',
                label='Идентификатор',
                is_pk=True
            ),
            ('plan', 'client_order_key'): PMES.AdminField(
                table_key='plan',
                field_name='client_order_key',
                label='Ссылка заказа клиента'
            )
        }
    )
