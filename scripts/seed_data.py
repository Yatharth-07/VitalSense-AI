from __future__ import annotations

import json
import sys
from typing import Any, Dict, List
import requests

RAW_TEST_RECORDS: List[Dict[str, Any]] = [
    {
        "test_id": 1,
        "full_name": "Robyn Pears",
        "date_of_birth": "28.01.1960",
        "email": "robyn@gmail.com",
        "glucose": 232.0,
        "haemoglobin": 13.5,
        "cholesterol": 180.0,
        "expected_result": "ACCEPT",
        "expected_reason": "Valid date, valid email, numeric measurements."
    },
    {
        "test_id": 2,
        "full_name": "John Hunter",
        "date_of_birth": "10.12.1990",
        "email": "hunter@gmail",
        "glucose": 94.0,
        "haemoglobin": 15.0,
        "cholesterol": 200.0,
        "expected_result": "REJECT",
        "expected_reason": "Malformed email address (missing valid domain extension)."
    },
    {
        "test_id": 3,
        "full_name": "Darryl Tim",
        "date_of_birth": "12.11.1993",
        "email": "timd@smh.com.au",
        "glucose": 240.0,
        "haemoglobin": 18.6,
        "cholesterol": 326.0,
        "expected_result": "ACCEPT",
        "expected_reason": "Valid date and email, numeric measurements."
    },
    {
        "test_id": 4,
        "full_name": "Peter Larry",
        "date_of_birth": "31.11.2001",
        "email": "Larry@hotmail.com",
        "glucose": 88.0,
        "haemoglobin": 11.5,
        "cholesterol": 165.0,
        "expected_result": "REJECT",
        "expected_reason": "Invalid calendar date (November has only 30 days)."
    },
    {
        "test_id": 5,
        "full_name": "Sam Kerr",
        "date_of_birth": "09.12.2006",
        "email": "sam@news.com.au",
        "glucose": 198.0,
        "haemoglobin": 8.9,
        "cholesterol": 192.0,
        "expected_result": "ACCEPT",
        "expected_reason": "Valid date, email, numeric measurements."
    },
    {
        "test_id": 6,
        "full_name": "Robyn Pears",
        "date_of_birth": "28.01.1960",
        "email": "robyn@gmail.com",
        "glucose": 232.0,
        "haemoglobin": 13.5,
        "cholesterol": 180.0,
        "expected_result": "ACCEPT",
        "expected_reason": "Duplicate entry explicitly permitted by assignment instructions."
    },
    {
        "test_id": 7,
        "full_name": "Madison XI",
        "date_of_birth": "12.09.1998",
        "email": "madison@hotmail.com",
        "glucose": 85.0,
        "haemoglobin": 7.6,
        "cholesterol": 163.0,
        "expected_result": "ACCEPT",
        "expected_reason": "Numerically valid measurement (7.6 Hb is low but clinically valid, not rejected)."
    },
    {
        "test_id": 8,
        "full_name": "Kris Wu",
        "date_of_birth": "19.10.2030",
        "email": "Kris.wu.gmail.com",
        "glucose": 79.0,
        "haemoglobin": 16.5,
        "cholesterol": 197.0,
        "expected_result": "REJECT",
        "expected_reason": "Two validation errors: Future date of birth (2030) and missing @ in email."
    },
    {
        "test_id": 9,
        "full_name": "Tenille Singh",
        "date_of_birth": "30.11.1991",
        "email": "Tenille@yahoo.com",
        "glucose": 101.0,
        "haemoglobin": 15.0,
        "cholesterol": 310.0,
        "expected_result": "ACCEPT",
        "expected_reason": "Valid date, email, numeric measurements."
    },
    {
        "test_id": 10,
        "full_name": "Prem Kumar",
        "date_of_birth": "28.04.1990",
        "email": "prem@telstra.com",
        "glucose": 155.0,
        "haemoglobin": 12.5,
        "cholesterol": 265.0,
        "expected_result": "ACCEPT",
        "expected_reason": "Valid date, email, numeric measurements."
    }
]


def run_seed_import(api_base_url: str = "http://127.0.0.1:8000/api") -> Dict[str, Any]:
    """Sends the 10 test records to the backend batch-import endpoint and prints results."""
    url = f"{api_base_url}/patients/batch-import"
    print(f"Connecting to VitalSense API at {url}...")
    try:
        response = requests.post(url, json=RAW_TEST_RECORDS, timeout=10.0)
        response.raise_for_status()
        summary = response.json()

        print("\n" + "="*60)
        print("          VITALSENSE AI — 10 TEST CASES VERIFICATION       ")
        print("="*60)
        print(f"Total Submitted Records: {summary['total_submitted']}")
        print(f"Valid Records Accepted : {summary['valid_records']} (Expected: 7)")
        print(f"Invalid Records Rejected: {summary['invalid_records']} (Expected: 3)")
        print(f"Accepted Duplicates    : {summary['accepted_duplicates']} (Expected: 1)")
        print(f"Invalid Email Records  : {summary['invalid_email_count']} (Expected: 2)")
        print(f"Invalid Date Records   : {summary['invalid_date_count']} (Expected: 2)")
        print("-"*60)
        print("DETAILS PER TEST CASE:")
        for res in summary['results']:
            status_flag = "[OK] ACCEPTED" if res['status'] == "ACCEPTED" else "[X] REJECTED"
            print(f"Test #{res['test_index']:02d}: {res['full_name']:<15} -> {status_flag}")
            if res['errors']:
                for field, errs in res['errors'].items():
                    print(f"    - {field}: {', '.join(errs)}")
        print("="*60 + "\n")
        return summary
    except requests.exceptions.RequestException as exc:
        print(f"Error communicating with API: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    run_seed_import()
