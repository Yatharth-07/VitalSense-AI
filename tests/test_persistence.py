from __future__ import annotations

import os
from datetime import date
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.patient import Patient
from app.repositories.patient_repository import PatientRepository


class TestDatabasePersistence:

    @pytest.fixture
    def file_db_path(self, tmp_path):
        db_file = tmp_path / "test_persistence.db"
        return str(db_file)

    def test_persistence_across_session_and_restart(self, file_db_path: str):
        db_url = f"sqlite:///{file_db_path}"
        engine = create_engine(db_url, connect_args={"check_same_thread": False})
        SessionMaker = sessionmaker(bind=engine)

        # 1. Create table and save a patient record in first connection
        Base.metadata.create_all(bind=engine)
        session1 = SessionMaker()
        repo1 = PatientRepository(session1)

        p1 = Patient(
            full_name="Sam Kerr",
            date_of_birth=date(2006, 12, 9),
            email="sam@news.com.au",
            glucose=198.0,
            haemoglobin=8.9,
            cholesterol=192.0,
            remarks="Initial remarks"
        )
        saved = repo1.create(p1)
        patient_id = saved.id
        session1.close()
        engine.dispose()

        # 2. Re-open database from disk simulating application restart
        engine2 = create_engine(db_url, connect_args={"check_same_thread": False})
        SessionMaker2 = sessionmaker(bind=engine2)
        session2 = SessionMaker2()
        repo2 = PatientRepository(session2)

        fetched = repo2.get_by_id(patient_id)
        assert fetched is not None
        assert fetched.full_name == "Sam Kerr"
        assert fetched.email == "sam@news.com.au"
        assert fetched.glucose == 198.0

        # 3. Update record and verify it persists
        repo2.update(fetched, {"email": "gokul@infocare.com"})
        session2.close()
        engine2.dispose()

        # 4. Re-open again and verify update was saved
        engine3 = create_engine(db_url, connect_args={"check_same_thread": False})
        SessionMaker3 = sessionmaker(bind=engine3)
        session3 = SessionMaker3()
        repo3 = PatientRepository(session3)

        updated_fetched = repo3.get_by_id(patient_id)
        assert updated_fetched.email == "gokul@infocare.com"

        # 5. Delete and verify it remains deleted
        repo3.delete(updated_fetched)
        session3.close()
        engine3.dispose()

        # 6. Check final deletion
        engine4 = create_engine(db_url, connect_args={"check_same_thread": False})
        session4 = sessionmaker(bind=engine4)()
        assert PatientRepository(session4).get_by_id(patient_id) is None
        session4.close()
        engine4.dispose()
