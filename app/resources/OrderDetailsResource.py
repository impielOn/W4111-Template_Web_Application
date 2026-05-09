from __future__ import annotations

from pydantic import BaseModel, Field
from .AbstractBaseResource import AbstractBaseResource
from ..services.MySQLDataService import MySQLDataService


class OrderDetailsModel(BaseModel):
    orderNumber: int | None = None
    productCode: str | None = None
    quantityOrdered: int | None = None
    priceEach: float | None = None
    orderLineNumber: int | None = None


class OrderDetailsCollection(BaseModel):
    items: list[OrderDetailsModel] = Field(default_factory=list)


class OrderDetailsResource(AbstractBaseResource):
    def __init__(self, config: dict | None = None) -> None:
        cfg = dict(config or {})
        super().__init__(cfg)
        service_config: dict = {
            "db_url": cfg.get("db_url"),
            "table_name": "orderdetails",
            "primary_key_field": "orderNumber"  # Primary lookup key
        }
        self._service = MySQLDataService(service_config)

    def get(self, template: dict) -> OrderDetailsCollection:
        rows = self._service.retrieveByTemplate(template)
        return OrderDetailsCollection(
            items=[OrderDetailsModel.model_validate(r) for r in rows]
        )

    def get_by_id(self, id: str) -> OrderDetailsCollection:
        """
        In OrderDetails, one ID (orderNumber) returns multiple rows.
        We return a Collection instead of a single Model.
        """
        rows = self._service.retrieveByTemplate({"orderNumber": id})
        return OrderDetailsCollection(
            items=[OrderDetailsModel.model_validate(r) for r in rows]
        )

    def post(self, new_data: OrderDetailsModel) -> str:
        data = new_data.model_dump(exclude_none=True)
        return self._service.create(data)

    def put(self, order_id: str, new_data: OrderDetailsModel) -> int:
        """
        To follow the AbstractBaseResource header, we use 'order_id'.
        HOWEVER, we must also have the 'productCode' inside the 'new_data'
        to know WHICH line item in that order to update.
        """
        if not new_data.productCode:
            raise ValueError("productCode must be provided in the model to update an order detail.")

        # We use a template update because we have two keys
        target_criteria = {
            "orderNumber": order_id,
            "productCode": new_data.productCode
        }

        # Data to change (excluding the keys themselves)
        update_payload = new_data.model_dump(
            exclude={"orderNumber", "productCode"},
            exclude_unset=True
        )

        # This requires your MySQLDataService to have a method for
        # updating based on a template/filter.
        return self._service.updateByTemplate(target_criteria, update_payload)

    def delete(self, id: str) -> int:
        """Deletes ALL line items for a specific order."""
        return self._service.deleteByPrimaryKey(id)