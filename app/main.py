from __future__ import annotations
import os
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

# Ensure app is in path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.resources.CustomerResource import CustomerResource, CustomerModel, CustomerCollection
from app.resources.OrderResource import OrderResource, OrderModel, OrderCollection
from app.resources.OrderDetailsResource import OrderDetailsResource, OrderDetailsModel, OrderDetailsCollection

def _get_app_name() -> str:
    return os.getenv("APP_NAME", "ClassicModels API")

app = FastAPI(title=_get_app_name(), version="0.1.0")

# Initialize Resources
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
import os
from dotenv import load_dotenv

# Load env variables
load_dotenv()
# .env only contains MYSQL_ROOT_USER and MYSQL_ROOT_PASSWORD in original setup
db_user = os.getenv("MYSQL_ROOT_USER")
db_pass = os.getenv("MYSQL_ROOT_PASSWORD")
db_host = os.getenv("MYSQL_HOST", "localhost")
db_port = os.getenv("MYSQL_PORT", "3306")
db_name = os.getenv("MYSQL_DB", "classicmodels")
db_url = f"mysql+pymysql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
config = {"db_url": db_url} if db_url else {}

customer_res = CustomerResource(config)
order_res = OrderResource(config)
order_details_res = OrderDetailsResource(config)

# --- GENERAL ---

class EchoRequest(BaseModel):
    message: str

@app.get("/", tags=["root"])
def read_root() -> dict[str, str]:
    return {"message": "Hello from FastAPI"}


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/echo", tags=["echo"])
def echo(payload: EchoRequest) -> EchoRequest:
    return payload

# --- CUSTOMERS ---

@app.get("/customers", tags=["Customers"])
def get_customers(request: Request) -> CustomerCollection:
    template = dict(request.query_params)
    return customer_res.get(template)

@app.get("/customers/{customerNumber}", tags=["Customers"])
def get_customer(customerNumber: str) -> CustomerModel:
    try:
        return customer_res.get_by_id(customerNumber)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

@app.post("/customers", tags=["Customers"], status_code=201)
def create_customer(new_data: CustomerModel) -> str:
    return customer_res.post(new_data)

@app.put("/customers/{customerNumber}", tags=["Customers"])
def update_customer(customerNumber: str, new_data: CustomerModel):
    updated = customer_res.put(customerNumber, new_data)
    return {"updated": updated}

@app.delete("/customers/{customerNumber}", tags=["Customers"])
def delete_customer(customerNumber: str):
    deleted = customer_res.delete(customerNumber)
    return {"deleted": deleted}

# --- ORDERS ---

@app.get("/orders", tags=["Orders"])
def get_orders(request: Request) -> OrderCollection:
    template = dict(request.query_params)
    return order_res.get(template)

@app.get("/orders/{orderNumber}", tags=["Orders"])
def get_order(orderNumber: str) -> OrderModel:
    try:
        return order_res.get_by_id(orderNumber)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

@app.post("/orders", tags=["Orders"], status_code=201)
def create_order(new_data: OrderModel) -> str:
    return order_res.post(new_data)

@app.put("/orders/{orderNumber}", tags=["Orders"])
def update_order(orderNumber: str, new_data: OrderModel):
    updated = order_res.put(orderNumber, new_data)
    return {"updated": updated}

@app.delete("/orders/{orderNumber}", tags=["Orders"])
def delete_order(orderNumber: str):
    deleted = order_res.delete(orderNumber)
    return {"deleted": deleted}

# --- ORDER DETAILS (Composite Key Logic) ---

@app.get("/orderdetails", tags=["OrderDetails"])
def get_all_order_details(request: Request) -> OrderDetailsCollection:
    """Lists order details, supporting filters like ?productCode=S10_1678"""
    template = dict(request.query_params)
    return order_details_res.get(template)

@app.post("/orderdetails", tags=["OrderDetails"], status_code=201)
def create_order_detail(new_data: OrderDetailsModel) -> str:
    return order_details_res.post(new_data)

@app.get("/orders/{orderNumber}/orderdetails", tags=["OrderDetails"])
def get_order_details_by_order(orderNumber: str) -> OrderDetailsCollection:
    """Returns all line items for a specific order."""
    return order_details_res.get_by_id(orderNumber)

@app.get("/orders/{orderNumber}/orderdetails/{productCode}", tags=["OrderDetails"])
def get_specific_order_detail(orderNumber: str, productCode: str) -> OrderDetailsModel:
    """Unambiguously identifies a single row by Order and Product."""
    results = order_details_res.get({"orderNumber": orderNumber, "productCode": productCode})
    if not results.items:
        raise HTTPException(status_code=404, detail="Order detail line not found")
    return results.items[0]

@app.put("/orders/{orderNumber}/orderdetails/{productCode}", tags=["OrderDetails"])
def update_order_detail(orderNumber: str, productCode: str, new_data: OrderDetailsModel):
    # Inject productCode into the model to satisfy the composite update logic
    new_data.productCode = productCode
    try:
        updated = order_details_res.put(orderNumber, new_data)
        return {"updated": updated}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.delete("/orders/{orderNumber}/orderdetails/{productCode}", tags=["OrderDetails"])
def delete_order_detail(orderNumber: str, productCode: str):
    # Use the service's deleteByTemplate for surgical deletion of one line
    deleted = order_details_res._service.deleteByTemplate({
        "orderNumber": orderNumber,
        "productCode": productCode
    })
    return {"deleted": deleted}

if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))

    uvicorn.run(app, host=host, port=port)

