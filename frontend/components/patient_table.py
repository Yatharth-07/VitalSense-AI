from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional
import streamlit as st


def render_patient_table(
    patients: List[Dict[str, Any]],
    on_view: Callable[[Dict[str, Any]], None],
    on_edit: Callable[[Dict[str, Any]], None],
    on_delete: Callable[[int], None],
    on_regenerate_ai: Callable[[int], None]
):
    """
    Renders professional, responsive patient records table with action buttons.
    """
    if not patients:
        st.info("No patient records found matching your criteria.")
        return

    # Table Header
    header_col1, header_col2, header_col3, header_col4, header_col5, header_col6 = st.columns([1, 3, 2, 3, 2, 3])
    with header_col1:
        st.markdown("**ID**")
    with header_col2:
        st.markdown("**Patient Name**")
    with header_col3:
        st.markdown("**DOB**")
    with header_col4:
        st.markdown("**Email**")
    with header_col5:
        st.markdown("**Metrics (G / Hb / Chol)**")
    with header_col6:
        st.markdown("**Actions**")

    st.markdown("<hr style='margin: 0.5rem 0;'>", unsafe_allow_html=True)

    for p in patients:
        col1, col2, col3, col4, col5, col6 = st.columns([1, 3, 2, 3, 2, 3])
        p_id = p["id"]

        with col1:
            st.write(f"#{p_id}")
        with col2:
            st.markdown(f"**{p['full_name']}**")
        with col3:
            st.write(p.get("date_of_birth_display", str(p["date_of_birth"])))
        with col4:
            st.write(p["email"])
        with col5:
            st.write(f"{p['glucose']} / {p['haemoglobin']} / {p['cholesterol']}")

        with col6:
            btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)
            with btn_col1:
                if st.button("👁️", key=f"view_{p_id}", help="View Health Insights"):
                    on_view(p)
            with btn_col2:
                if st.button("✏️", key=f"edit_{p_id}", help="Edit Patient Information"):
                    on_edit(p)
            with btn_col3:
                if st.button("✨", key=f"ai_{p_id}", help="Regenerate AI Remarks"):
                    on_regenerate_ai(p_id)
            with btn_col4:
                if st.button("🗑️", key=f"del_{p_id}", help="Delete Patient Record"):
                    on_delete(p_id)

        st.markdown("<hr style='margin: 0.3rem 0; opacity: 0.4;'>", unsafe_allow_html=True)
