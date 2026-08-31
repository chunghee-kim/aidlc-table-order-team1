from typing import Protocol

from app.models import Table


class TableRepo(Protocol):
    def find_by_number(self, store_id: int, table_number: int) -> Table | None: ...

    def upsert(self, table: Table) -> Table: ...
