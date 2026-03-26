"""SimulaNewsMachine — premium internal dashboard for content operations."""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from dashboard_components import (
    inject_custom_css,
    open_local_path,
    render_copy_buffer,
    render_link_action,
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


def _set_navigation(page: str, focus: str | None = None):
    st.session_state["dashboard_nav"] = page
    if focus:
        st.session_state["dashboard_instagram_focus"] = focus
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


def _copy_button(label: str, text: str, key: str):
    if st.button(label, key=key, use_container_width=True):
        set_copy_buffer(text, label)
        st.toast("Conteúdo preparado para copiar")


def _render_story_summary(article: dict):
    article = article or {}
    st.markdown(f"**{article.get('title', 'Sem título')}**")
    st.caption(
        f"{article.get('source', 'Fonte desconhecida')} | "
        f"{article.get('category', 'unknown')} | Score {article.get('score', 0)}"
    )
    if article.get("summary"):
        st.write((article.get("summary") or "")[:240])
    if article.get("link"):
        st.markdown(f"[{article.get('link')}]({article.get('link')})")


def _render_story_actions(article: dict, key_prefix: str, allow_digest_actions: bool = False):
    article = article or {}
    url = article.get("link", "")
    cols = st.columns([1.1, 1.1, 1.1, 1.1, 1.1]) if allow_digest_actions else st.columns([1.2, 1.2, 1.2])
    with cols[0]:
        render_link_action(url, "Open Source", f"{key_prefix}_open")
    with cols[1]:
        _copy_button("Copy Link", url, f"{key_prefix}_copy")
    with cols[2]:
        if st.button("Preview in Brief", key=f"{key_prefix}_brief", use_container_width=True):
            st.session_state["dashboard_preview_article"] = article.get("title", "")
    if allow_digest_actions:
        with cols[3]:
            if st.button("Add to Morning", key=f"{key_prefix}_add_morning", use_container_width=True):
                _add_story_to_digest("instagram_morning_digest", article)
                st.toast("Adicionado ao draft da manhã")
        with cols[4]:
            if st.button("Add to Afternoon", key=f"{key_prefix}_add_afternoon", use_container_width=True):
                _add_story_to_digest("instagram_afternoon_digest", article)
                st.toast("Adicionado ao draft da tarde")


def _render_preview_snippet():
    article_title = st.session_state.get("dashboard_preview_article", "")
    if not article_title:
        return
    snippet = extract_brief_snippet(article_title)
    if not snippet:
        st.info("Sem snippet correspondente no brief actual.")
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
    cols = st.columns(3)
    cols[0].metric("QA Average", qa.get("average", "N/A"))
    cols[1].metric("Approved", "Yes" if qa.get("approved") else "No")
    cols[2].metric("Hashtags", len(qa.get("hashtags", [])))
    if qa.get("scores"):
        st.caption("Scores")
        for name, value in qa.get("scores", {}).items():
            render_status_pill(f"{name}: {value}", "muted")
    if qa.get("issues"):
        st.warning(" | ".join(str(issue) for issue in qa.get("issues", [])))
    if qa.get("hashtags"):
        _copy_button("Copy Hashtags", " ".join(str(x) for x in qa.get("hashtags", [])), f"{key_prefix}_hashtags")


def _render_digest_pack(pack: dict, key_prefix: str):
    pack = _safe_dict(pack)
    if not pack:
        st.info("Fallback mode — sem digest pack estruturado persistido no latest run.")
        return

    st.markdown(f"**Digest Theme**  \n{pack.get('digest_theme', 'N/A')}")
    st.markdown(f"**Cover Hook**  \n{pack.get('cover_hook', 'N/A')}")
    cols = st.columns(3)
    with cols[0]:
        _copy_button("Copy Cover Hook", pack.get("cover_hook", ""), f"{key_prefix}_hook")
    with cols[1]:
        _copy_button("Copy Caption Intro", pack.get("caption_intro", ""), f"{key_prefix}_caption_intro")
    with cols[2]:
        _copy_button("Copy Community Question", pack.get("community_question", ""), f"{key_prefix}_question")

    slides = _safe_list(pack.get("slides", []))
    if slides:
        st.markdown("**Slides**")
        for idx, slide in enumerate(slides[:7], 1):
            if isinstance(slide, dict):
                st.markdown(
                    f"{idx}. **{slide.get('news_title', 'N/A')}**  \n"
                    f"{slide.get('mini_summary', '')}  \n"
                    f"*Porque importa:* {slide.get('why_it_matters', '')}"
                )
            else:
                st.markdown(f"{idx}. {slide}")

    if pack.get("caption_news_list"):
        st.markdown("**Caption News List**")
        for item in _safe_list(pack.get("caption_news_list", [])):
            st.write(str(item))

    st.markdown(f"**Notes for Design**  \n{pack.get('notes_for_design', 'N/A')}")


def _render_sidebar(context: dict):
    run_summary = context.get("run_summary", {}) or {}
    runtime = context.get("runtime", {}) or {}
    snapshot = context.get("snapshot", {}) or {}

    st.sidebar.title("Simula Operations")
    st.sidebar.caption("Daily content control center")
    render_status_pill(
        f"Run {run_summary.get('status', snapshot.get('run_status', 'UNKNOWN'))}",
        "ok" if run_summary.get("status", snapshot.get("run_status", "UNKNOWN")) == "OK" else "warn",
    )
    if run_summary.get("ended_at"):
        st.sidebar.caption(run_summary.get("ended_at"))

    c1, c2 = st.sidebar.columns(2)
    c1.metric("Scanned", run_summary.get("articles_scanned", 0))
    c2.metric("Selected", run_summary.get("articles_selected", 0))
    c3, c4 = st.sidebar.columns(2)
    c3.metric("Feeds OK", run_summary.get("feeds_ok", 0))
    c4.metric("Cards", len((context.get("cards", {}) or {}).get("cards", [])))

    st.sidebar.radio("Navigation", NAV_ITEMS, key="dashboard_nav")

    st.sidebar.markdown("---")
    if st.sidebar.button("Reload data", use_container_width=True):
        _init_state(load_dashboard_context(), force=True)
        st.rerun()

    if st.sidebar.button("Open overrides file", use_container_width=True):
        _open_path_feedback(ensure_overrides_file())

    if st.sidebar.button("Save overrides", use_container_width=True):
        _save_overrides_feedback()

    export_text = build_selection_summary(context, st.session_state.get("dashboard_override_draft", {}))
    st.sidebar.download_button(
        "Export selection summary",
        data=export_text,
        file_name="simula_selection_summary.txt",
        mime="text/plain",
        use_container_width=True,
    )

    if st.sidebar.button("Open latest brief folder", use_container_width=True):
        _open_path_feedback(runtime.get("paths", {}).get("brief_folder", ""))

    if st.sidebar.button("Open cards folder", use_container_width=True):
        _open_path_feedback(runtime.get("paths", {}).get("cards_folder", ""))

    st.sidebar.markdown("---")
    st.sidebar.caption("Status")
    render_status_pill("MiniMax" if runtime.get("minimax_configured") else "MiniMax missing", "ok" if runtime.get("minimax_configured") else "warn")
    render_status_pill("Email on" if runtime.get("email_enabled") else "Email off", "ok" if runtime.get("email_enabled") else "muted")
    render_status_pill("Cards on" if runtime.get("card_generation_enabled") else "Cards off", "ok" if runtime.get("card_generation_enabled") else "muted")
    render_status_pill("Snapshot ready" if runtime.get("snapshot_exists") else "No snapshot", "ok" if runtime.get("snapshot_exists") else "warn")


def _render_overview(context: dict):
    snapshot = context.get("snapshot", {}) or {}
    plan = snapshot.get("plan", {}) or {}
    run_summary = context.get("run_summary", {}) or {}
    runtime = context.get("runtime", {}) or {}
    overrides = context.get("overrides", {}) or {}

    st.title("Overview")
    st.markdown('<div class="section-subtle">Latest run, daily selection and quick operational entry points.</div>', unsafe_allow_html=True)
    if not snapshot.get("exists"):
        st.warning("Structured latest-run snapshot not found. The dashboard is in fallback mode until the next normal run writes a snapshot.")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Run status", run_summary.get("status", snapshot.get("run_status", "UNKNOWN")))
    c2.metric("Scanned", run_summary.get("articles_scanned", 0))
    c3.metric("Curated", snapshot.get("total_after_dedup", run_summary.get("articles_after_dedup", 0)))
    c4.metric("Selected", run_summary.get("articles_selected", len(snapshot.get("curated_stories", []))))

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Overrides active", "Yes" if bool(overrides) else "No")
    c6.metric("Agents useful", "Yes" if context.get("agents_useful") else "No")
    c7.metric("Cards exist", "Yes" if runtime.get("cards_exist") else "No")
    c8.metric("Email enabled", "Yes" if runtime.get("email_enabled") else "No")

    quick = st.columns(4)
    with quick[0]:
        if st.button("View Morning Digest", use_container_width=True):
            _set_navigation("Instagram", "Morning Digest")
    with quick[1]:
        if st.button("View Afternoon Digest", use_container_width=True):
            _set_navigation("Instagram", "Afternoon Digest")
    with quick[2]:
        if st.button("Open Latest Brief", use_container_width=True):
            _open_path_feedback((context.get("brief", {}) or {}).get("path", ""))
    with quick[3]:
        if st.button("Open Overrides", use_container_width=True):
            _set_navigation("Overrides")

    d1, d2 = st.columns(2)
    with d1:
        st.markdown('<div class="dashboard-card morning-accent">', unsafe_allow_html=True)
        st.subheader("Morning Instagram Digest")
        stories = _safe_list(plan.get("instagram_morning_digest", []))
        st.caption(f"{len(stories)} stories")
        for article in stories[:5]:
            st.write(f"• {article.get('title', 'Sem título')}")
        st.markdown('</div>', unsafe_allow_html=True)
    with d2:
        st.markdown('<div class="dashboard-card afternoon-accent">', unsafe_allow_html=True)
        st.subheader("Afternoon Instagram Digest")
        stories = _safe_list(plan.get("instagram_afternoon_digest", []))
        st.caption(f"{len(stories)} stories")
        for article in stories[:5]:
            st.write(f"• {article.get('title', 'Sem título')}")
        st.markdown('</div>', unsafe_allow_html=True)

    st.subheader("Other channels")
    cols = st.columns(4)
    channel_preview = [
        ("X", [plan.get("x_thread_1"), plan.get("x_thread_2")]),
        ("YouTube", [plan.get("youtube_daily")]),
        ("Reddit", _safe_list(plan.get("reddit_candidates", []))[:3]),
        ("Discord", [plan.get("discord_post")]),
    ]
    for col, (label, items) in zip(cols, channel_preview):
        with col:
            st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
            st.markdown(f"**{label}**")
            for item in items:
                if not item:
                    continue
                st.write(item.get("title", "Sem título"))
            st.markdown('</div>', unsafe_allow_html=True)


def _render_news_browser(context: dict):
    stories = _safe_list((context.get("story_sets", {}) or {}).get("curated_stories", []))
    st.title("News Browser")
    st.markdown('<div class="section-subtle">Browse curated stories, open sources, copy links and build session-only digest drafts.</div>', unsafe_allow_html=True)

    if not stories:
        st.warning("Curated stories are not available. Run the normal pipeline to generate a dashboard snapshot.")
        return

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

    st.caption(f"{len(filtered)} stories after filters")
    _render_preview_snippet()

    for idx, article in enumerate(filtered, 1):
        with st.container():
            st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
            _render_story_summary(article)
            _render_story_actions(article, f"news_{idx}", allow_digest_actions=True)
            st.markdown('</div>', unsafe_allow_html=True)


def _render_digest_variant_cards(channel: str, plan: dict):
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
            st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
            active = current_value == value
            st.markdown(f"**{label}**{' — active' if active else ''}")
            st.caption(f"{len(stories)} stories")
            for story in stories[:4]:
                st.write(f"• {story.get('title', 'Sem título')}")
            if st.button(f"Set {label}", key=f"{channel}_{value}_set", use_container_width=True):
                _set_digest_variant(channel, value, plan)
            st.markdown('</div>', unsafe_allow_html=True)


def _render_digest_editor(channel: str, label: str, output: dict, pack: dict, card_lookup: dict, plan: dict):
    st.subheader(label)
    _render_digest_variant_cards(channel, plan)

    st.info("Story add/remove/reorder below is a session-only working draft. Persistent control over the pipeline still happens via digest variant overrides.")

    stories = _safe_list(st.session_state.get("dashboard_digest_drafts", {}).get(channel, []))
    if not stories:
        st.warning("No stories available for this digest.")
    else:
        for idx, article in enumerate(stories):
            with st.container():
                st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
                _render_story_summary(article)
                actions = st.columns(5)
                with actions[0]:
                    render_link_action(article.get("link", ""), "Open Source", f"{channel}_{idx}_open")
                with actions[1]:
                    _copy_button("Copy Link", article.get("link", ""), f"{channel}_{idx}_copy")
                with actions[2]:
                    if st.button("Move Up", key=f"{channel}_{idx}_up", use_container_width=True, disabled=idx == 0):
                        _move_story(channel, idx, -1)
                        st.rerun()
                with actions[3]:
                    if st.button("Move Down", key=f"{channel}_{idx}_down", use_container_width=True, disabled=idx == len(stories) - 1):
                        _move_story(channel, idx, 1)
                        st.rerun()
                with actions[4]:
                    if st.button("Remove", key=f"{channel}_{idx}_remove", use_container_width=True):
                        _remove_story_from_digest(channel, idx)
                        st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

    top_actions = st.columns(4)
    with top_actions[0]:
        if st.button("Save as Active", key=f"{channel}_save_active", use_container_width=True):
            _save_overrides_feedback()
    with top_actions[1]:
        _copy_button("Copy Full Digest Text", _format_digest_copy_text(pack, stories), f"{channel}_copy_full")
    with top_actions[2]:
        _copy_button("Copy Image Prompt", output.get("image_prompt", ""), f"{channel}_copy_image")
    with top_actions[3]:
        _copy_button("Copy Voice Script", output.get("voice_script", ""), f"{channel}_copy_voice")

    pack_col, qa_col = st.columns([1.4, 1])
    with pack_col:
        st.markdown("### Structured Digest Pack")
        _render_digest_pack(pack, f"{channel}_pack")
    with qa_col:
        st.markdown("### QA")
        _render_qa_block(output.get("qa", ""), f"{channel}_qa")

    asset_cols = st.columns(2)
    with asset_cols[0]:
        st.markdown("### Image Prompt")
        if output.get("image_prompt"):
            st.code(output.get("image_prompt", ""), language="text")
        else:
            st.info("No image prompt available.")
    with asset_cols[1]:
        st.markdown("### Voice Script")
        if output.get("voice_script"):
            st.code(output.get("voice_script", ""), language="text")
        else:
            st.info("No voice script available.")

    card_path = card_lookup.get("morning_digest" if channel == "instagram_morning_digest" else "afternoon_digest", "")
    st.markdown("### Card")
    if card_path and Path(card_path).exists():
        st.image(card_path, use_container_width=True)
        if st.button("Open Card Folder", key=f"{channel}_open_cards", use_container_width=False):
            _open_path_feedback(Path(card_path).parent)
    else:
        st.info("No card available for this digest.")


def _render_instagram(context: dict):
    st.title("Instagram")
    st.markdown('<div class="section-subtle">Control morning and afternoon editorial digests, inspect packs, QA, image prompts, voice scripts and cards.</div>', unsafe_allow_html=True)
    snapshot = context.get("snapshot", {}) or {}
    plan = _safe_dict(snapshot.get("plan", {}))

    if not plan:
        st.warning("No structured plan available. Run the normal pipeline first.")
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
        )
    with tabs[1]:
        _render_digest_editor(
            "instagram_afternoon_digest",
            "Afternoon Digest",
            _safe_dict(plan.get("instagram_afternoon_output", {})),
            _safe_dict(plan.get("instagram_afternoon_pack", {})),
            cards,
            plan,
        )


def _render_other_channels(context: dict):
    st.title("Other Channels")
    st.markdown('<div class="section-subtle">Inspect selected stories and generated outputs for X, YouTube, Reddit and Discord.</div>', unsafe_allow_html=True)
    snapshot = context.get("snapshot", {}) or {}
    plan = _safe_dict(snapshot.get("plan", {}))
    agent_outputs = _safe_list(snapshot.get("agent_outputs", []))

    sections = st.tabs(["X", "YouTube", "Reddit", "Discord"])

    with sections[0]:
        for label, channel in [("Thread 1", "x_thread_1"), ("Thread 2", "x_thread_2")]:
            article = _safe_dict(plan.get(channel, {}))
            st.subheader(label)
            if not article:
                st.info("Sem artigo selecionado.")
                continue
            _render_story_summary(article)
            _render_story_actions(article, f"x_{channel}")
            output = find_agent_output_for_article(article, agent_outputs)
            if output.get("post"):
                _copy_button("Copy Output", output.get("post", ""), f"x_{channel}_copy_output")
                st.code(output.get("post", ""), language="text")

    with sections[1]:
        article = _safe_dict(plan.get("youtube_daily", {}))
        if article:
            _render_story_summary(article)
            _render_story_actions(article, "youtube_daily")
            output = find_agent_output_for_article(article, agent_outputs)
            if output.get("post"):
                st.markdown("**Generated Output**")
                _copy_button("Copy Output", output.get("post", ""), "youtube_output_copy")
                st.code(output.get("post", ""), language="text")
            if output.get("voice_script"):
                _copy_button("Copy Voice Script", output.get("voice_script", ""), "yt_voice_copy")
        else:
            st.info("Sem artigo selecionado.")

    with sections[2]:
        reddit_articles = _safe_list(plan.get("reddit_candidates", []))
        if not reddit_articles:
            st.info("Sem candidatos elegíveis.")
        for idx, article in enumerate(reddit_articles, 1):
            st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
            _render_story_summary(article)
            _render_story_actions(article, f"reddit_{idx}")
            st.markdown('</div>', unsafe_allow_html=True)

    with sections[3]:
        article = _safe_dict(plan.get("discord_post", {}))
        if article:
            _render_story_summary(article)
            _render_story_actions(article, "discord_post")
            output = find_agent_output_for_article(article, agent_outputs)
            if output.get("post"):
                _copy_button("Copy Output", output.get("post", ""), "discord_output_copy")
                st.code(output.get("post", ""), language="text")
        else:
            st.info("Discord está em silêncio no latest run.")


def _render_image_voice(context: dict):
    st.title("Image + Voice")
    st.markdown('<div class="section-subtle">Fast access to creative-generation assets and the stories behind them.</div>', unsafe_allow_html=True)
    snapshot = context.get("snapshot", {}) or {}
    plan = _safe_dict(snapshot.get("plan", {}))
    agent_outputs = _safe_list(snapshot.get("agent_outputs", []))

    insta_tabs = st.tabs(["Instagram Morning", "Instagram Afternoon", "Top 3 Agent Outputs"])

    def render_digest_media(label, digest_key, output_key):
        stories = _safe_list(plan.get(digest_key, []))
        output = _safe_dict(plan.get(output_key, {}))
        st.subheader(label)
        if stories:
            for idx, article in enumerate(stories[:7], 1):
                st.write(f"{idx}. {article.get('title', 'Sem título')}")
                story_actions = st.columns([1.1, 1.1, 2])
                with story_actions[0]:
                    render_link_action(article.get("link", ""), "Open Source", f"{digest_key}_{idx}_open")
                with story_actions[1]:
                    _copy_button("Copy Story Link", article.get("link", ""), f"{digest_key}_{idx}_copy_link")
                with story_actions[2]:
                    st.caption(article.get("source", "Fonte desconhecida"))
        else:
            st.info("Sem stories disponíveis.")
        media_cols = st.columns(2)
        with media_cols[0]:
            st.markdown("**Image Prompt**")
            if output.get("image_prompt"):
                st.code(output.get("image_prompt", ""), language="text")
                _copy_button("Copy Image Prompt", output.get("image_prompt", ""), f"{digest_key}_img_copy")
            else:
                st.info("Sem image prompt.")
        with media_cols[1]:
            st.markdown("**Voice Script**")
            if output.get("voice_script"):
                st.code(output.get("voice_script", ""), language="text")
                _copy_button("Copy Voice Script", output.get("voice_script", ""), f"{digest_key}_voice_copy")
            else:
                st.info("Sem voice script.")

    with insta_tabs[0]:
        render_digest_media("Morning Digest", "instagram_morning_digest", "instagram_morning_output")
    with insta_tabs[1]:
        render_digest_media("Afternoon Digest", "instagram_afternoon_digest", "instagram_afternoon_output")
    with insta_tabs[2]:
        if not agent_outputs:
            st.info("Sem agent outputs persistidos.")
        for idx, output in enumerate(agent_outputs, 1):
            article = _safe_dict(output.get("article", {}))
            with st.expander(f"{idx}. {article.get('title', 'Sem título')}", expanded=False):
                _render_story_summary(article)
                if output.get("image_prompt"):
                    st.code(output.get("image_prompt", ""), language="text")
                if output.get("voice_script"):
                    st.code(output.get("voice_script", ""), language="text")


def _render_brief_page(context: dict):
    st.title("Brief")
    brief = context.get("brief", {}) or {}
    if not brief.get("exists"):
        st.warning("O brief final ainda não existe.")
        return

    actions = st.columns(4)
    with actions[0]:
        if st.button("Reload brief", use_container_width=True):
            st.rerun()
    with actions[1]:
        st.download_button(
            "Download markdown",
            data=brief.get("content", ""),
            file_name=Path(brief.get("path", "SIMULA_BRIEF_HOJE.md")).name,
            mime="text/markdown",
            use_container_width=True,
        )
    with actions[2]:
        if st.button("Open brief file", use_container_width=True):
            _open_path_feedback(brief.get("path", ""))
    with actions[3]:
        if st.button("Open brief folder", use_container_width=True):
            _open_path_feedback(brief.get("folder", ""))

    st.caption(brief.get("path", ""))
    tabs = st.tabs(["Rendered", "Raw markdown"])
    with tabs[0]:
        st.markdown(brief.get("content", ""))
    with tabs[1]:
        st.code(brief.get("content", ""), language="markdown")


def _render_overrides_page(context: dict):
    st.title("Overrides")
    st.markdown('<div class="section-subtle">Save digest/channel variant overrides safely as valid JSON.</div>', unsafe_allow_html=True)
    snapshot = context.get("snapshot", {}) or {}
    plan = _safe_dict(snapshot.get("plan", {}))
    current_saved = load_current_overrides()

    if not plan:
        st.warning("No plan available in snapshot. Override preview is limited until the next normal run.")

    for field in SUPPORTED_OVERRIDE_FIELDS:
        options = get_override_options(plan, field)
        option_values = [value for value, _ in options]
        labels = {value: label for value, label in options}
        current_value = int(st.session_state.get("dashboard_override_draft", {}).get(field, 0))
        chosen = st.selectbox(
            field,
            option_values,
            index=option_values.index(current_value) if current_value in option_values else 0,
            format_func=lambda value, labels=labels: labels[value],
            key=f"override_selector_{field}",
        )
        st.session_state["dashboard_override_draft"][field] = chosen

    buttons = st.columns(3)
    with buttons[0]:
        if st.button("Save overrides", use_container_width=True):
            _save_overrides_feedback()
    with buttons[1]:
        if st.button("Reset overrides", use_container_width=True):
            ok, message = reset_current_overrides()
            if ok:
                st.session_state["dashboard_override_draft"] = {field: 0 for field in SUPPORTED_OVERRIDE_FIELDS}
                st.success(f"Overrides limpos em {message}")
            else:
                st.error(message)
    with buttons[2]:
        if st.button("Open overrides file", use_container_width=True):
            _open_path_feedback(ensure_overrides_file())

    st.subheader("Current saved JSON")
    st.code(json.dumps(current_saved, indent=2, ensure_ascii=False), language="json")

    st.subheader("Preview of resulting selection")
    preview_cols = st.columns(2)
    for col, field in zip(preview_cols, ["instagram_morning_digest", "instagram_afternoon_digest"]):
        with col:
            resolved = _safe_list(resolve_preview_selection(
                plan,
                field,
                int(st.session_state.get("dashboard_override_draft", {}).get(field, 0)),
            ))
            st.markdown(f"**{DIGEST_LABELS.get(field, field)}**")
            st.caption(f"Active variant: {st.session_state.get('dashboard_override_draft', {}).get(field, 0)}")
            for story in resolved[:5]:
                st.write(f"• {story.get('title', 'Sem título')}")


def _render_settings_status(context: dict):
    st.title("Settings / Status")
    runtime = context.get("runtime", {}) or {}
    paths = runtime.get("paths", {}) or {}
    assets_status = runtime.get("assets_status", {}) or {}

    cols = st.columns(4)
    cols[0].metric("MiniMax", "Configured" if runtime.get("minimax_configured") else "Missing")
    cols[1].metric("Email", "Enabled" if runtime.get("email_enabled") else "Disabled")
    cols[2].metric("Cards", "Enabled" if runtime.get("card_generation_enabled") else "Disabled")
    cols[3].metric("Snapshot", "Ready" if runtime.get("snapshot_exists") else "Missing")

    st.subheader("Assets")
    for name, exists in assets_status.items():
        render_status_pill(f"{name}: {'ok' if exists else 'missing'}", "ok" if exists else "warn")

    st.subheader("Paths")
    for label, path in paths.items():
        st.write(f"**{label}**")
        st.code(path or "N/A", language="text")

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
    render_copy_buffer()

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
