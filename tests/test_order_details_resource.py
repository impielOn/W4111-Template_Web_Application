import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
import os
from dotenv import load_dotenv

import pytest
from app.resources.OrderDetailsResource import OrderDetailsResource, OrderDetailsModel, OrderDetailsCollection

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
    """Fixture to initialize the OrderDetailsResource."""
    config = {"db_url": db_url}
    return OrderDetailsResource(config)


def test_get_by_id(resource):
    # Order 10100 is a standard record in classicmodels
    collection = resource.get_by_id("10100")

    assert isinstance(collection, OrderDetailsCollection)
    assert len(collection.items) > 0
    # Check that all items belong to the requested order
    for item in collection.items:
        assert item.orderNumber == 10100


def test_create_and_delete_lifecycle(resource):
    # Setup: Use existing order and product to satisfy Foreign Key constraints
    # Order 10101 and Product S18_2325 are valid classicmodels data
    test_order_id = 10101
    test_prod_code = "S18_2325"

    # PRE-CLEANUP: Wipe any existing matching row before starting
    resource._service.deleteByTemplate({
        "orderNumber": test_order_id,
        "productCode": test_prod_code
    })

    new_detail = OrderDetailsModel(
        orderNumber=test_order_id,
        productCode=test_prod_code,
        quantityOrdered=30,
        priceEach=120.50,
        orderLineNumber=15
    )

    # 1. Test POST (Create)
    pk = resource.post(new_detail)
    assert pk == str(test_order_id)

    # 2. Verify existence via template
    results = resource.get({"orderNumber": test_order_id, "productCode": test_prod_code})
    assert len(results.items) == 1
    assert results.items[0].quantityOrdered == 30

    # 3. Cleanup: Use the specific delete logic
    # (Assuming you added a method to handle the composite key)
    # If not, we use the service's deleteByTemplate directly
    rows = resource._service.deleteByTemplate({
        "orderNumber": test_order_id,
        "productCode": test_prod_code
    })
    assert rows == 1


def test_put_update(resource):
    # Setup: Target an existing line item
    # Order 10102, Product S18_1342
    target_order = "10102"
    target_product = "S18_1342"

    # Get original to restore later
    original_data = resource.get({
        "orderNumber": target_order,
        "productCode": target_product
    }).items[0]

    try:
        # 1. Update the quantity
        update_model = OrderDetailsModel(
            productCode=target_product,  # Required for our custom PUT logic
            quantityOrdered=original_data.quantityOrdered + 10
        )

        # 2. Test PUT
        rows = resource.put(target_order, update_model)
        assert rows == 1

        # 3. Verify change
        updated = resource.get({
            "orderNumber": target_order,
            "productCode": target_product
        }).items[0]
        assert updated.quantityOrdered == original_data.quantityOrdered + 10

    finally:
        # Restore original state
        restore_model = OrderDetailsModel(
            productCode=target_product,
            quantityOrdered=original_data.quantityOrdered
        )
        resource.put(target_order, restore_model)


def test_get_by_template(resource):
    # Test filtering by a specific product code across all orders
    target_prod = "S10_1678"
    collection = resource.get({"productCode": target_prod})

    assert len(collection.items) > 0
    for item in collection.items:
        assert item.productCode == target_prod