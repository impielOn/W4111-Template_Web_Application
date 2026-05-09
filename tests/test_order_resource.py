import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
import os
from datetime import date
from dotenv import load_dotenv

import pytest
from app.resources.OrderResource import OrderResource, OrderModel

# Load env variables
load_dotenv()
db_user = os.getenv("MYSQL_ROOT_USER")
db_pass = os.getenv("MYSQL_ROOT_PASSWORD")
db_host = os.getenv("MYSQL_HOST", "localhost")
db_port = os.getenv("MYSQL_PORT", "3306")
db_name = os.getenv("MYSQL_DB", "classicmodels")
db_url = f"mysql+pymysql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

@pytest.fixture(scope="module")
def resource():
    """Fixture to initialize the OrderResource."""
    config = {"db_url": db_url}
    return OrderResource(config)


def test_get_by_id(resource):
    # Testing with known classicmodels record #10100
    order = resource.get_by_id("10100")

    assert isinstance(order, OrderModel)
    assert order.orderNumber == 10100
    assert order.status == "Shipped"
    assert order.customerNumber == 363


def test_create_and_delete_lifecycle(resource):
    # 1. Define new order data
    # Note: customerNumber 124 (Mini Gifts Distributors Ltd) exists in classicmodels
    new_order_id = 99999
    new_order = OrderModel(
        orderNumber=new_order_id,
        orderDate=date(2023, 10, 1),
        requiredDate=date(2023, 10, 10),
        status="In Process",
        customerNumber=124
    )

    # 2. Test POST (Create)
    pk = resource.post(new_order)
    assert pk == str(new_order_id)

    # 3. Test GET (Retrieve)
    retrieved = resource.get_by_id(str(new_order_id))
    assert retrieved.status == "In Process"
    # Verify Pydantic converted the string from DB back to a date object
    assert isinstance(retrieved.orderDate, date)

    # 4. Test DELETE
    rows_deleted = resource.delete(str(new_order_id))
    assert rows_deleted == 1

    # Verify it's gone
    with pytest.raises(ValueError, match="No order found with number '99999'"):
        resource.get_by_id(str(new_order_id))


def test_put_update(resource):
    # Setup: Create a temporary order to update
    temp_id = "88888"
    resource.post(OrderModel(
        orderNumber=int(temp_id),
        orderDate=date.today(),
        requiredDate=date.today(),
        status="On Hold",
        customerNumber=124
    ))

    try:
        # 1. Update status and add a comment
        update_data = OrderModel(status="Shipped", comments="Test update")

        # 2. Test PUT
        rows_affected = resource.put(temp_id, update_data)
        assert rows_affected == 1

        # 3. Verify changes
        updated_order = resource.get_by_id(temp_id)
        assert updated_order.status == "Shipped"
        assert updated_order.comments == "Test update"

    finally:
        # Cleanup
        resource.delete(temp_id)


def test_get_by_template(resource):
    # Test filtering by status
    template = {"status": "Cancelled"}
    collection = resource.get(template)

    assert len(collection.items) > 0
    for item in collection.items:
        assert item.status == "Cancelled"