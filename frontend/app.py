from __future__ import annotations

import os
import sys
from datetime import date
from typing import Any, Dict, List, Optional
import requests
import streamlit as st

# Ensure project root is in Python module search path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from app.core.database import SessionLocal, engine, Base
from app.models.patient import Patient
from app.repositories.patient_repository import PatientRepository
from app.services.health_insights_service import HealthInsightsService
from app.services.patient_service import PatientService
from app.core.exceptions import ValidationException, PatientNotFoundException
from frontend.components.patient_form import render_patient_form
from frontend.components.patient_table import render_patient_table
from frontend.components.health_insights import render_health_insights_view
from frontend.components.batch_import import render_batch_import_view

# Streamlit Page Config
st.set_page_config(
    page_title="VitalSense AI — Patient Health Insights & Blood Test Management",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database schema automatically
Base.metadata.create_all(bind=engine)


def load_custom_css():
    """Injects custom CSS styling."""
    css_path = os.path.join(os.path.dirname(__file__), "styles", "custom.css")
    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


load_custom_css()


class BackendClient:
    """
    Unified client: Attempts HTTP connection to FastAPI backend first;
    gracefully uses local Python Service layer if backend server is not running separately.
    Guarantees seamless offline evaluation and interview demonstration.
    """

    def __init__(self, api_url: str = settings.API_BASE_URL):
        self.api_url = api_url.rstrip("/")

    def is_api_alive(self) -> bool:
        try:
            r = requests.get(f"{self.api_url}/health", timeout=1.0)
            return r.status_code == 200
        except Exception:
            return False

    def get_service(self) -> PatientService:
        db = SessionLocal()
        repo = PatientRepository(db)
        insights = HealthInsightsService()
        return PatientService(repo, insights)

    def get_all_patients(self, search: Optional[str] = None) -> List[Dict[str, Any]]:
        if self.is_api_alive():
            params = {"search": search} if search else {}
            r = requests.get(f"{self.api_url}/patients", params=params, timeout=5.0)
            return r.json()
        else:
            db = SessionLocal()
            try:
                repo = PatientRepository(db)
                records = repo.get_all(search=search)
                from app.schemas.patient import PatientResponse
                return [PatientResponse.from_orm_patient(p).model_dump() for p in records]
            finally:
                db.close()

    def get_patient(self, patient_id: int) -> Optional[Dict[str, Any]]:
        if self.is_api_alive():
            r = requests.get(f"{self.api_url}/patients/{patient_id}", timeout=5.0)
            return r.json() if r.status_code == 200 else None
        else:
            db = SessionLocal()
            try:
                repo = PatientRepository(db)
                p = repo.get_by_id(patient_id)
                from app.schemas.patient import PatientResponse
                return PatientResponse.from_orm_patient(p).model_dump() if p else None
            finally:
                db.close()

    def create_patient(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if self.is_api_alive():
            r = requests.post(f"{self.api_url}/patients", json=payload, timeout=8.0)
            if r.status_code == 422:
                err_body = r.json()
                detail = err_body.get("detail", {})
                raise ValidationException(detail.get("errors", {}))
            r.raise_for_status()
            return r.json()
        else:
            service = self.get_service()
            try:
                res = service.create_patient(payload)
                return res.model_dump()
            finally:
                service.repository.db.close()

    def update_patient(self, patient_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        if self.is_api_alive():
            r = requests.put(f"{self.api_url}/patients/{patient_id}", json=payload, timeout=8.0)
            if r.status_code == 422:
                err_body = r.json()
                detail = err_body.get("detail", {})
                raise ValidationException(detail.get("errors", {}))
            r.raise_for_status()
            return r.json()
        else:
            service = self.get_service()
            try:
                res = service.update_patient(patient_id, payload)
                return res.model_dump()
            finally:
                service.repository.db.close()

    def delete_patient(self, patient_id: int) -> bool:
        if self.is_api_alive():
            r = requests.delete(f"{self.api_url}/patients/{patient_id}", timeout=5.0)
            return r.status_code == 200
        else:
            service = self.get_service()
            try:
                return service.delete_patient(patient_id)
            finally:
                service.repository.db.close()

    def regenerate_insights(self, patient_id: int) -> Dict[str, Any]:
        if self.is_api_alive():
            r = requests.post(f"{self.api_url}/patients/{patient_id}/generate-insights", timeout=8.0)
            r.raise_for_status()
            return r.json()
        else:
            service = self.get_service()
            try:
                res = service.regenerate_insights(patient_id)
                return res.model_dump()
            finally:
                service.repository.db.close()

    def run_batch_import(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        if self.is_api_alive():
            r = requests.post(f"{self.api_url}/patients/batch-import", json=records, timeout=15.0)
            r.raise_for_status()
            return r.json()
        else:
            service = self.get_service()
            try:
                summary = service.import_controlled_records(records)
                return summary.model_dump()
            finally:
                service.repository.db.close()

    def get_dashboard_metrics(self) -> Dict[str, Any]:
        if self.is_api_alive():
            r = requests.get(f"{self.api_url}/patients/metrics/dashboard", timeout=5.0)
            return r.json() if r.status_code == 200 else {"total_patients": 0, "patients_with_remarks": 0}
        else:
            db = SessionLocal()
            try:
                repo = PatientRepository(db)
                return repo.get_metrics_summary()
            finally:
                db.close()


client = BackendClient()

# Session State Initialization
if "current_nav" not in st.session_state:
    st.session_state["current_nav"] = "Dashboard"
if "view_patient" not in st.session_state:
    st.session_state["view_patient"] = None
if "edit_patient" not in st.session_state:
    st.session_state["edit_patient"] = None
if "delete_target_id" not in st.session_state:
    st.session_state["delete_target_id"] = None


# Sidebar Navigation
with st.sidebar:
    st.markdown("## 🩺 **VitalSense AI**")
    st.caption("v1.0.0 • Healthcare Patient Management")
    st.markdown("---")

    nav_options = [
        "📊 Dashboard",
        "➕ Add Patient",
        "📋 Patient Records",
        "💡 Health Insights",
        "🧪 10-Case Assignment Demo"
    ]
    chosen_nav = st.radio("Navigation", nav_options, index=0)
    clean_nav = chosen_nav.split(" ", 1)[-1]
    st.session_state["current_nav"] = clean_nav

    st.markdown("---")
    st.markdown("### System Telemetry")
    api_online = client.is_api_alive()
    if api_online:
        st.success("🟢 FastAPI Backend: ONLINE")
    else:
        st.info("🔷 Direct Service Mode (Embedded)")

    st.caption(f"AI Provider: `{settings.AI_PROVIDER}`")
    st.caption(f"Database: `SQLite (vitalsense.db)`")


# Header Banner
st.markdown(
    """
    <div class="vitalsense-header">
        <h1>VitalSense AI</h1>
        <p>AI-Powered Patient Health Insights & Blood Test Management System</p>
    </div>
    """,
    unsafe_allow_html=True
)

current_view = st.session_state["current_nav"]

# -------------------------------------------------------------
# 1. DASHBOARD VIEW
# -------------------------------------------------------------
if current_view == "Dashboard":
    st.markdown("### 📊 Clinical Dashboard Overview")
    metrics = client.get_dashboard_metrics()
    total_pts = metrics.get("total_patients", 0)
    with_rmk = metrics.get("patients_with_remarks", 0)
    pending_rmk = metrics.get("pending_remarks", 0)

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="title">Total Patients</div>
                <div class="value">{total_pts}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with m2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="title">Records with AI Remarks</div>
                <div class="value">{with_rmk}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with m3:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="title">Pending AI Remarks</div>
                <div class="value">{pending_rmk}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with m4:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="title">Database Status</div>
                <div class="value" style="color: #059669; font-size: 1.5rem;">Connected</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("---")
    st.markdown("#### Quick Clinical Actions")
    qa1, qa2, qa3 = st.columns(3)
    with qa1:
        if st.button("➕ Register New Patient", use_container_width=True):
            st.session_state["current_nav"] = "Add Patient"
            st.rerun()
    with qa2:
        if st.button("📋 Browse All Records", use_container_width=True):
            st.session_state["current_nav"] = "Patient Records"
            st.rerun()
    with qa3:
        if st.button("🧪 Run Assignment Test Suite (10 Cases)", use_container_width=True):
            st.session_state["current_nav"] = "10-Case Assignment Demo"
            st.rerun()

    st.markdown("---")
    st.markdown("#### Recently Registered Patients")
    recent = client.get_all_patients()[:5]
    if recent:
        for r in recent:
            st.markdown(
                f"• **{r['full_name']}** ({r.get('date_of_birth_display', r['date_of_birth'])}) — "
                f"Glucose: `{r['glucose']} mg/dL`, Hb: `{r['haemoglobin']} g/dL`, Chol: `{r['cholesterol']} mg/dL` — Email: `{r['email']}`"
            )
    else:
        st.info("No patient records in the database yet. Click 'Run Assignment Test Suite' to import sample patients.")


# -------------------------------------------------------------
# 2. ADD PATIENT VIEW
# -------------------------------------------------------------
elif current_view == "Add Patient":
    st.markdown("### ➕ Patient Registration & Blood Test Entry")

    def handle_create(payload: Dict[str, Any]):
        try:
            with st.spinner("Validating submitted fields and generating AI remarks..."):
                created = client.create_patient(payload)
            st.success(f"Patient '{created['full_name']}' was successfully registered with ID #{created['id']}!")
            st.session_state["view_patient"] = created
            st.markdown(
                f"""
                <div class="remarks-card">
                    <h4>Generated AI Health Remarks</h4>
                    <pre style="white-space: pre-wrap; font-family: inherit; font-size: 0.95rem; line-height: 1.6;">{created.get('remarks', '')}</pre>
                </div>
                """,
                unsafe_allow_html=True
            )
        except ValidationException as exc:
            st.error("Submission rejected due to validation errors:")
            for field, errs in exc.errors.items():
                st.markdown(f"- **{field}**: {', '.join(errs)}")
        except Exception as exc:
            st.error(f"Failed to create patient: {exc}")

    render_patient_form(on_submit=handle_create, is_edit_mode=False)


# -------------------------------------------------------------
# 3. PATIENT RECORDS VIEW
# -------------------------------------------------------------
elif current_view == "Patient Records":
    st.markdown("### 📋 Patient Management Records")

    # Search Bar
    search_col1, search_col2 = st.columns([4, 1])
    with search_col1:
        search_query = st.text_input("🔍 Search patients by full name or email address...", value="")
    with search_col2:
        st.write("")
        st.write("")
        refresh_btn = st.button("🔄 Refresh")

    # Handle Edit State Modal/Section
    if st.session_state["edit_patient"]:
        curr = st.session_state["edit_patient"]
        st.markdown(f"#### ✏️ Edit Patient Information — ID #{curr['id']}: {curr['full_name']}")
        st.caption("Step 5 Demonstration: You can update the email address to `gokul@infocare.com`.")

        def handle_update(payload: Dict[str, Any]):
            try:
                with st.spinner("Updating patient information..."):
                    updated = client.update_patient(curr["id"], payload)
                st.success(f"Patient ID #{curr['id']} was successfully updated!")
                st.session_state["edit_patient"] = None
                st.rerun()
            except ValidationException as exc:
                st.error("Update rejected due to validation errors:")
                for field, errs in exc.errors.items():
                    st.markdown(f"- **{field}**: {', '.join(errs)}")

        render_patient_form(on_submit=handle_update, initial_data=curr, is_edit_mode=True)
        if st.button("Cancel Editing"):
            st.session_state["edit_patient"] = None
            st.rerun()
        st.markdown("---")

    # Handle Delete Confirmation
    if st.session_state["delete_target_id"]:
        del_id = st.session_state["delete_target_id"]
        st.warning(f"⚠️ Are you sure you want to permanently delete patient record #{del_id}?")
        col_yes, col_no = st.columns(2)
        with col_yes:
            if st.button("Yes, Confirm Delete Record", key="btn_confirm_del"):
                client.delete_patient(del_id)
                st.success(f"Patient #{del_id} deleted successfully.")
                st.session_state["delete_target_id"] = None
                st.rerun()
        with col_no:
            if st.button("Cancel", key="btn_cancel_del"):
                st.session_state["delete_target_id"] = None
                st.rerun()
        st.markdown("---")

    # Callbacks
    def on_view(patient: Dict[str, Any]):
        st.session_state["view_patient"] = patient
        st.session_state["current_nav"] = "Health Insights"
        st.rerun()

    def on_edit(patient: Dict[str, Any]):
        st.session_state["edit_patient"] = patient
        st.rerun()

    def on_delete(patient_id: int):
        st.session_state["delete_target_id"] = patient_id
        st.rerun()

    def on_regenerate_ai(patient_id: int):
        with st.spinner(f"Re-evaluating AI remarks for patient #{patient_id}..."):
            client.regenerate_insights(patient_id)
        st.success(f"AI remarks regenerated for patient #{patient_id}!")
        st.rerun()

    patients_list = client.get_all_patients(search=search_query)
    render_patient_table(
        patients=patients_list,
        on_view=on_view,
        on_edit=on_edit,
        on_delete=on_delete,
        on_regenerate_ai=on_regenerate_ai
    )


# -------------------------------------------------------------
# 4. HEALTH INSIGHTS VIEW
# -------------------------------------------------------------
elif current_view == "Health Insights":
    st.markdown("### 💡 AI-Powered Health Insights & Lab Metrics")
    all_patients = client.get_all_patients()

    if not all_patients:
        st.info("No patient records available. Please register a patient or execute the demonstration suite first.")
    else:
        patient_options = {
            f"#{p['id']} - {p['full_name']} (DOB: {p.get('date_of_birth_display', p['date_of_birth'])})": p
            for p in all_patients
        }

        # Select target patient
        default_index = 0
        if st.session_state["view_patient"]:
            target_key = f"#{st.session_state['view_patient']['id']} - {st.session_state['view_patient']['full_name']} (DOB: {st.session_state['view_patient'].get('date_of_birth_display', st.session_state['view_patient']['date_of_birth'])})"
            keys_list = list(patient_options.keys())
            if target_key in keys_list:
                default_index = keys_list.index(target_key)

        selected_key = st.selectbox("Select Patient to Inspect:", list(patient_options.keys()), index=default_index)
        selected_patient = patient_options[selected_key]

        render_health_insights_view(selected_patient)


# -------------------------------------------------------------
# 5. 10-CASE ASSIGNMENT DEMO VIEW
# -------------------------------------------------------------
elif current_view == "10-Case Assignment Demo":
    def run_import_suite(records: List[Dict[str, Any]]) -> Dict[str, Any]:
        return client.run_batch_import(records)

    render_batch_import_view(on_run_import=run_import_suite)
