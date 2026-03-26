"""SimulaNewsMachine — reusable Streamlit UI helpers for the dashboard."""

from __future__ import annotations

import os
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path

import streamlit as st


def inject_custom_css():
    st.markdown(
        """
        <style>
        .stApp {
            background: linear-gradient(180deg, #fbfbfc 0%, #f4f5f7 100%);
            color: #111827;
        }
        .block-container {
            max-width: 1380px;
            padding-top: 1.35rem;
            padding-bottom: 2.4rem;
        }
        [data-testid="stSidebar"] > div:first-child {
            background: linear-gradient(180deg, #ffffff 0%, #f7f8fa 100%);
            border-right: 1px solid #e5e7eb;
        }
        h1, h2, h3, h4 {
            letter-spacing: -0.02em;
        }
        .dashboard-hero {
            background: linear-gradient(135deg, rgba(255,255,255,0.96) 0%, rgba(248,249,251,0.96) 100%);
            border: 1px solid #eceef2;
            border-radius: 22px;
            padding: 24px 26px 18px 26px;
            box-shadow: 0 12px 32px rgba(18, 24, 40, 0.05);
            margin-bottom: 18px;
        }
        .dashboard-kicker {
            color: #b42318;
            font-size: 0.8rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin-bottom: 8px;
        }
        .dashboard-hero h1 {
            margin: 0;
            font-size: 2rem;
            line-height: 1.1;
            color: #101828;
        }
        .dashboard-hero p {
            margin: 10px 0 0 0;
            color: #667085;
            font-size: 0.98rem;
            line-height: 1.5;
            max-width: 860px;
        }
        .dashboard-section-head {
            margin-top: 10px;
            margin-bottom: 12px;
        }
        .dashboard-section-head h2,
        .dashboard-section-head h3 {
            margin-bottom: 0;
        }
        .dashboard-section-subtitle {
            color: #667085;
            font-size: 0.94rem;
            margin-top: 3px;
        }
        .dashboard-card {
            background: #ffffff;
            border: 1px solid #eceef2;
            border-radius: 18px;
            padding: 18px 20px;
            box-shadow: 0 12px 28px rgba(15, 23, 42, 0.05);
            margin-bottom: 14px;
        }
        .card-soft {
            background: #fbfcfd;
        }
        .card-morning {
            border-left: 5px solid #b42318;
        }
        .card-afternoon {
            border-left: 5px solid #344054;
            background: linear-gradient(180deg, #ffffff 0%, #fbfbfc 100%);
        }
        .card-success {
            border-left: 5px solid #027a48;
        }
        .card-warning {
            border-left: 5px solid #b54708;
        }
        .dashboard-pill {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 999px;
            font-size: 0.8rem;
            font-weight: 600;
            margin-right: 6px;
            margin-bottom: 6px;
        }
        .pill-ok { background: #ecfdf3; color: #027a48; }
        .pill-warn { background: #fff7ed; color: #b54708; }
        .pill-muted { background: #f2f4f7; color: #344054; }
        .pill-red { background: #fef3f2; color: #b42318; }
        .pill-info { background: #eff8ff; color: #175cd3; }
        .dashboard-meta {
            color: #667085;
            font-size: 0.88rem;
            line-height: 1.4;
            margin-top: 4px;
            margin-bottom: 8px;
        }
        .dashboard-empty {
            background: #ffffff;
            border: 1px dashed #d0d5dd;
            border-radius: 18px;
            padding: 18px 20px;
            margin-bottom: 14px;
        }
        .dashboard-empty strong {
            color: #101828;
            display: block;
            margin-bottom: 4px;
        }
        .dashboard-empty span {
            color: #667085;
            display: block;
            line-height: 1.45;
        }
        .dashboard-notice {
            border-radius: 18px;
            padding: 16px 18px;
            margin-bottom: 14px;
            border: 1px solid #e4e7ec;
            background: #ffffff;
            box-shadow: 0 10px 24px rgba(18, 24, 40, 0.04);
        }
        .notice-ok { border-left: 5px solid #027a48; }
        .notice-warn { border-left: 5px solid #b54708; }
        .notice-red { border-left: 5px solid #b42318; }
        .notice-muted { border-left: 5px solid #98a2b3; }
        .dashboard-copy-ready {
            background: #fffaf5;
            border: 1px solid #f5d0ab;
            border-left: 5px solid #b54708;
            border-radius: 16px;
            padding: 14px 16px 8px 16px;
            margin-top: 10px;
            margin-bottom: 12px;
        }
        .dashboard-copy-ready strong {
            color: #7a2e0b;
            display: block;
            margin-bottom: 4px;
        }
        .dashboard-copy-ready span {
            color: #8a4b1d;
            display: block;
            margin-bottom: 8px;
            font-size: 0.92rem;
        }
        .dashboard-pathbox {
            background: #f8fafc;
            border: 1px solid #e4e7ec;
            border-radius: 14px;
            padding: 12px 14px;
            margin-bottom: 10px;
        }
        .dashboard-divider {
            height: 1px;
            background: #eceef2;
            margin: 20px 0 18px 0;
        }
        div.stButton > button,
        div.stDownloadButton > button,
        div[data-testid="stLinkButton"] a {
            border-radius: 12px !important;
            border: 1px solid #e4e7ec !important;
            min-height: 2.7rem;
            font-weight: 600 !important;
        }
        div.stButton > button[kind="primary"] {
            background: #b42318;
            color: white;
            border-color: #b42318 !important;
        }
        div[data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #eceef2;
            border-radius: 16px;
            padding: 10px 12px;
            box-shadow: 0 10px 24px rgba(18, 24, 40, 0.04);
        }
        [data-testid="stTabs"] button {
            font-weight: 600;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


@contextmanager
def card_container(accent: str | None = None, soft: bool = False):
    classes = ["dashboard-card"]
    if soft:
        classes.append("card-soft")
    if accent == "morning":
        classes.append("card-morning")
    elif accent == "afternoon":
        classes.append("card-afternoon")
    elif accent == "success":
        classes.append("card-success")
    elif accent == "warning":
        classes.append("card-warning")
    st.markdown(f'<div class="{" ".join(classes)}">', unsafe_allow_html=True)
    try:
        yield
    finally:
        st.markdown("</div>", unsafe_allow_html=True)


def render_status_pill(label: str, tone: str = "muted"):
    tone_map = {
        "ok": "pill-ok",
        "warn": "pill-warn",
        "red": "pill-red",
        "muted": "pill-muted",
        "info": "pill-info",
    }
    css_class = tone_map.get(tone, "pill-muted")
    st.markdown(
        f'<span class="dashboard-pill {css_class}">{label}</span>',
        unsafe_allow_html=True,
    )


def render_page_header(title: str, subtitle: str, kicker: str = "Simula Operations"):
    st.markdown(
        (
            '<div class="dashboard-hero">'
            f'<div class="dashboard-kicker">{kicker}</div>'
            f"<h1>{title}</h1>"
            f"<p>{subtitle}</p>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_section_header(title: str, subtitle: str = "", level: int = 2):
    heading_tag = "h2" if level == 2 else "h3"
    subtitle_html = (
        f'<div class="dashboard-section-subtitle">{subtitle}</div>'
        if subtitle else ""
    )
    st.markdown(
        (
            '<div class="dashboard-section-head">'
            f"<{heading_tag}>{title}</{heading_tag}>"
            f"{subtitle_html}"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_empty_state(title: str, message: str):
    st.markdown(
        (
            '<div class="dashboard-empty">'
            f"<strong>{title}</strong>"
            f"<span>{message}</span>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_notice(title: str, message: str, tone: str = "muted"):
    tone_map = {
        "ok": "notice-ok",
        "warn": "notice-warn",
        "red": "notice-red",
        "muted": "notice-muted",
    }
    css_class = tone_map.get(tone, "notice-muted")
    st.markdown(
        (
            f'<div class="dashboard-notice {css_class}">'
            f"<strong>{title}</strong>"
            f"<div>{message}</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_prompt_block(title: str, text: str, empty_message: str, accent: str | None = None):
    with card_container(accent=accent, soft=True):
        st.markdown(f"**{title}**")
        if text:
            st.code(text, language="text")
        else:
            render_status_pill("Missing", "warn")
            st.caption(empty_message)


def render_path_block(label: str, path_value: str):
    st.markdown(
        (
            '<div class="dashboard-pathbox">'
            f"<strong>{label}</strong><br>"
            f"{path_value or 'N/A'}"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def set_copy_buffer(text: str, label: str = "", slot_key: str = "global"):
    st.session_state["dashboard_copy_buffer_text"] = text or ""
    st.session_state["dashboard_copy_buffer_label"] = label or "Copy-ready text"
    st.session_state["dashboard_copy_buffer_slot"] = slot_key or "global"


def render_copy_buffer(slot_key: str | None = None):
    text = st.session_state.get("dashboard_copy_buffer_text", "")
    if not text:
        return
    current_slot = st.session_state.get("dashboard_copy_buffer_slot", "global")
    if slot_key is not None and current_slot != slot_key:
        return
    label = st.session_state.get("dashboard_copy_buffer_label", "Copy-ready text")
    area_key = f"dashboard_copy_buffer_area_{slot_key or current_slot}"
    st.markdown(
        (
            '<div class="dashboard-copy-ready">'
            f"<strong>Ready to copy — {label}</strong>"
            "<span>Selecciona e copia directamente desta caixa.</span>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )
    st.text_area(
        "Copy-ready",
        value=text,
        height=min(max(120, len(text) // 2), 320),
        key=area_key,
        label_visibility="collapsed",
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
