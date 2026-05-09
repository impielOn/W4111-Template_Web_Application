from __future__ import annotations

from pydantic import BaseModel, Field

from .AbstractBaseResource import AbstractBaseResource
from ..services.MySQLDataService import MySQLDataService


class CustomerModel(BaseModel):
    customerNumber: int | None = None  # Primary key, not null in MySQL
    customerName: str = ""
    contactLastName: str = ""
    contactFirstName: str = ""
    phone: str = ""
    addressLine1: str = ""
    addressLine2: str | None = None  # Often NULL in the DB
    city: str = ""
    state: str | None = None  # Often NULL for international customers
    postalCode: str | None = None  # New
    country: str = ""
    salesRepEmployeeNumber: int | None = None  # Foreign Key to Employees
    creditLimit: float | None = None  # Decimal/Double in MySQL


class CustomerCollection(BaseModel):
    items: list[CustomerModel] = Field(default_factory=list)


class CustomerResource(AbstractBaseResource):
    def __init__(self, config: dict | None = None) -> None:
        cfg = dict(config or {})
        super().__init__(cfg)
        # DB connection info
        service_config: dict = {
            "db_url": cfg.get("db_url"),
            "table_name": "customers",
            "primary_key_field": "customerNumber"  # PK for customers table
        }
        self._service = MySQLDataService(service_config)

    def get(self, template: dict) -> CustomerCollection:
        rows = self._service.retrieveByTemplate(template)
        return CustomerCollection(
            items=[CustomerModel.model_validate(r) for r in rows]
        )

    def get_by_id(self, id: str) -> CustomerModel:  # noqa: A002
        row = self._service.retrieveByPrimaryKey(str(id))
        if not row:
            # Row will be {} if not found based on Service implementation
            raise ValueError(f"No customer with id {id!r}")
        return CustomerModel.model_validate(row)

    def post(self, new_data: CustomerModel) -> str:
        data = new_data.model_dump()
        # DB set to AUTO_INCREMENT for ID generation
        return self._service.create(data)

    def delete(self, id: str) -> int:  # noqa: A002
        return self._service.deleteByPrimaryKey(str(id))

    def put(self, customer_id: str, new_data: CustomerModel) -> int:
        # Filter out the PK from the update body to prevent SQL errors
        data = new_data.model_dump(exclude={"customerNumber"}, exclude_unset=True)
        return self._service.updateByPrimaryKey(customer_id, data)
