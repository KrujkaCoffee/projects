import json
import os
import pathlib
import tempfile

from project_cust_38.sub_mes.resource_planning import catalog_link as CL

class CatalogLinkStore:
    def __init__(self, path: str | pathlib.Path):
        self.path = pathlib.Path(path).expanduser().resolve()

    def load(self):
        try:
            with self.path.open('r', encoding='utf-8') as stream:
                data = json.load(stream)
        except FileNotFoundError:
            return CL.CatalogLinkManager()
        if (not isinstance(data, dict)
            or data.get('format') != 'catalog_links'
            or data.get('version') != 1):
            raise ValueError('Неподдерживаемый формат файла связей')
        return CL.CatalogLinkManager.from_list(data['links'])

    def save(self, manager: CL.CatalogLinkManager):
        text = json.dumps(
            {
                'format': 'catalog_links',
                'version': 1,
                'links': manager.to_list()
            },
            ensure_ascii=False,
            indent=2
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode='w',
                encoding='utf-8',
                dir=self.path.parent,
                prefix=self.path.name + '.',
                suffix='.tmp',
                delete=False
            ) as stream:
                temporary_path = pathlib.Path(stream.name)
                stream.write(text)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_path, self.path)
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
