import pytest
from fastapi.testclient import TestClient
from app.main import app

# Skip tests if httpx (dependency for TestClient) is missing
pytest.importorskip("httpx")

client = TestClient(app)


# --- FIXTURES ---

@pytest.fixture
def temp_customer():
    """
    Creates a temporary customer for testing and deletes it after the test.
    """
    cust_id = 8888
    payload = {
        "customerNumber": cust_id,
        "customerName": "FastAPI Test Corp",
        "contactLastName": "Tester",
        "contactFirstName": "Pytest",
        "phone": "555-0101",
        "addressLine1": "123 Test Blvd",
        "city": "Boston",
        "country": "USA"
    }

    # SETUP: Create the resource
    client.post("/customers", json=payload)

    yield cust_id  # This is where the test runs

    # TEARDOWN: Clean up even if the test fails
    client.delete(f"/customers/{cust_id}")


@pytest.fixture
def temp_order_detail():
    """
    Creates a temporary order detail line for an existing order (10100).
    Deletes the specific line after the test.
    """
    order_id = 10100
    prod_code = "S10_4757"  # Ensure this product isn't already in order 10100

    payload = {
        "orderNumber": order_id,
        "productCode": prod_code,
        "quantityOrdered": 1,
        "priceEach": 50.00,
        "orderLineNumber": 99
    }

    # SETUP: Create line item
    client.post("/orderdetails", json=payload)

    yield order_id, prod_code

    # TEARDOWN: Surgical delete of just this line
    client.delete(f"/orders/{order_id}/orderdetails/{prod_code}")


# --- BASIC ENDPOINT TESTS ---

def test_health() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_root() -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json() == {"message": "Hello from FastAPI"}


# --- CUSTOMER RESOURCE TESTS ---

def test_get_customer(temp_customer):
    resp = client.get(f"/customers/{temp_customer}")
    assert resp.status_code == 200
    assert resp.json()["customerNumber"] == temp_customer


def test_update_customer(temp_customer):
    update_payload = {"customerName": "Updated Name"}
    resp = client.put(f"/customers/{temp_customer}", json=update_payload)
    assert resp.status_code == 200

    # Verify update persisted
    verify = client.get(f"/customers/{temp_customer}")
    assert verify.json()["customerName"] == "Updated Name"


def test_customer_filtering():
    # Test listing with template search
    resp = client.get("/customers?city=NYC")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    for item in data["items"]:
        assert item["city"] == "NYC"


# --- ORDER DETAILS TESTS ---

def test_get_specific_order_detail(temp_order_detail):
    order_id, prod_code = temp_order_detail
    resp = client.get(f"/orders/{order_id}/orderdetails/{prod_code}")
    assert resp.status_code == 200
    assert resp.json()["productCode"] == prod_code
    assert resp.json()["orderNumber"] == order_id


def test_update_order_detail(temp_order_detail):
    order_id, prod_code = temp_order_detail
    # Update quantity for this specific line
    update_payload = {"productCode": prod_code, "quantityOrdered": 100}

    resp = client.put(f"/orders/{order_id}/orderdetails/{prod_code}", json=update_payload)
    assert resp.status_code == 200
    assert resp.json()["updated"] == 1

    # Double check value
    verify = client.get(f"/orders/{order_id}/orderdetails/{prod_code}")
    assert verify.json()["quantityOrdered"] == 100


# --- ERROR HANDLING TESTS ---

def test_get_invalid_customer():
    resp = client.get("/customers/999999999")
    assert resp.status_code == 404


def test_put_invalid_order_detail():
    # Attempting to update a line that doesn't exist
    update_payload = {"productCode": "NONEXISTENT", "quantityOrdered": 5}
    resp = client.put("/orders/10100/orderdetails/NONEXISTENT", json=update_payload)

    # Depending on your implementation, this might be 400 or return updated: 0
    assert resp.status_code in [200, 400, 404]