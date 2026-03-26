"""SimulaNewsMachine — premium internal dashboard for content operations."""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from dashboard_components import (
    card_container,
    inject_custom_css,
    open_local_path,
    render_copy_buffer,
    render_empty_state,
    render_link_action,
    render_notice,
    render_page_header,
    render_path_block,
    render_prompt_block,
    render_section_header,
    render_status_pill,
    set_copy_buffer,
)
from dashboard_data import (
    build_selection_summary,
    extract_brief_snippet,
    find_agent_output_for_article,
    load_dashboard_context,
    parse_qa_data,
)
from dashboard_overrides import (
    SUPPORTED_OVERRIDE_FIELDS,
    ensure_overrides_file,
    get_override_options,
    load_current_overrides,
    reset_current_overrides,
    resolve_preview_selection,
    save_current_overrides,
)

NAV_ITEMS = [
    "Overview",
    "News Browser",
    "Instagram",
    "Other Channels",
    "Image + Voice",
    "Brief",
    "Overrides",
    "Settings / Status",
]

DIGEST_LABELS = {
    "instagram_morning_digest": "Morning Digest",
    "instagram_afternoon_digest": "Afternoon Digest",
}


def _article_key(article: dict) -> str:
    article = article or {}
    return article.get("link") or article.get("title") or json.dumps(article, ensure_ascii=False, sort_keys=True)


def _safe_list(value):
    return value if isinstance(value, list) else []


def _safe_dict(value):
    return value if isinstance(value, dict) else {}


def _init_state(context: dict, force: bool = False):
    plan = _safe_dict((context.get("snapshot", {}) or {}).get("plan", {}))
    current_overrides = load_current_overrides()

    if force or "dashboard_nav" not in st.session_state:
        st.session_state["dashboard_nav"] = "Overview"
    if force or "dashboard_override_draft" not in st.session_state:
        st.session_state["dashboard_override_draft"] = {
            field: int(current_overrides.get(field, 0)) if str(current_overrides.get(field, 0)).isdigit() else 0
            for field in SUPPORTED_OVERRIDE_FIELDS
        }
    if force or "dashboard_digest_drafts" not in st.session_state:
        morning = _safe_list(resolve_preview_selection(
            plan,
            "instagram_morning_digest",
            st.session_state["dashboard_override_draft"].get("instagram_morning_digest", 0),
        ))
        afternoon = _safe_list(resolve_preview_selection(
            plan,
            "instagram_afternoon_digest",
            st.session_state["dashboard_override_draft"].get("instagram_afternoon_digest", 0),
        ))
        st.session_state["dashboard_digest_drafts"] = {
            "instagram_morning_digest": list(morning),
            "instagram_afternoon_digest": list(afternoon),
        }
    if force or "dashboard_preview_article" not in st.session_state:
        st.session_state["dashboard_preview_article"] = ""


def _set_navigation(page: str):
    st.session_state["dashboard_nav"] = page
    st.rerun()


def _save_overrides_feedback():
    ok, message = save_current_overrides(st.session_state.get("dashboard_override_draft", {}))
    if ok:
        st.success(f"Overrides guardados em {message}")
    else:
        st.error(f"Falha ao guardar overrides: {message}")


def _open_path_feedback(path_like):
    ok, message = open_local_path(path_like)
    if ok:
        st.toast(f"Aberto: {message}")
    else:
        st.warning(message)


def _copy_button(label: str, text: str, key: str, primary: bool = False, slot_key: str | None = None):
    if st.button(label, key=key, use_container_width=True, type="primary" if primary else "secondary"):
        slot = slot_key or key
        set_copy_buffer(text, label, slot)
        st.toast(f"{label} pronto para copiar")


def _render_freshness_notice(context: dict):
    freshness = _safe_dict(context.get("freshness", {}))
    if not freshness:
        return

    age_hours = freshness.get("age_hours")
    age_text = (
        f"Última actualização há {age_hours}h."
        if isinstance(age_hours, (int, float))
        else "Timestamp de actualização indisponível."
    )
    source_label = {
        "structured_snapshot": "snapshot estruturado",
        "fallback_files": "fallback de ficheiros",
        "missing": "dados em falta",
    }.get(freshness.get("source", ""), freshness.get("source", "origem desconhecida"))

    render_notice(
        f"Dashboard state — {freshness.get('label', 'Unknown')}",
        f"{freshness.get('message', '')} Fonte actual: {source_label}. {age_text}".strip(),
        freshness.get("tone", "muted"),
    )


def _render_story_summary(article: dict, show_inline_link: bool = True):
    article = article or {}
    title = article.get("title", "Sem título")
    source = article.get("source", "Fonte desconhecida")
    category = article.get("category", "unknown")
    score = article.get("score", 0)
    summary = (article.get("summary") or "").strip()
    link = article.get("link", "")

    meta_cols = st.columns([5, 1.2])
    with meta_cols[0]:
        st.markdown(f"#### {title}")
        st.caption(f"{source} • {category}")
    with meta_cols[1]:
        render_status_pill(f"Score {score}", "info" if score >= 50 else "muted")

    if summary:
        st.write(summary[:240])
    if link and show_inline_link:
        st.markdown(f"[Open source ↗]({link})")


def _render_story_actions(article: dict, key_prefix: str, allow_digest_actions: bool = False):
    article = article or {}
    url = article.get("link", "")
    copy_slot = f"{key_prefix}_copy_slot"

    primary = st.columns(3)
    with primary[0]:
        render_link_action(url, "Open Source", f"{key_prefix}_open")
    with primary[1]:
        _copy_button("Copy Link", url, f"{key_prefix}_copy", slot_key=copy_slot)
    with primary[2]:
        if st.button("Preview in Brief", key=f"{key_prefix}_brief", use_container_width=True):
            st.session_state["dashboard_preview_article"] = article.get("title", "")

    if allow_digest_actions:
        secondary = st.columns(2)
        with secondary[0]:
            if st.button("Add to Morning", key=f"{key_prefix}_add_morning", use_container_width=True):
                _add_story_to_digest("instagram_morning_digest", article)
                st.toast("Adicionado ao draft da manhã")
        with secondary[1]:
            if st.button("Add to Afternoon", key=f"{key_prefix}_add_afternoon", use_container_width=True):
                _add_story_to_digest("instagram_afternoon_digest", article)
                st.toast("Adicionado ao draft da tarde")

    render_copy_buffer(copy_slot)


def _render_preview_snippet():
    article_title = st.session_state.get("dashboard_preview_article", "")
    if not article_title:
        return
    snippet = extract_brief_snippet(article_title)
    if not snippet:
        render_empty_state("Brief preview indisponível", "O artigo foi marcado para preview mas não foi encontrado no brief actual.")
        return
    with st.expander(f"Preview in Brief — {article_title[:80]}", expanded=False):
        st.code(snippet, language="markdown")


def _add_story_to_digest(channel: str, article: dict):
    drafts = st.session_state.get("dashboard_digest_drafts", {})
    current = list(drafts.get(channel, []))
    current_keys = {_article_key(item) for item in current}
    if _article_key(article) not in current_keys:
        current.append(article)
    drafts[channel] = current[:7]
    st.session_state["dashboard_digest_drafts"] = drafts


def _remove_story_from_digest(channel: str, index: int):
    drafts = st.session_state.get("dashboard_digest_drafts", {})
    current = list(drafts.get(channel, []))
    if 0 <= index < len(current):
        current.pop(index)
    drafts[channel] = current
    st.session_state["dashboard_digest_drafts"] = drafts


def _move_story(channel: str, index: int, direction: int):
    drafts = st.session_state.get("dashboard_digest_drafts", {})
    current = list(drafts.get(channel, []))
    target = index + direction
    if 0 <= index < len(current) and 0 <= target < len(current):
        current[index], current[target] = current[target], current[index]
    drafts[channel] = current
    st.session_state["dashboard_digest_drafts"] = drafts


def _set_digest_variant(channel: str, variant: int, plan: dict):
    st.session_state["dashboard_override_draft"][channel] = variant
    resolved = _safe_list(resolve_preview_selection(plan, channel, variant))
    st.session_state["dashboard_digest_drafts"][channel] = list(resolved)
    st.toast(f"{DIGEST_LABELS.get(channel, channel)} → variante {variant}")


def _format_digest_copy_text(pack: dict, stories: list[dict]) -> str:
    pack = _safe_dict(pack)
    lines = [
        pack.get("cover_hook", "Sem cover hook"),
        "",
        f"Tema: {pack.get('digest_theme', 'N/A')}",
        "",
    ]
    slides = _safe_list(pack.get("slides", []))
    for idx, story in enumerate(stories[:7], 1):
        slide = slides[idx - 1] if idx - 1 < len(slides) and isinstance(slides[idx - 1], dict) else {}
        lines.append(f"{idx}. {slide.get('news_title') or story.get('title', 'Sem título')}")
        summary = slide.get("mini_summary") or story.get("summary", "")
        if summary:
            lines.append(f"   {summary}")
        why = slide.get("why_it_matters") or ""
        if why:
            lines.append(f"   Porque importa: {why}")
    if pack.get("caption_intro"):
        lines.extend(["", "Caption Intro:", pack.get("caption_intro", "")])
    for item in _safe_list(pack.get("caption_news_list", [])):
        lines.append(str(item))
    if pack.get("community_question"):
        lines.extend(["", "Pergunta final:", pack.get("community_question", "")])
    return "\n".join(lines).strip()


def _render_qa_block(qa_raw, key_prefix: str):
    qa = parse_qa_data(qa_raw)
    if qa.get("average") == "N/A" and not qa.get("scores"):
        render_empty_state("QA não disponível", "Este bloco ainda não tem avaliação estruturada para o latest run.")
        return

    cols = st.columns(3)
    cols[0].metric("QA Average", qa.get("average", "N/A"))
    cols[1].metric("Approved", "Yes" if qa.get("approved") else "No")
    cols[2].metric("Hashtags", len(qa.get("hashtags", [])))
    if qa.get("scores"):
        st.caption("Editorial checks")
        for name, value in qa.get("scores", {}).items():
            render_status_pill(f"{name}: {value}", "muted")
    if qa.get("issues"):
        st.warning(" | ".join(str(issue) for issue in qa.get("issues", [])))
    if qa.get("hashtags"):
        slot = f"{key_prefix}_hashtags_slot"
        _copy_button(
            "Copy Hashtags",
            " ".join(str(x) for x in qa.get("hashtags", [])),
            f"{key_prefix}_hashtags",
            slot_key=slot,
        )
        render_copy_buffer(slot)


def _render_digest_pack(pack: dict, key_prefix: str):
    pack = _safe_dict(pack)
    if not pack:
        render_empty_state("Agent output missing", "O latest run não tem um digest pack estruturado para este bloco. O dashboard está em fallback seguro.")
        return
    copy_slot = f"{key_prefix}_copy_slot"

    top_cols = st.columns([1.3, 1, 1])
    with top_cols[0]:
        st.markdown(f"**Digest Theme**  \n{pack.get('digest_theme', 'N/A')}")
    with top_cols[1]:
        st.markdown(f"**Cover Hook**  \n{pack.get('cover_hook', 'N/A')}")
    with top_cols[2]:
        if pack.get("format"):
            render_status_pill(pack.get("format", ""), "info")
        if pack.get("cta_style"):
            render_status_pill(f"CTA {pack.get('cta_style')}", "muted")

    button_row = st.columns(3)
    with button_row[0]:
        _copy_button("Copy Cover Hook", pack.get("cover_hook", ""), f"{key_prefix}_hook", slot_key=copy_slot)
    with button_row[1]:
        _copy_button("Copy Caption Intro", pack.get("caption_intro", ""), f"{key_prefix}_caption_intro", slot_key=copy_slot)
    with button_row[2]:
        _copy_button("Copy Community Question", pack.get("community_question", ""), f"{key_prefix}_question", slot_key=copy_slot)

    render_copy_buffer(copy_slot)

    slides = _safe_list(pack.get("slides", []))
    if slides:
        render_section_header("Slides", "Uma história por slide, em ordem editorial.", level=3)
        for idx, slide in enumerate(slides[:7], 1):
            with card_container(soft=True):
                if isinstance(slide, dict):
                    st.markdown(f"**{idx}. {slide.get('news_title', 'N/A')}**")
                    if slide.get("mini_summary"):
                        st.write(slide.get("mini_summary", ""))
                    if slide.get("why_it_matters"):
                        st.caption(f"Porque importa: {slide.get('why_it_matters', '')}")
                else:
                    st.write(f"{idx}. {slide}")

    if pack.get("caption_intro") or pack.get("caption_news_list"):
        render_section_header("Caption", "Abertura e lista curta de apoio ao carrossel.", level=3)
        if pack.get("caption_intro"):
            st.write(pack.get("caption_intro", ""))
        for item in _safe_list(pack.get("caption_news_list", [])):
            st.write(str(item))

    footer = st.columns(2)
    with footer[0]:
        st.markdown(f"**Community Question**  \n{pack.get('community_question', 'N/A')}")
    with footer[1]:
        st.markdown(f"**Notes for Design**  \n{pack.get('notes_for_design', 'N/A')}")


def _render_sidebar(context: dict):
    run_summary = context.get("run_summary", {}) or {}
    runtime = context.get("runtime", {}) or {}
    snapshot = context.get("snapshot", {}) or {}
    status = context.get("status", {}) or {}
    freshness = context.get("freshness", {}) or {}

    def _sidebar_pill(label: str, tone: str = "muted"):
        tone_map = {
            "ok": "pill-ok",
            "warn": "pill-warn",
            "red": "pill-red",
            "muted": "pill-muted",
            "info": "pill-info",
        }
        css_class = tone_map.get(tone, "pill-muted")
        st.sidebar.markdown(
            f'<span class="dashboard-pill {css_class}">{label}</span>',
            unsafe_allow_html=True,
        )

    st.sidebar.title("Simula Operations")
    st.sidebar.caption("Internal content control center")
    _sidebar_pill(
        f"Run {run_summary.get('status', snapshot.get('run_status', 'UNKNOWN'))}",
        "ok" if run_summary.get("status", snapshot.get("run_status", "UNKNOWN")) == "OK" else "warn",
    )
    if freshness.get("label"):
        _sidebar_pill(
            f"{freshness.get('label')} data",
            freshness.get("tone", "muted"),
        )
    if status.get("timestamp"):
        st.sidebar.caption(status.get("timestamp"))
    if freshness.get("source"):
        source_label = {
            "structured_snapshot": "Snapshot",
            "fallback_files": "Fallback",
            "missing": "Missing",
        }.get(freshness.get("source", ""), freshness.get("source", "Unknown"))
        st.sidebar.caption(f"Source: {source_label}")

    metrics_top = st.sidebar.columns(2)
    metrics_top[0].metric("Scanned", run_summary.get("articles_scanned", 0))
    metrics_top[1].metric("Selected", run_summary.get("articles_selected", 0))
    metrics_bottom = st.sidebar.columns(2)
    metrics_bottom[0].metric("Feeds OK", run_summary.get("feeds_ok", 0))
    metrics_bottom[1].metric("Cards", len((context.get("cards", {}) or {}).get("cards", [])))

    st.sidebar.radio("Navigate", NAV_ITEMS, key="dashboard_nav")

    st.sidebar.markdown("---")
    st.sidebar.caption("Quick actions")
    if st.sidebar.button("Reload data", use_container_width=True, type="primary"):
        _init_state(load_dashboard_context(), force=True)
        st.rerun()
    if st.sidebar.button("Open overrides file", use_container_width=True):
        _open_path_feedback(ensure_overrides_file())
    if st.sidebar.button("Open latest brief folder", use_container_width=True):
        _open_path_feedback(runtime.get("paths", {}).get("brief_folder", ""))
    if st.sidebar.button("Open cards folder", use_container_width=True):
        _open_path_feedback(runtime.get("paths", {}).get("cards_folder", ""))

    export_text = build_selection_summary(context, st.session_state.get("dashboard_override_draft", {}))
    st.sidebar.download_button(
        "Export selection summary",
        data=export_text,
        file_name="simula_selection_summary.txt",
        mime="text/plain",
        use_container_width=True,
    )

    st.sidebar.markdown("---")
    st.sidebar.caption("Operational signals")
    _sidebar_pill("MiniMax ready" if runtime.get("minimax_configured") else "MiniMax missing", "ok" if runtime.get("minimax_configured") else "warn")
    _sidebar_pill("Email on" if runtime.get("email_enabled") else "Email off", "ok" if runtime.get("email_enabled") else "muted")
    _sidebar_pill("Cards on" if runtime.get("card_generation_enabled") else "Cards off", "ok" if runtime.get("card_generation_enabled") else "muted")
    _sidebar_pill("Snapshot ready" if runtime.get("snapshot_exists") else "No snapshot", "ok" if runtime.get("snapshot_exists") else "warn")


def _render_overview(context: dict):
    snapshot = context.get("snapshot", {}) or {}
    plan = snapshot.get("plan", {}) or {}
    run_summary = context.get("run_summary", {}) or {}
    runtime = context.get("runtime", {}) or {}
    overrides = context.get("overrides", {}) or {}
    freshness = context.get("freshness", {}) or {}
    agent_runtime = context.get("agent_runtime", {}) or {}

    render_page_header(
        "Overview",
        "Latest run health, editorial status and the fastest route into today’s decisions.",
    )

    _render_freshness_notice(context)

    if not snapshot.get("exists"):
        render_empty_state(
            "Snapshot not available",
            "The dashboard is in fallback mode until the next normal run refreshes the structured latest-run snapshot.",
        )

    render_section_header("Quick Actions", "Jump straight into the most common daily tasks.")
    quick = st.columns(4)
    with quick[0]:
        if st.button("View Morning Digest", use_container_width=True, type="primary"):
            _set_navigation("Instagram")
    with quick[1]:
        if st.button("Open Latest Brief", use_container_width=True):
            _open_path_feedback((context.get("brief", {}) or {}).get("path", ""))
    with quick[2]:
        if st.button("Open Overrides", use_container_width=True):
            _set_navigation("Overrides")
    with quick[3]:
        if st.button("Open Cards Folder", use_container_width=True):
            _open_path_feedback(runtime.get("paths", {}).get("cards_folder", ""))

    render_section_header("Run Status", "Operational health and core output availability.")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Run status", run_summary.get("status", snapshot.get("run_status", "UNKNOWN")))
    c2.metric("Scanned", run_summary.get("articles_scanned", 0))
    c3.metric("Curated", snapshot.get("total_after_dedup", run_summary.get("articles_after_dedup", 0)))
    c4.metric("Selected", run_summary.get("articles_selected", len(snapshot.get("curated_stories", []))))
    c5.metric("Freshness", freshness.get("label", "Unknown"))

    render_section_header("Operational Health", "What is ready, what is active, and what still depends on fallback.")
    health = st.columns(5)
    health[0].metric("Overrides active", "Yes" if bool(overrides) else "No")
    health[1].metric("Agents useful", "Yes" if context.get("agents_useful") else "No")
    health[2].metric("Cards available", "Yes" if runtime.get("cards_exist") else "No")
    health[3].metric("Email enabled", "Yes" if runtime.get("email_enabled") else "No")
    health[4].metric("Data source", {
        "structured_snapshot": "Snapshot",
        "fallback_files": "Fallback",
        "missing": "Missing",
    }.get(freshness.get("source", ""), "Unknown"))

    render_section_header("Agent Runtime", "Visibility into agent latency, fallbacks and useful output count.")
    runtime_cols = st.columns(4)
    runtime_cols[0].metric("Pipelines", agent_runtime.get("pipelines", 0))
    runtime_cols[1].metric("Calls OK", agent_runtime.get("calls_succeeded", 0))
    runtime_cols[2].metric("Timeouts / Fail", f"{agent_runtime.get('calls_timed_out', 0)} / {agent_runtime.get('calls_failed', 0)}")
    runtime_cols[3].metric("Useful outputs", agent_runtime.get("useful_outputs", 0))

    render_section_header("Instagram Today", "Morning and afternoon editorial digest blocks at a glance.")
    d1, d2 = st.columns(2)
    with d1:
        with card_container(accent="morning"):
            st.subheader("Morning Digest")
            stories = _safe_list(plan.get("instagram_morning_digest", []))
            render_status_pill(f"{len(stories)} stories", "info")
            for article in stories[:5]:
                st.write(f"• {article.get('title', 'Sem título')}")
            if not stories:
                render_empty_state("No morning digest", "There is no active morning digest in the current structured plan.")
    with d2:
        with card_container(accent="afternoon"):
            st.subheader("Afternoon Digest")
            stories = _safe_list(plan.get("instagram_afternoon_digest", []))
            render_status_pill(f"{len(stories)} stories", "info")
            for article in stories[:5]:
                st.write(f"• {article.get('title', 'Sem título')}")
            if not stories:
                render_empty_state("No afternoon digest", "There is no active afternoon digest in the current structured plan.")

    render_section_header("Content Overview", "Fast preview of the other channels planned for this run.")
    cols = st.columns(4)
    channel_preview = [
        ("X", [plan.get("x_thread_1"), plan.get("x_thread_2")]),
        ("YouTube", [plan.get("youtube_daily")]),
        ("Reddit", _safe_list(plan.get("reddit_candidates", []))[:3]),
        ("Discord", [plan.get("discord_post")]),
    ]
    for col, (label, items) in zip(cols, channel_preview):
        with col:
            with card_container():
                st.markdown(f"**{label}**")
                visible = False
                for item in items:
                    if not item:
                        continue
                    visible = True
                    st.write(item.get("title", "Sem título"))
                if not visible:
                    st.caption("Sem conteúdo activo.")


def _render_news_browser(context: dict):
    stories = _safe_list((context.get("story_sets", {}) or {}).get("curated_stories", []))
    render_page_header(
        "News Browser",
        "Filter curated stories, open direct sources and push promising items into working digest drafts.",
    )
    _render_freshness_notice(context)

    top_actions = st.columns(3)
    with top_actions[0]:
        if st.button("Open Latest Brief", use_container_width=True):
            _open_path_feedback((context.get("brief", {}) or {}).get("path", ""))
    with top_actions[1]:
        if st.button("Go to Instagram", use_container_width=True):
            _set_navigation("Instagram")
    with top_actions[2]:
        if st.button("Open Overrides", use_container_width=True):
            _set_navigation("Overrides")

    if not stories:
        render_empty_state("No curated stories available", "Run the normal pipeline first so the dashboard can load the latest structured story set.")
        return

    with card_container(soft=True):
        render_section_header("Filters", "Keep filtering controls together so results stay easy to scan.", level=3)
        categories = sorted({story.get("category", "unknown") for story in stories})
        sources = sorted({story.get("source", "Fonte desconhecida") for story in stories})
        filters = st.columns([1.1, 1.1, 0.9, 1.4])
        category_filter = filters[0].multiselect("Category", categories)
        source_filter = filters[1].multiselect("Source", sources)
        min_score = filters[2].slider("Min score", min_value=0, max_value=100, value=0)
        search_text = filters[3].text_input("Search")

    filtered = []
    search_lower = search_text.lower().strip()
    for story in stories:
        if category_filter and story.get("category", "unknown") not in category_filter:
            continue
        if source_filter and story.get("source", "Fonte desconhecida") not in source_filter:
            continue
        if story.get("score", 0) < min_score:
            continue
        haystack = " ".join([
            story.get("title", ""),
            story.get("summary", ""),
            story.get("source", ""),
        ]).lower()
        if search_lower and search_lower not in haystack:
            continue
        filtered.append(story)

    render_section_header("Results", f"{len(filtered)} stories after filters.")
    _render_preview_snippet()

    for idx, article in enumerate(filtered, 1):
        with card_container():
            _render_story_summary(article)
            _render_story_actions(article, f"news_{idx}", allow_digest_actions=True)


def _render_digest_variant_cards(channel: str, plan: dict, accent: str):
    current_value = int(st.session_state.get("dashboard_override_draft", {}).get(channel, 0))
    alternatives = _safe_list(plan.get(f"{channel}_alternatives", []))
    variants = [
        ("Primary", _safe_list(plan.get(channel, [])), 0),
        ("Alternative 1", alternatives[0] if len(alternatives) > 0 else [], 1),
        ("Alternative 2", alternatives[1] if len(alternatives) > 1 else [], 2),
    ]
    cols = st.columns(3)
    for col, (label, stories, value) in zip(cols, variants):
        with col:
            with card_container(accent=accent if current_value == value else None, soft=current_value != value):
                st.markdown(f"**{label}**")
                render_status_pill("Active selection" if current_value == value else "Available fallback", "red" if current_value == value else "muted")
                st.caption(f"{len(stories)} stories")
                for story in stories[:4]:
                    st.write(f"• {story.get('title', 'Sem título')}")
                if not stories:
                    st.caption("No stories in this variant.")
                if st.button(
                    "Use This Variant" if current_value != value else "Current Variant",
                    key=f"{channel}_{value}_set",
                    use_container_width=True,
                    disabled=current_value == value,
                ):
                    _set_digest_variant(channel, value, plan)


def _render_digest_story_draft(channel: str, stories: list[dict]):
    render_section_header(
        "Selected Stories",
        "Session-only preview. Add/remove/reorder stays local to this browser session; only variant overrides are persisted.",
        level=3,
    )
    if not stories:
        render_empty_state("No stories in this digest", "There are no stories available for the current digest draft.")
        return

    for idx, article in enumerate(stories):
        with card_container(soft=True):
            _render_story_summary(article)
            first_row = st.columns(3)
            with first_row[0]:
                render_link_action(article.get("link", ""), "Open Source", f"{channel}_{idx}_open")
            with first_row[1]:
                _copy_button("Copy Link", article.get("link", ""), f"{channel}_{idx}_copy", slot_key=f"{channel}_{idx}_copy_slot")
            with first_row[2]:
                if st.button("Remove", key=f"{channel}_{idx}_remove", use_container_width=True):
                    _remove_story_from_digest(channel, idx)
                    st.rerun()

            second_row = st.columns(2)
            with second_row[0]:
                if st.button("Move Up", key=f"{channel}_{idx}_up", use_container_width=True, disabled=idx == 0):
                    _move_story(channel, idx, -1)
                    st.rerun()
            with second_row[1]:
                if st.button("Move Down", key=f"{channel}_{idx}_down", use_container_width=True, disabled=idx == len(stories) - 1):
                    _move_story(channel, idx, 1)
                    st.rerun()
            render_copy_buffer(f"{channel}_{idx}_copy_slot")


def _render_digest_assets(channel: str, label: str, output: dict, pack: dict, card_lookup: dict, stories: list[dict], accent: str):
    render_section_header("Generated Assets", f"{label} pack, prompts, QA and card state.", level=3)

    tabs = st.tabs(["Digest Pack", "Image Prompt", "Voice Script", "QA", "Card"])

    with tabs[0]:
        with card_container(accent=accent):
            _render_digest_pack(pack, f"{channel}_pack")

    with tabs[1]:
        render_prompt_block(
            "Image Prompt",
            output.get("image_prompt", ""),
            "The latest run did not persist an image prompt for this digest.",
            accent=accent,
        )
        _copy_button("Copy Image Prompt", output.get("image_prompt", ""), f"{channel}_copy_image", slot_key=f"{channel}_image_slot")
        render_copy_buffer(f"{channel}_image_slot")

    with tabs[2]:
        render_prompt_block(
            "Voice Script",
            output.get("voice_script", ""),
            "The latest run did not persist a voice script for this digest.",
            accent=accent,
        )
        _copy_button("Copy Voice Script", output.get("voice_script", ""), f"{channel}_copy_voice", slot_key=f"{channel}_voice_slot")
        render_copy_buffer(f"{channel}_voice_slot")

    with tabs[3]:
        with card_container():
            _render_qa_block(output.get("qa", ""), f"{channel}_qa")

    with tabs[4]:
        card_key = "morning_digest" if channel == "instagram_morning_digest" else "afternoon_digest"
        card_path = card_lookup.get(card_key, "")
        with card_container():
            if card_path and Path(card_path).exists():
                st.image(card_path, use_container_width=True)
                actions = st.columns(2)
                with actions[0]:
                    if st.button("Open Card Folder", key=f"{channel}_open_cards", use_container_width=True):
                        _open_path_feedback(Path(card_path).parent)
                with actions[1]:
                    _copy_button("Copy Card Path", card_path, f"{channel}_copy_card_path", slot_key=f"{channel}_card_slot")
                render_copy_buffer(f"{channel}_card_slot")
            else:
                render_empty_state("No card available", "This digest does not currently have a generated card in the latest run.")


def _render_digest_editor(channel: str, label: str, output: dict, pack: dict, card_lookup: dict, plan: dict, accent: str):
    stories = _safe_list(st.session_state.get("dashboard_digest_drafts", {}).get(channel, []))
    current_variant = int(st.session_state.get("dashboard_override_draft", {}).get(channel, 0))
    has_pack = bool(pack)
    has_card = bool(card_lookup.get("morning_digest" if channel == "instagram_morning_digest" else "afternoon_digest", ""))

    render_section_header(label, "Review the active digest, compare variants, then inspect generated assets.")
    render_notice(
        "Persistence model",
        "Save Variant Override only persists the selected variant (0/1/2). Manual story edits below are session-only preview and are not written back to the pipeline state.",
        "warn",
    )
    summary = st.columns(4)
    summary[0].metric("Stories", len(stories))
    summary[1].metric("Persisted variant", current_variant)
    summary[2].metric("Pack ready", "Yes" if has_pack else "Fallback")
    summary[3].metric("Card", "Yes" if has_card else "No")

    action_row = st.columns(4)
    with action_row[0]:
        if st.button("Save Variant Override", key=f"{channel}_save_active", use_container_width=True, type="primary"):
            _save_overrides_feedback()
    with action_row[1]:
        _copy_button("Copy Full Digest Text", _format_digest_copy_text(pack, stories), f"{channel}_copy_full", slot_key=f"{channel}_actions_slot")
    with action_row[2]:
        _copy_button("Copy Community Question", _safe_dict(pack).get("community_question", ""), f"{channel}_copy_question", slot_key=f"{channel}_actions_slot")
    with action_row[3]:
        if st.button("Open Overrides Page", key=f"{channel}_open_overrides", use_container_width=True):
            _set_navigation("Overrides")
    render_copy_buffer(f"{channel}_actions_slot")

    _render_digest_variant_cards(channel, plan, accent)

    main_cols = st.columns([1.15, 0.95], gap="large")
    with main_cols[0]:
        with card_container(accent=accent):
            _render_digest_story_draft(channel, stories)
    with main_cols[1]:
        _render_digest_assets(channel, label, output, pack, card_lookup, stories, accent)


def _render_instagram(context: dict):
    render_page_header(
        "Instagram",
        "Morning and afternoon digests, structured packs, prompts, QA and cards in one operational workspace.",
    )
    _render_freshness_notice(context)
    snapshot = context.get("snapshot", {}) or {}
    plan = _safe_dict(snapshot.get("plan", {}))

    action_row = st.columns(3)
    with action_row[0]:
        if st.button("Save Overrides", use_container_width=True, type="primary"):
            _save_overrides_feedback()
    with action_row[1]:
        if st.button("Open Cards Folder", use_container_width=True):
            _open_path_feedback((context.get("runtime", {}) or {}).get("paths", {}).get("cards_folder", ""))
    with action_row[2]:
        if st.button("Open Latest Brief", use_container_width=True):
            _open_path_feedback((context.get("brief", {}) or {}).get("path", ""))

    if not plan:
        render_empty_state("No structured plan available", "Run the normal pipeline first so the dashboard can load Instagram digests and their variants.")
        return

    tabs = st.tabs(["Morning Digest", "Afternoon Digest"])
    cards = _safe_dict(snapshot.get("card_paths", {}))
    with tabs[0]:
        _render_digest_editor(
            "instagram_morning_digest",
            "Morning Digest",
            _safe_dict(plan.get("instagram_morning_output", {})),
            _safe_dict(plan.get("instagram_morning_pack", {})),
            cards,
            plan,
            "morning",
        )
    with tabs[1]:
        _render_digest_editor(
            "instagram_afternoon_digest",
            "Afternoon Digest",
            _safe_dict(plan.get("instagram_afternoon_output", {})),
            _safe_dict(plan.get("instagram_afternoon_pack", {})),
            cards,
            plan,
            "afternoon",
        )


def _render_channel_output_block(output: dict, copy_key: str, empty_text: str):
    output = _safe_dict(output)
    if output.get("post"):
        with card_container():
            st.markdown("**Generated Output**")
            st.code(output.get("post", ""), language="text")
            slot = f"{copy_key}_output_slot"
            _copy_button("Copy Output", output.get("post", ""), f"{copy_key}_output", slot_key=slot)
            render_copy_buffer(slot)
    else:
        render_empty_state("No generated output", empty_text)


def _render_other_channels(context: dict):
    render_page_header(
        "Other Channels",
        "Keep X, YouTube, Reddit and Discord visible without overloading the workspace.",
    )
    _render_freshness_notice(context)
    snapshot = context.get("snapshot", {}) or {}
    plan = _safe_dict(snapshot.get("plan", {}))
    agent_outputs = _safe_list(snapshot.get("agent_outputs", []))

    sections = st.tabs(["X", "YouTube", "Reddit", "Discord"])

    with sections[0]:
        render_section_header("X Threads", "Two lighter editorial slots with direct source access.")
        for label, channel in [("Thread 1", "x_thread_1"), ("Thread 2", "x_thread_2")]:
            article = _safe_dict(plan.get(channel, {}))
            with card_container():
                st.subheader(label)
                if not article:
                    render_empty_state("No story selected", "This thread slot is empty in the latest plan.")
                    continue
                _render_story_summary(article)
                _render_story_actions(article, f"x_{channel}")
                output = find_agent_output_for_article(article, agent_outputs)
                _render_channel_output_block(output, f"x_{channel}", "No generated thread copy is available for this slot.")

    with sections[1]:
        render_section_header("YouTube Daily", "Daily video slot with direct source and optional generated output.")
        article = _safe_dict(plan.get("youtube_daily", {}))
        with card_container():
            if article:
                _render_story_summary(article)
                _render_story_actions(article, "youtube_daily")
                output = find_agent_output_for_article(article, agent_outputs)
                _render_channel_output_block(output, "youtube_daily", "No generated YouTube output is available for this slot.")
                if output.get("voice_script"):
                    with st.expander("Voice Script", expanded=False):
                        st.code(output.get("voice_script", ""), language="text")
                        _copy_button("Copy Voice Script", output.get("voice_script", ""), "yt_voice_copy", slot_key="yt_voice_slot")
                        render_copy_buffer("yt_voice_slot")
            else:
                render_empty_state("No YouTube story selected", "This channel has no active daily pick in the latest run.")

    with sections[2]:
        render_section_header("Reddit Candidates", "Shortlist of eligible stories for Reddit.")
        reddit_articles = _safe_list(plan.get("reddit_candidates", []))
        if not reddit_articles:
            render_empty_state("No Reddit candidates", "The planner did not persist eligible Reddit stories in the latest run.")
        for idx, article in enumerate(reddit_articles, 1):
            with card_container():
                st.markdown(f"**Candidate {idx}**")
                _render_story_summary(article)
                _render_story_actions(article, f"reddit_{idx}")

    with sections[3]:
        render_section_header("Discord", "Single operational slot with explicit silence when nothing qualifies.")
        article = _safe_dict(plan.get("discord_post", {}))
        with card_container():
            if article:
                _render_story_summary(article)
                _render_story_actions(article, "discord_post")
                output = find_agent_output_for_article(article, agent_outputs)
                _render_channel_output_block(output, "discord_post", "No generated Discord copy is available for this slot.")
            else:
                render_empty_state("Discord is silent", "No Discord post was selected for the latest run.")


def _render_image_voice(context: dict):
    render_page_header(
        "Image + Voice",
        "Use this page as a production prep workspace for prompts, scripts and the stories behind them.",
    )
    _render_freshness_notice(context)
    snapshot = context.get("snapshot", {}) or {}
    plan = _safe_dict(snapshot.get("plan", {}))
    agent_outputs = _safe_list(snapshot.get("agent_outputs", []))

    insta_tabs = st.tabs(["Instagram Morning", "Instagram Afternoon", "Top 3 Agent Outputs"])

    def render_digest_media(label, digest_key, output_key, accent):
        stories = _safe_list(plan.get(digest_key, []))
        output = _safe_dict(plan.get(output_key, {}))

        cols = st.columns([1.05, 0.95], gap="large")
        with cols[0]:
            with card_container(accent=accent):
                render_section_header(label, "Source stories and direct links for this creative block.", level=3)
                if stories:
                    for idx, article in enumerate(stories[:7], 1):
                        st.markdown(f"**{idx}. {article.get('title', 'Sem título')}**")
                        st.caption(article.get("source", "Fonte desconhecida"))
                        story_actions = st.columns(2)
                        with story_actions[0]:
                            render_link_action(article.get("link", ""), "Open Source", f"{digest_key}_{idx}_open")
                        with story_actions[1]:
                            _copy_button("Copy Story Link", article.get("link", ""), f"{digest_key}_{idx}_copy_link", slot_key=f"{digest_key}_{idx}_story_slot")
                        render_copy_buffer(f"{digest_key}_{idx}_story_slot")
                else:
                    render_empty_state("No stories available", "This digest has no persisted stories in the latest run.")
        with cols[1]:
            render_prompt_block(
                "Image Prompt",
                output.get("image_prompt", ""),
                "No image prompt is available for this digest.",
                accent=accent,
            )
            _copy_button("Copy Image Prompt", output.get("image_prompt", ""), f"{digest_key}_img_copy", slot_key=f"{digest_key}_image_slot")
            render_copy_buffer(f"{digest_key}_image_slot")
            render_prompt_block(
                "Voice Script",
                output.get("voice_script", ""),
                "No voice script is available for this digest.",
                accent=accent,
            )
            _copy_button("Copy Voice Script", output.get("voice_script", ""), f"{digest_key}_voice_copy", slot_key=f"{digest_key}_voice_slot")
            render_copy_buffer(f"{digest_key}_voice_slot")

    with insta_tabs[0]:
        render_digest_media("Morning Digest", "instagram_morning_digest", "instagram_morning_output", "morning")
    with insta_tabs[1]:
        render_digest_media("Afternoon Digest", "instagram_afternoon_digest", "instagram_afternoon_output", "afternoon")
    with insta_tabs[2]:
        render_section_header("Top 3 Agent Outputs", "Quick access to article-level image and voice assets.")
        if not agent_outputs:
            render_empty_state("No agent outputs persisted", "The latest run does not include article-level creative outputs.")
        for idx, output in enumerate(agent_outputs, 1):
            article = _safe_dict(output.get("article", {}))
            with st.expander(f"{idx}. {article.get('title', 'Sem título')}", expanded=False):
                _render_story_summary(article)
                if output.get("image_prompt"):
                    st.code(output.get("image_prompt", ""), language="text")
                    _copy_button("Copy Image Prompt", output.get("image_prompt", ""), f"top_agent_image_{idx}", slot_key=f"top_agent_{idx}_slot")
                if output.get("voice_script"):
                    st.code(output.get("voice_script", ""), language="text")
                    _copy_button("Copy Voice Script", output.get("voice_script", ""), f"top_agent_voice_{idx}", slot_key=f"top_agent_{idx}_slot")
                render_copy_buffer(f"top_agent_{idx}_slot")


def _render_brief_page(context: dict):
    brief = context.get("brief", {}) or {}
    render_page_header(
        "Brief",
        "Use the latest brief as a working artifact, with quick access to the file, folder and raw markdown.",
    )
    _render_freshness_notice(context)
    if not brief.get("exists"):
        render_empty_state("Brief not available", "The latest brief file does not exist yet for this environment or run state.")
        return

    actions = st.columns(4)
    with actions[0]:
        if st.button("Reload Brief", use_container_width=True, type="primary"):
            st.rerun()
    with actions[1]:
        st.download_button(
            "Download Markdown",
            data=brief.get("content", ""),
            file_name=Path(brief.get("path", "SIMULA_BRIEF_HOJE.md")).name,
            mime="text/markdown",
            use_container_width=True,
        )
    with actions[2]:
        if st.button("Open Brief File", use_container_width=True):
            _open_path_feedback(brief.get("path", ""))
    with actions[3]:
        if st.button("Open Brief Folder", use_container_width=True):
            _open_path_feedback(brief.get("folder", ""))

    render_path_block("Brief path", brief.get("path", ""))
    tabs = st.tabs(["Rendered", "Raw markdown"])
    with tabs[0]:
        with card_container():
            st.markdown(brief.get("content", ""))
    with tabs[1]:
        with card_container():
            st.code(brief.get("content", ""), language="markdown")


def _render_overrides_page(context: dict):
    snapshot = context.get("snapshot", {}) or {}
    plan = _safe_dict(snapshot.get("plan", {}))
    current_saved = load_current_overrides()

    render_page_header(
        "Overrides",
        "Guided override controls for digest and channel variants, with a preview before you save.",
    )
    _render_freshness_notice(context)

    if not plan:
        render_empty_state("Plan not available", "Override preview is limited until a normal run persists a structured plan into the latest snapshot.")

    top = st.columns(3)
    with top[0]:
        if st.button("Save Overrides", use_container_width=True, type="primary"):
            _save_overrides_feedback()
    with top[1]:
        if st.button("Reset Overrides", use_container_width=True):
            ok, message = reset_current_overrides()
            if ok:
                st.session_state["dashboard_override_draft"] = {field: 0 for field in SUPPORTED_OVERRIDE_FIELDS}
                st.success(f"Overrides limpos em {message}")
            else:
                st.error(message)
    with top[2]:
        if st.button("Open Overrides File", use_container_width=True):
            _open_path_feedback(ensure_overrides_file())

    summary = st.columns(3)
    summary[0].metric("Saved overrides", len(current_saved))
    summary[1].metric("Morning variant", st.session_state.get("dashboard_override_draft", {}).get("instagram_morning_digest", 0))
    summary[2].metric("Afternoon variant", st.session_state.get("dashboard_override_draft", {}).get("instagram_afternoon_digest", 0))

    main_cols = st.columns([1, 1], gap="large")
    with main_cols[0]:
        with card_container():
            render_section_header("Guided Selection", "Pick digest/channel variants without editing raw JSON.", level=3)
            for field in SUPPORTED_OVERRIDE_FIELDS:
                options = get_override_options(plan, field)
                option_values = [value for value, _ in options]
                labels = {value: label for value, label in options}
                current_value = int(st.session_state.get("dashboard_override_draft", {}).get(field, 0))
                chosen = st.selectbox(
                    field.replace("_", " ").title(),
                    option_values,
                    index=option_values.index(current_value) if current_value in option_values else 0,
                    format_func=lambda value, labels=labels: labels[value],
                    key=f"override_selector_{field}",
                )
                st.session_state["dashboard_override_draft"][field] = chosen

    with main_cols[1]:
        with card_container():
            render_section_header("Preview of Effect", "Check the resulting digest selections before you save.", level=3)
            preview_cols = st.columns(2)
            for col, field in zip(preview_cols, ["instagram_morning_digest", "instagram_afternoon_digest"]):
                with col:
                    resolved = _safe_list(resolve_preview_selection(
                        plan,
                        field,
                        int(st.session_state.get("dashboard_override_draft", {}).get(field, 0)),
                    ))
                    st.markdown(f"**{DIGEST_LABELS.get(field, field)}**")
                    render_status_pill(
                        f"Variant {st.session_state.get('dashboard_override_draft', {}).get(field, 0)}",
                        "info",
                    )
                    for story in resolved[:5]:
                        st.write(f"• {story.get('title', 'Sem título')}")
                    if not resolved:
                        st.caption("No stories available.")

    with st.expander("Current saved JSON", expanded=False):
        st.code(json.dumps(current_saved, indent=2, ensure_ascii=False), language="json")


def _render_settings_status(context: dict):
    runtime = context.get("runtime", {}) or {}
    paths = runtime.get("paths", {}) or {}
    assets_status = runtime.get("assets_status", {}) or {}

    render_page_header(
        "Settings / Status",
        "Operational diagnostics for feature availability, required assets and file paths.",
    )
    _render_freshness_notice(context)

    cols = st.columns(4)
    cols[0].metric("MiniMax", "Configured" if runtime.get("minimax_configured") else "Missing")
    cols[1].metric("Email", "Enabled" if runtime.get("email_enabled") else "Disabled")
    cols[2].metric("Cards", "Enabled" if runtime.get("card_generation_enabled") else "Disabled")
    cols[3].metric("Snapshot", "Ready" if runtime.get("snapshot_exists") else "Missing")

    render_section_header("Feature Status", "High-level operational switches without exposing secrets.")
    with card_container():
        render_status_pill("Email ready" if runtime.get("email_ready") else "Email not ready", "ok" if runtime.get("email_ready") else "warn")
        render_status_pill("Assets ready" if runtime.get("assets_ready") else "Assets missing", "ok" if runtime.get("assets_ready") else "warn")
        render_status_pill("Cards exist" if runtime.get("cards_exist") else "No cards", "ok" if runtime.get("cards_exist") else "muted")
        render_status_pill("Overrides file" if runtime.get("overrides_exists") else "No overrides file", "info" if runtime.get("overrides_exists") else "muted")

    render_section_header("Assets", "Required dashboard-visible resources for card generation.")
    with card_container():
        for name, exists in assets_status.items():
            render_status_pill(f"{name}: {'ok' if exists else 'missing'}", "ok" if exists else "warn")

    render_section_header("Paths", "Useful operational paths, shown cleanly instead of as a raw dump.")
    with card_container():
        for label, path in paths.items():
            render_path_block(label.replace("_", " ").title(), path)

    actions = st.columns(3)
    with actions[0]:
        if st.button("Open Brief Folder", use_container_width=True):
            _open_path_feedback(paths.get("brief_folder", ""))
    with actions[1]:
        if st.button("Open Cards Folder", use_container_width=True):
            _open_path_feedback(paths.get("cards_folder", ""))
    with actions[2]:
        if st.button("Open Overrides File", use_container_width=True):
            _open_path_feedback(ensure_overrides_file())


def main():
    st.set_page_config(
        page_title="Simula Operations Dashboard",
        page_icon="🏎️",
        layout="wide",
    )
    inject_custom_css()

    context = load_dashboard_context()
    _init_state(context)
    _render_sidebar(context)

    nav = st.session_state.get("dashboard_nav", "Overview")
    if nav == "Overview":
        _render_overview(context)
    elif nav == "News Browser":
        _render_news_browser(context)
    elif nav == "Instagram":
        _render_instagram(context)
    elif nav == "Other Channels":
        _render_other_channels(context)
    elif nav == "Image + Voice":
        _render_image_voice(context)
    elif nav == "Brief":
        _render_brief_page(context)
    elif nav == "Overrides":
        _render_overrides_page(context)
    elif nav == "Settings / Status":
        _render_settings_status(context)


if __name__ == "__main__":
    main()
