"""SimulaNewsMachine — reusable Streamlit UI helpers for the dashboard."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import streamlit as st


def inject_custom_css():
    st.markdown(
        """
        <style>
        .stApp {
            background: linear-gradient(180deg, #fbfbfb 0%, #f4f5f7 100%);
            color: #17181b;
        }
        .dashboard-card {
            background: white;
            border: 1px solid #eceef2;
            border-radius: 18px;
            padding: 18px 20px;
            box-shadow: 0 10px 26px rgba(18, 24, 40, 0.05);
            margin-bottom: 12px;
        }
        .dashboard-pill {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 999px;
            font-size: 0.82rem;
            font-weight: 600;
            margin-right: 6px;
            margin-bottom: 6px;
        }
        .pill-ok { background: #ecfdf3; color: #027a48; }
        .pill-warn { background: #fff7ed; color: #b54708; }
        .pill-muted { background: #f2f4f7; color: #344054; }
        .pill-red { background: #fef3f2; color: #b42318; }
        .section-subtle {
            color: #667085;
            font-size: 0.95rem;
            margin-top: -8px;
            margin-bottom: 12px;
        }
        .morning-accent {
            border-left: 5px solid #c1121f;
        }
        .afternoon-accent {
            border-left: 5px solid #444ce7;
        }
        div.stButton > button {
            border-radius: 12px;
            border: 1px solid #e4e7ec;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_status_pill(label: str, tone: str = "muted"):
    tone_map = {
        "ok": "pill-ok",
        "warn": "pill-warn",
        "red": "pill-red",
        "muted": "pill-muted",
    }
    css_class = tone_map.get(tone, "pill-muted")
    st.markdown(
        f'<span class="dashboard-pill {css_class}">{label}</span>',
        unsafe_allow_html=True,
    )


def set_copy_buffer(text: str, label: str = ""):
    st.session_state["dashboard_copy_buffer_text"] = text or ""
    st.session_state["dashboard_copy_buffer_label"] = label or "Copy-ready text"


def render_copy_buffer():
    text = st.session_state.get("dashboard_copy_buffer_text", "")
    if not text:
        return
    label = st.session_state.get("dashboard_copy_buffer_label", "Copy-ready text")
    with st.expander("Copy helper", expanded=False):
        st.caption(f"{label} — usa esta caixa como fallback de copy.")
        st.text_area(
            "Copy-ready",
            value=text,
            height=min(max(120, len(text) // 2), 320),
            key="dashboard_copy_buffer_area",
        )


def open_local_path(path_like) -> tuple[bool, str]:
    try:
        path = Path(path_like)
        if not path.exists():
            return False, f"Caminho não existe: {path}"
        if os.name == "nt":
            os.startfile(str(path))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
        return True, str(path)
    except Exception as e:
        return False, str(e)


def render_link_action(url: str, label: str, key: str):
    url = url or ""
    if url:
        st.link_button(label, url, use_container_width=True)
    else:
        st.button(label, disabled=True, use_container_width=True, key=f"{key}_disabled")
