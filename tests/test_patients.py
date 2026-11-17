from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from scripts.seed_data import RAW_TEST_RECORDS


class TestPatientAPI:

    def test_create_valid_patient(self, client: TestClient):
        payload = {
            "full_name": "Robyn Pears",
            "date_of_birth": "28.01.1960",
            "email": "robyn@gmail.com",
            "glucose": 232.0,
            "haemoglobin": 13.5,
            "cholesterol": 180.0
        }
        response = client.post("/api/patients", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["id"] is not None
        assert data["full_name"] == "Robyn Pears"
        assert data["email"] == "robyn@gmail.com"
        assert data["date_of_birth_display"] == "28/01/1960"
        assert data["remarks"] is not None
        assert "SUMMARY:" in data["remarks"]

    def test_create_invalid_patient_rejected(self, client: TestClient):
        # Test 2: John Hunter has invalid email
        payload = {
            "full_name": "John Hunter",
            "date_of_birth": "10.12.1990",
            "email": "hunter@gmail",
            "glucose": 94.0,
            "haemoglobin": 15.0,
            "cholesterol": 200.0
        }
        response = client.post("/api/patients", json=payload)
        assert response.status_code == 422
        body = response.json()
        assert "errors" in body["detail"]
        assert "email" in body["detail"]["errors"]

    def test_get_all_patients_and_search(self, client: TestClient):
        # Create two patients
        client.post("/api/patients", json={
            "full_name": "Sam Kerr",
            "date_of_birth": "09.12.2006",
            "email": "sam@news.com.au",
            "glucose": 198.0,
            "haemoglobin": 8.9,
            "cholesterol": 192.0
        })
        client.post("/api/patients", json={
            "full_name": "Tenille Singh",
            "date_of_birth": "30.11.1991",
            "email": "Tenille@yahoo.com",
            "glucose": 101.0,
            "haemoglobin": 15.0,
            "cholesterol": 310.0
        })

        # Get all
        res_all = client.get("/api/patients")
        assert res_all.status_code == 200
        items = res_all.json()
        assert len(items) == 2

        # Search by name
        res_search = client.get("/api/patients?search=Kerr")
        assert res_search.status_code == 200
        search_items = res_search.json()
        assert len(search_items) == 1
        assert search_items[0]["full_name"] == "Sam Kerr"

    def test_get_patient_by_id_and_not_found(self, client: TestClient):
        created = client.post("/api/patients", json={
            "full_name": "Prem Kumar",
            "date_of_birth": "28.04.1990",
            "email": "prem@telstra.com",
            "glucose": 155.0,
            "haemoglobin": 12.5,
            "cholesterol": 265.0
        }).json()

        # Success fetch
        res = client.get(f"/api/patients/{created['id']}")
        assert res.status_code == 200
        assert res.json()["full_name"] == "Prem Kumar"

        # 404 for non-existent ID
        res_missing = client.get("/api/patients/99999")
        assert res_missing.status_code == 404

    def test_update_patient_email_and_metrics(self, client: TestClient):
        created = client.post("/api/patients", json={
            "full_name": "Darryl Tim",
            "date_of_birth": "12.11.1993",
            "email": "timd@smh.com.au",
            "glucose": 240.0,
            "haemoglobin": 18.6,
            "cholesterol": 326.0
        }).json()

        patient_id = created["id"]
        original_remarks = created["remarks"]

        # Step 5 from prompt: Update email address to gokul@infocare.com
        update_payload = {
            "email": "gokul@infocare.com"
        }
        res_update = client.put(f"/api/patients/{patient_id}", json=update_payload)
        assert res_update.status_code == 200
        updated = res_update.json()
        assert updated["email"] == "gokul@infocare.com"
        # Remarks unchanged since blood test values were not modified
        assert updated["remarks"] == original_remarks

        # Now update blood test values -> should regenerate AI remarks
        res_metrics = client.put(f"/api/patients/{patient_id}", json={
            "glucose": 95.0,
            "haemoglobin": 14.0,
            "cholesterol": 175.0
        })
        assert res_metrics.status_code == 200
        metrics_updated = res_metrics.json()
        assert metrics_updated["glucose"] == 95.0
        assert metrics_updated["remarks"] != original_remarks

    def test_delete_patient(self, client: TestClient):
        created = client.post("/api/patients", json={
            "full_name": "Robyn Pears",
            "date_of_birth": "28.01.1960",
            "email": "robyn@gmail.com",
            "glucose": 232.0,
            "haemoglobin": 13.5,
            "cholesterol": 180.0
        }).json()
        patient_id = created["id"]

        # Delete
        del_res = client.delete(f"/api/patients/{patient_id}")
        assert del_res.status_code == 200

        # Confirm deleted from DB
        get_res = client.get(f"/api/patients/{patient_id}")
        assert get_res.status_code == 404

        # Deleting non-existent returns 404
        del_again = client.delete(f"/api/patients/{patient_id}")
        assert del_again.status_code == 404

    def test_duplicate_robyn_pears_records_both_accepted(self, client: TestClient):
        """
        Tests 1 and 6 both submit Robyn Pears.
        Both records must be accepted and persisted with distinct IDs.
        """
        payload = {
            "full_name": "Robyn Pears",
            "date_of_birth": "28.01.1960",
            "email": "robyn@gmail.com",
            "glucose": 232.0,
            "haemoglobin": 13.5,
            "cholesterol": 180.0
        }
        res1 = client.post("/api/patients", json=payload)
        res2 = client.post("/api/patients", json=payload)

        assert res1.status_code == 201
        assert res2.status_code == 201
        assert res1.json()["id"] != res2.json()["id"]

    def test_batch_import_ten_test_records_exact_results(self, client: TestClient):
        """
        Verifies the exact assignment specifications from Section 10:
        Total submitted: 10
        Valid records: 7
        Invalid records: 3
        Accepted duplicates: 1
        Invalid email records: 2
        Invalid date records: 2
        """
        res = client.post("/api/patients/batch-import", json=RAW_TEST_RECORDS)
        assert res.status_code == 200
        summary = res.json()

        assert summary["total_submitted"] == 10
        assert summary["valid_records"] == 7
        assert summary["invalid_records"] == 3
        assert summary["accepted_duplicates"] == 1
        assert summary["invalid_email_count"] == 2
        assert summary["invalid_date_count"] == 2

        # Check individual test statuses
        results = summary["results"]
        # Test 1: Robyn Pears -> Accepted
        assert results[0]["status"] == "ACCEPTED"
        # Test 2: John Hunter -> Rejected (email)
        assert results[1]["status"] == "REJECTED"
        assert "email" in results[1]["errors"]
        # Test 3: Darryl Tim -> Accepted
        assert results[2]["status"] == "ACCEPTED"
        # Test 4: Peter Larry -> Rejected (Nov 31)
        assert results[3]["status"] == "REJECTED"
        assert "date_of_birth" in results[3]["errors"]
        # Test 5: Sam Kerr -> Accepted
        assert results[4]["status"] == "ACCEPTED"
        # Test 6: Robyn Pears (Duplicate) -> Accepted
        assert results[5]["status"] == "ACCEPTED"
        # Test 7: Madison XI -> Accepted
        assert results[6]["status"] == "ACCEPTED"
        # Test 8: Kris Wu -> Rejected (both date and email)
        assert results[7]["status"] == "REJECTED"
        assert "date_of_birth" in results[7]["errors"]
        assert "email" in results[7]["errors"]
        # Test 9: Tenille Singh -> Accepted
        assert results[8]["status"] == "ACCEPTED"
        # Test 10: Prem Kumar -> Accepted
        assert results[9]["status"] == "ACCEPTED"
