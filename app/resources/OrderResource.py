from __future__ import annotations

from datetime import date
from pydantic import BaseModel, Field

from .AbstractBaseResource import AbstractBaseResource
from ..services.MySQLDataService import MySQLDataService


class OrderModel(BaseModel):
    orderNumber: int | None = None  # Primary Key
    orderDate: date | None = None  # Not null in DB
    requiredDate: date | None = None  # Not null in DB
    shippedDate: date | None = None  # NULL if not yet shipped
    status: str = ""
    comments: str | None = None
    customerNumber: int | None = None  # FK for Customers, not null in DB


class OrderCollection(BaseModel):
    items: list[OrderModel] = Field(default_factory=list)


class OrderResource(AbstractBaseResource):
    def __init__(self, config: dict | None = None) -> None:
        cfg = dict(config or {})
        super().__init__(cfg)
        # DB connection info
        service_config: dict = {
            "db_url": cfg.get("db_url"),
            "table_name": "orders",
            "primary_key_field": "orderNumber"  # PK for orders table
        }
        self._service = MySQLDataService(service_config)

    def get(self, template: dict) -> OrderCollection:
        rows = self._service.retrieveByTemplate(template)
        return OrderCollection(
            items=[OrderModel.model_validate(r) for r in rows]
        )

    def get_by_id(self, id: str) -> OrderModel:  # noqa: A002
        row = self._service.retrieveByPrimaryKey(str(id))
        if not row:
            # Row will be {} if not found based on Service implementation
            raise ValueError(f"No order found with number {id!r}")
        return OrderModel.model_validate(row)

    def post(self, new_data: OrderModel) -> str:
        data = new_data.model_dump()
        # DB set to AUTO_INCREMENT for ID generation
        return self._service.create(data)

    def delete(self, id: str) -> int:  # noqa: A002
        return self._service.deleteByPrimaryKey(str(id))

    def put(self, order_id: str, new_data: OrderModel) -> int:
        # Filter out the PK from the update body to prevent SQL errors
        data = new_data.model_dump(exclude={"orderNumber"}, exclude_unset=True)
        return self._service.updateByPrimaryKey(order_id, data)
