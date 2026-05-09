import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
import os
from dotenv import load_dotenv

import pytest
from app.resources.CustomerResource import CustomerResource, CustomerModel

# Load env variables from .env file
load_dotenv()
# Classicmodels DB config
db_user = os.getenv("MYSQL_ROOT_USER")
db_pass = os.getenv("MYSQL_ROOT_PASSWORD")
db_host = os.getenv("MYSQL_HOST", "localhost")  # Default to localhost
db_port = os.getenv("MYSQL_PORT", "3306")  # Default MySQL port is 3306
db_name = os.getenv("MYSQL_DB", "classicmodels")
db_url = f"mysql+pymysql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

@pytest.fixture(scope="module")
def resource():
    """Fixture to initialize the resource once for all tests in this file."""
    config = {"db_url": db_url}
    return CustomerResource(config)


def test_get_by_id(resource):
    # Testing with a known classicmodels record
    customer = resource.get_by_id("103")

    assert isinstance(customer, CustomerModel)
    assert customer.customerNumber == 103
    assert customer.contactFirstName == "Carine "
    assert customer.customerName == "Atelier graphique"


def test_create_and_delete_lifecycle(resource):
    # 1. Define new data
    new_cust_id = 9999
    new_cust = CustomerModel(
        customerNumber=new_cust_id,
        customerName="Gemini Logistics",
        contactFirstName="Test",
        contactLastName="User",
        phone="555-1234",
        addressLine1="123 AI Lane",
        city="New York",
        country="USA"
    )

    # 2. Test POST (Create)
    pk = resource.post(new_cust)
    assert pk == str(new_cust_id)

    # 3. Test GET (Retrieve)
    retrieved = resource.get_by_id(str(new_cust_id))
    assert retrieved.customerName == "Gemini Logistics"

    # 4. Test DELETE
    rows_deleted = resource.delete(str(new_cust_id))
    assert rows_deleted == 1

    # Verify it's gone
    with pytest.raises(ValueError, match="No customer with id '9999'"):
        resource.get_by_id(str(new_cust_id))


def test_put_update(resource):
    # Setup: Create a temporary record to update
    temp_id = "8888"
    resource.post(CustomerModel(
        customerNumber=int(temp_id), customerName="Update Test",
        contactFirstName="Old", contactLastName="Name",
        phone="123", addressLine1="123", city="NY", country="USA"
    ))

    try:
        # 1. Define update data (Changing only the first name)
        update_data = CustomerModel(contactFirstName="New")

        # 2. Test PUT
        rows_affected = resource.put(temp_id, update_data)
        assert rows_affected == 1

        # 3. Verify change
        updated_cust = resource.get_by_id(temp_id)
        assert updated_cust.contactFirstName == "New"
        assert updated_cust.customerName == "Update Test"  # Should remain unchanged

    finally:
        # Cleanup
        resource.delete(temp_id)


def test_get_by_template(resource):
    # Test filtering by city
    template = {"city": "NYC"}
    collection = resource.get(template)

    assert len(collection.items) > 0
    for item in collection.items:
        assert item.city == "NYC"