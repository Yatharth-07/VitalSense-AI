from __future__ import annotations

from typing import Any, Callable, Dict, Optional
import streamlit as st


def render_patient_form(
    on_submit: Callable[[Dict[str, Any]], Any],
    initial_data: Optional[Dict[str, Any]] = None,
    is_edit_mode: bool = False
):
    """
    Renders patient registration / update form.
    Groups personal information and blood test metrics with clear healthcare visual indicators.
    """
    initial = initial_data or {}

    with st.form(key="patient_entry_form", clear_on_submit=not is_edit_mode):
        st.markdown("#### 👤 Patient Personal Information")
        st.caption("All demographic fields are required. Enter date in DD/MM/YYYY format.")

        col1, col2 = st.columns(2)
        with col1:
            full_name = st.text_input(
                "Full Name *",
                value=initial.get("full_name", ""),
                placeholder="e.g. Robyn Pears, Madison XI",
                help="Patient's legal or recognized full name."
            )
            email = st.text_input(
                "Email Address *",
                value=initial.get("email", ""),
                placeholder="e.g. robyn@gmail.com, gokul@infocare.com",
                help="Must be a valid email with a domain extension."
            )

        with col2:
            dob_raw = st.text_input(
                "Date of Birth (DD/MM/YYYY) *",
                value=initial.get("date_of_birth_display") or initial.get("date_of_birth", ""),
                placeholder="DD/MM/YYYY or DD.MM.YYYY",
                help="Must be a valid historical calendar date (not in future, valid month days)."
            )

        st.markdown("---")
        st.markdown("#### 🩸 Blood Test Measurements")
        st.caption("Standard quantitative serum laboratory metrics.")

        col3, col4, col5 = st.columns(3)
        with col3:
            glucose_val = st.number_input(
                "Glucose (mg/dL) *",
                min_value=10.0,
                max_value=1000.0,
                value=float(initial.get("glucose", 95.0)),
                step=1.0,
                help="Normal fasting range: 70 - 140 mg/dL"
            )
        with col4:
            hb_val = st.number_input(
                "Haemoglobin (g/dL) *",
                min_value=1.0,
                max_value=35.0,
                value=float(initial.get("haemoglobin", 14.0)),
                step=0.1,
                help="Normal adult range: 12.0 - 17.5 g/dL"
            )
        with col5:
            chol_val = st.number_input(
                "Total Cholesterol (mg/dL) *",
                min_value=20.0,
                max_value=1500.0,
                value=float(initial.get("cholesterol", 185.0)),
                step=1.0,
                help="Desirable adult range: < 200 mg/dL"
            )

        btn_label = "Update Patient Record" if is_edit_mode else "Register Patient & Generate AI Insights"
        submitted = st.form_submit_button(btn_label)

        if submitted:
            payload = {
                "full_name": full_name,
                "date_of_birth": dob_raw,
                "email": email,
                "glucose": glucose_val,
                "haemoglobin": hb_val,
                "cholesterol": chol_val
            }
            on_submit(payload)
