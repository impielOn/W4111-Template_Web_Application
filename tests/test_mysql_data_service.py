import sys
import tempfile
from pathlib import Path

import os
from dotenv import load_dotenv

sys.path.append(str(Path(__file__).resolve().parents[1]))
from app.services.MySQLDataService import MySQLDataService


def _make_service():
    # Load env variables from .env file
    load_dotenv()
    # Classicmodels DB config
    db_user = os.getenv("MYSQL_ROOT_USER")
    db_pass = os.getenv("MYSQL_ROOT_PASSWORD")
    db_host = os.getenv("MYSQL_HOST", "localhost")  # Default to localhost
    db_port = os.getenv("MYSQL_PORT", "3306")  # Default MySQL port is 3306
    db_name = os.getenv("MYSQL_DB", "classicmodels")
    db_url = f"mysql+pymysql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

    config = {
        "mysql_url": db_url,
        "table_name": "customers",
        "primary_key_field": "customerNumber"
    }
    service = MySQLDataService(config)
    return service


def test_retrieve_by_primary_key():
    # 1. Setup the service using your updated factory function
    service = _make_service()

    # 2. Define a known ID from the classicmodels database
    # In classicmodels, 103 is "Atelier graphique"
    target_pk = "103"
    # Execute the retrieval
    result = service.retrieveByPrimaryKey(target_pk)
    # Ensure we actually got a dictionary back
    assert isinstance(result, dict), "Result should be a dictionary"
    # Ensure the dictionary isn't empty
    assert len(result) > 0, f"No customer found with ID {target_pk}"
    # Check specific fields from the classicmodels schema
    assert str(result["customerNumber"]) == target_pk
    assert result["customerName"] == "Atelier graphique"
    assert "city" in result
    #print(f"Test Passed: Successfully retrieved {result['customerName']}")


# Test for non-existent primary key retrieval
def test_retrieve_by_primary_key_not_found():
    service = _make_service()
    result = service.retrieveByPrimaryKey("9999999")  # ID that doesn't exist

    assert result == {}, "Expected an empty dictionary for a non-existent PK"


def test_retrieve_by_template():
    service = _make_service()
    # Template to return data
    template = {
        "city": "NYC",
        "country": "USA"
    }
    results = service.retrieveByTemplate(template)
    assert isinstance(results, list), "Expected a list of results"
    assert len(results) > 0, f"No records found for template: {template}"

    # Verifying every returned row matches template
    for row in results:
        assert row["city"] == "NYC"
        assert row["country"] == "USA"
        # Check that we got full records, not just the filtered columns
        assert "customerName" in row
        assert "phone" in row


def test_create(tmp_path):
    service = _make_service()

    # 1. Create a unique ID to avoid "Duplicate Entry" errors
    # In classicmodels, customerNumber is an integer.
    # We'll use a large random integer for testing.
    test_id = 9999

    # 2. Build a payload that satisfies the 'customers' table schema
    # Classicmodels requires certain fields to be NOT NULL
    new_customer = {
        "customerNumber": test_id,
        "customerName": "Gemini Test Corp",
        "contactLastName": "User",
        "contactFirstName": "Gemini",
        "phone": "555-0199",
        "addressLine1": "123 AI Boulevard",
        "city": "New York",
        "country": "USA"
    }

    # 3. Execute the create
    # We wrap this in a try/finally or handle cleanup so we don't
    # pollute the database with every test run.
    try:
        pk = service.create(new_customer)

        # 4. Assertions
        assert pk == str(test_id), "The returned PK should match the input ID"

        # Verify it actually exists in the DB now
        verified_row = service.retrieveByPrimaryKey(str(test_id))
        assert verified_row["customerName"] == "Gemini Test Corp"
        assert verified_row["city"] == "New York"

    finally:
        # 5. Cleanup: Delete the test record so the test is repeatable
        service.deleteByPrimaryKey(str(test_id))
        print(f"Test Passed: Created and cleaned up customer {test_id}")


def test_update_by_primary_key():
    service = _make_service()
    temp_id = "8888"  # High ID unlikely to exist

    # 1. SETUP: Create a dummy record
    dummy_payload = {
        "customerNumber": temp_id,
        "customerName": "Temp Corp",
        "contactLastName": "Tester",
        "contactFirstName": "Dummy",
        "phone": "555-0000",
        "addressLine1": "123 Test St",
        "city": "TestCity",
        "country": "USA"
    }
    service.create(dummy_payload)

    try:
        # 2. TEST: Update this temporary record
        update_data = {"contactFirstName": "Updated-Name"}
        service.updateByPrimaryKey(temp_id, update_data)

        # Verify
        result = service.retrieveByPrimaryKey(temp_id)
        assert result["contactFirstName"] == "Updated-Name"

    finally:
        # 3. TEARDOWN: Delete the temporary record entirely
        service.deleteByPrimaryKey(temp_id)
        print(f"Cleaned up temporary customer {temp_id}.")


def test_delete_by_primary_key():
    service = _make_service()

    # 1. SETUP: Create a temporary record to delete
    # Using a unique ID to avoid collisions
    temp_id = "7777"
    dummy_customer = {
        "customerNumber": temp_id,
        "customerName": "Delete Test Corp",
        "contactLastName": "Disposable",
        "contactFirstName": "Record",
        "phone": "555-0000",
        "addressLine1": "123 Ghost St",
        "city": "LostCity",
        "country": "USA"
    }

    # Ensure it's in the DB first
    service.create(dummy_customer)
    assert service.retrieveByPrimaryKey(temp_id) != {}, "Setup failed: Record not created"

    # 2. TEST: Execute the deletion
    # The method should return 1 (rows affected)
    rows_deleted = service.deleteByPrimaryKey(temp_id)

    # 3. ASSERTIONS
    assert rows_deleted == 1, f"Expected 1 row to be deleted, but got {rows_deleted}"

    # 4. VERIFY: Try to retrieve it again
    # It should return an empty dictionary now
    final_check = service.retrieveByPrimaryKey(temp_id)
    assert final_check == {}, "Record still exists after deletion attempt"

    print(f"Test Passed: Temporary customer {temp_id} was successfully deleted.")


if __name__ == "__main__":
    test_functions = [
        test_retrieve_by_primary_key,
        test_retrieve_by_template,
        test_create,
        test_update_by_primary_key,
        test_delete_by_primary_key,
        test_retrieve_by_primary_key_not_found()
    ]

    for test_func in test_functions:
        with tempfile.TemporaryDirectory() as temp_dir:
            test_func(Path(temp_dir))

    print("All manual test calls passed.")
