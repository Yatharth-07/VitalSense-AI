from __future__ import annotations

from typing import Any, Dict, Optional
import streamlit as st
import plotly.graph_objects as go


def render_metric_gauge(
    title: str,
    value: float,
    unit: str,
    min_val: float,
    max_val: float,
    normal_low: float,
    normal_high: float
) -> go.Figure:
    """Renders a clean Plotly gauge comparing measured value with adult physiological range."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={'text': f"<b>{title}</b> ({unit})", 'font': {'size': 14, 'color': '#0F172A'}},
        number={'suffix': f" {unit}", 'font': {'size': 18, 'color': '#0F766E'}},
        gauge={
            'axis': {'range': [min_val, max_val], 'tickcolor': "#94A3B8"},
            'bar': {'color': "#0F766E"},
            'bgcolor': "#F8FAFC",
            'borderwidth': 1,
            'bordercolor': "#CBD5E1",
            'steps': [
                {'range': [min_val, normal_low], 'color': '#FEF3C7'},
                {'range': [normal_low, normal_high], 'color': '#D1FAE5'},
                {'range': [normal_high, max_val], 'color': '#FEE2E2'}
            ],
            'threshold': {
                'line': {'color': "#DC2626", 'width': 3},
                'thickness': 0.8,
                'value': value
            }
        }
    ))
    fig.update_layout(
        height=180,
        margin=dict(l=20, r=20, t=30, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Plus Jakarta Sans, sans-serif")
    )
    return fig


def render_health_insights_view(patient: Dict[str, Any]):
    """Renders detailed health insights, comparison visualizations, and disclaimer."""
    st.markdown(
        """
        <div class="disclaimer-box">
            <strong>⚠️ IMPORTANT CLINICAL NOTICE & DISCLAIMER</strong><br>
            VitalSense AI produces educational and informational summaries strictly to assist healthcare professionals.
            The observations below <strong>DO NOT</strong> constitute a clinical medical diagnosis, disease identification,
            or prescription. Reference ranges vary across clinical laboratories, patient age, sex, and clinical history.
        </div>
        """,
        unsafe_allow_html=True
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        fig_gluc = render_metric_gauge(
            "Fasting Glucose",
            patient["glucose"],
            "mg/dL",
            min_val=40,
            max_val=350,
            normal_low=70,
            normal_high=140
        )
        st.plotly_chart(fig_gluc, use_container_width=True)

    with col2:
        fig_hb = render_metric_gauge(
            "Haemoglobin",
            patient["haemoglobin"],
            "g/dL",
            min_val=4.0,
            max_val=22.0,
            normal_low=12.0,
            normal_high=17.5
        )
        st.plotly_chart(fig_hb, use_container_width=True)

    with col3:
        fig_chol = render_metric_gauge(
            "Total Cholesterol",
            patient["cholesterol"],
            "mg/dL",
            min_val=100,
            max_val=400,
            normal_low=120,
            normal_high=200
        )
        st.plotly_chart(fig_chol, use_container_width=True)

    st.markdown("### AI Health Observations & Remarks")
    remarks = patient.get("remarks")
    if remarks:
        st.markdown(
            f"""
            <div class="remarks-card">
                <h4>Generated Remarks for {patient['full_name']}</h4>
                <pre style="white-space: pre-wrap; font-family: inherit; font-size: 0.95rem; line-height: 1.6; color: #1E293B; background: transparent; border: none; padding: 0;">{remarks}</pre>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.info("No AI remarks generated yet for this patient.")
