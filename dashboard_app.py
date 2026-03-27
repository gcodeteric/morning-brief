"""SimulaNewsMachine — operator-first publishing workspace."""

from __future__ import annotations

import hashlib
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
    WORKSPACE_PLATFORMS,
    WORKSPACE_PLATFORM_LABELS,
    build_selection_summary,
    load_dashboard_context,
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
    "News Feed",
    "Selected News",
    "Platform Outputs",
    "Advanced / System",
]

SEARCH_SCOPE_OPTIONS = (
    "Title + source",
    "Title only",
    "Source only",
)

SORT_OPTIONS = (
    "Score ↓",
    "Score ↑",
    "Title A-Z",
    "Source A-Z",
    "Category A-Z",
)

DISPLAY_COUNT_OPTIONS = ("24", "48", "96", "All")


def _safe_list(value):
    return value if isinstance(value, list) else []


def _safe_dict(value):
    return value if isinstance(value, dict) else {}


def _widget_key(prefix: str, value: str = "") -> str:
    digest = hashlib.md5(str(value).encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}"


def _story_key(item: dict | None) -> str:
    item = item or {}
    return str(item.get("key") or "")


def _workspace_items(context: dict) -> list[dict]:
    return [item for item in _safe_list(context.get("story_workspace", [])) if _story_key(item)]


def _workspace_lookup(context: dict) -> dict[str, dict]:
    return {item["key"]: item for item in _workspace_items(context)}


def _sanitize_platforms(platforms) -> list[str]:
    values = []
    for platform in _safe_list(platforms):
        if platform in WORKSPACE_PLATFORMS and platform not in values:
            values.append(platform)
    return values


def _default_story_platforms(item: dict) -> list[str]:
    defaults = _sanitize_platforms(item.get("recommended_platforms", []))
    return defaults or ["instagram", "x", "email"]


def _is_recommended_story(item: dict) -> bool:
    item = item or {}
    return bool(item.get("in_active_plan"))


def _display_limit(option: str) -> int | None:
    return None if option == "All" else int(option)


def _story_search_haystack(item: dict, scope: str = "Title + source") -> str:
    item = item or {}
    story = _safe_dict(item.get("story", {}))
    title = story.get("title", "")
    source = story.get("source", "")
    summary = story.get("summary", "")
    tags = " ".join(_safe_list(item.get("planner_tags", [])))
    if scope == "Title only":
        parts = [title]
    elif scope == "Source only":
        parts = [source]
    else:
        parts = [title, source, summary, tags]
    return " ".join(str(part or "") for part in parts).lower()


def _filter_sort_workspace_items(
    items: list[dict],
    *,
    category_filter=None,
    source_filter=None,
    min_score: int = 0,
    search_text: str = "",
    search_scope: str = "Title + source",
    recommended_only: bool = False,
    system_only: bool = False,
    digest_only: bool = False,
    sort_option: str = "Score ↓",
) -> list[dict]:
    category_filter = category_filter or []
    source_filter = source_filter or []
    search_lower = (search_text or "").lower().strip()
    filtered = []

    for item in items or []:
        story = _safe_dict(item.get("story", {}))
        if category_filter and story.get("category", "unknown") not in category_filter:
            continue
        if source_filter and story.get("source", "Fonte desconhecida") not in source_filter:
            continue
        if int(story.get("score", 0) or 0) < min_score:
            continue
        if recommended_only and not _is_recommended_story(item):
            continue
        if system_only and not item.get("selected_by_system"):
            continue
        if digest_only and not item.get("in_current_digest"):
            continue
        if search_lower and search_lower not in _story_search_haystack(item, search_scope):
            continue
        filtered.append(item)

    if sort_option == "Score ↑":
        filtered.sort(key=lambda item: (int(_safe_dict(item.get("story", {})).get("score", 0) or 0), _safe_dict(item.get("story", {})).get("title", "").lower()))
    elif sort_option == "Title A-Z":
        filtered.sort(key=lambda item: _safe_dict(item.get("story", {})).get("title", "").lower())
    elif sort_option == "Source A-Z":
        filtered.sort(key=lambda item: _safe_dict(item.get("story", {})).get("source", "").lower())
    elif sort_option == "Category A-Z":
        filtered.sort(key=lambda item: (_safe_dict(item.get("story", {})).get("category", "").lower(), -int(_safe_dict(item.get("story", {})).get("score", 0) or 0)))
    else:
        filtered.sort(key=lambda item: (-int(_safe_dict(item.get("story", {})).get("score", 0) or 0), _safe_dict(item.get("story", {})).get("title", "").lower()))

    return filtered


def _story_badges(item: dict) -> list[tuple[str, str]]:
    item = item or {}
    story = _safe_dict(item.get("story", {}))
    score = int(story.get("score", 0) or 0)
    category = story.get("category", "unknown")
    planner_tags = _safe_list(item.get("planner_tags", []))

    badges: list[tuple[str, str]] = []
    if _is_recommended_story(item):
        badges.append(("Recommended", "ok"))
    if item.get("selected_by_system"):
        badges.append(("System picked", "info"))
    if any("Morning Digest" in tag for tag in planner_tags):
        badges.append(("Morning Digest", "warn"))
    if any("Afternoon Digest" in tag for tag in planner_tags):
        badges.append(("Afternoon Digest", "info"))
    if score >= 70:
        badges.append(("High Score", "ok"))

    category_labels = {
        "sim_racing": "Sim Racing",
        "motorsport": "Motorsport",
        "nostalgia": "Nostalgia",
        "racing_games": "Racing Games",
        "portugal": "PT",
    }
    label = category_labels.get(category)
    if label:
        badges.append((label, "muted"))
    return badges


def _selected_story_keys(context: dict) -> list[str]:
    available = set(_workspace_lookup(context))
    current = _safe_list(st.session_state.get("dashboard_selected_story_keys", []))
    filtered = [key for key in current if key in available]
    if filtered != current:
        st.session_state["dashboard_selected_story_keys"] = filtered
    return filtered


def _selected_story_items(context: dict) -> list[dict]:
    lookup = _workspace_lookup(context)
    return [lookup[key] for key in _selected_story_keys(context) if key in lookup]


def _collect_story_links(items: list[dict]) -> str:
    links = []
    seen = set()
    for item in items or []:
        link = str(_safe_dict(item.get("story", {})).get("link", "") or "").strip()
        if not link or link in seen:
            continue
        seen.add(link)
        links.append(link)
    return "\n".join(links)


def _get_story_platforms(item: dict) -> list[str]:
    story_key = _story_key(item)
    mapping = dict(st.session_state.get("dashboard_story_platforms", {}))
    current = _sanitize_platforms(mapping.get(story_key, []))
    if not current:
        current = _default_story_platforms(item)
        mapping[story_key] = current
        st.session_state["dashboard_story_platforms"] = mapping
    return current


def _set_story_platforms(story_key: str, platforms) -> list[str]:
    mapping = dict(st.session_state.get("dashboard_story_platforms", {}))
    current = _sanitize_platforms(platforms)
    mapping[story_key] = current
    st.session_state["dashboard_story_platforms"] = mapping
    return current


def _select_multiple_stories(items: list[dict]) -> int:
    current = list(st.session_state.get("dashboard_selected_story_keys", []))
    mapping = dict(st.session_state.get("dashboard_story_platforms", {}))
    added = 0

    for item in items or []:
        story_key = _story_key(item)
        if not story_key:
            continue
        if story_key not in current:
            current.append(story_key)
            added += 1
        mapping[story_key] = _sanitize_platforms(mapping.get(story_key) or _default_story_platforms(item))

    if items:
        st.session_state["dashboard_active_story_key"] = _story_key(items[0])
    st.session_state["dashboard_selected_story_keys"] = current
    st.session_state["dashboard_story_platforms"] = mapping
    return added


def _apply_platform_choice_to_selected(items: list[dict], mode: str = "recommended") -> int:
    mapping = dict(st.session_state.get("dashboard_story_platforms", {}))
    changed = 0
    for item in items or []:
        story_key = _story_key(item)
        if not story_key:
            continue
        values = _default_story_platforms(item) if mode == "recommended" else list(WORKSPACE_PLATFORMS)
        if _sanitize_platforms(mapping.get(story_key, [])) != values:
            changed += 1
        mapping[story_key] = values
        widget_key = _widget_key("story_platforms", story_key)
        st.session_state[widget_key] = values
    st.session_state["dashboard_story_platforms"] = mapping
    return changed


def _select_story(item: dict):
    story_key = _story_key(item)
    if not story_key:
        return
    current = list(st.session_state.get("dashboard_selected_story_keys", []))
    if story_key not in current:
        current.append(story_key)
    st.session_state["dashboard_selected_story_keys"] = current
    _set_story_platforms(story_key, st.session_state.get("dashboard_story_platforms", {}).get(story_key) or _default_story_platforms(item))
    st.session_state["dashboard_active_story_key"] = story_key


def _deselect_story(story_key: str):
    current = [key for key in _safe_list(st.session_state.get("dashboard_selected_story_keys", [])) if key != story_key]
    st.session_state["dashboard_selected_story_keys"] = current
    mapping = dict(st.session_state.get("dashboard_story_platforms", {}))
    mapping.pop(story_key, None)
    st.session_state["dashboard_story_platforms"] = mapping
    if st.session_state.get("dashboard_active_story_key") == story_key:
        st.session_state["dashboard_active_story_key"] = current[0] if current else ""


def _seed_planned_selection(context: dict) -> bool:
    lookup = _workspace_lookup(context)
    seed = [key for key in _safe_list(context.get("selection_seed", [])) if key in lookup]
    if not seed:
        return False

    st.session_state["dashboard_selected_story_keys"] = seed
    mapping = dict(st.session_state.get("dashboard_story_platforms", {}))
    for key in seed:
        mapping[key] = _sanitize_platforms(mapping.get(key) or _default_story_platforms(lookup[key]))
    st.session_state["dashboard_story_platforms"] = mapping
    st.session_state["dashboard_active_story_key"] = seed[0]
    return True


def _clear_story_selection():
    st.session_state["dashboard_selected_story_keys"] = []
    st.session_state["dashboard_story_platforms"] = {}
    st.session_state["dashboard_active_story_key"] = ""


def _init_state(context: dict, force: bool = False):
    current_overrides = load_current_overrides()
    lookup = _workspace_lookup(context)

    if force or "dashboard_nav" not in st.session_state:
        st.session_state["dashboard_nav"] = "News Feed"
    if force or "dashboard_selected_story_keys" not in st.session_state:
        st.session_state["dashboard_selected_story_keys"] = []
    if force or "dashboard_story_platforms" not in st.session_state:
        st.session_state["dashboard_story_platforms"] = {}
    else:
        mapping = {}
        for key, value in dict(st.session_state.get("dashboard_story_platforms", {})).items():
            if key in lookup:
                mapping[key] = _sanitize_platforms(value)
        st.session_state["dashboard_story_platforms"] = mapping
    if force or "dashboard_active_story_key" not in st.session_state:
        st.session_state["dashboard_active_story_key"] = ""
    if force or "dashboard_override_draft" not in st.session_state:
        st.session_state["dashboard_override_draft"] = {
            field: int(current_overrides.get(field, 0)) if str(current_overrides.get(field, 0)).isdigit() else 0
            for field in SUPPORTED_OVERRIDE_FIELDS
        }

    _selected_story_keys(context)


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
        if not str(text or "").strip():
            st.warning("There is no usable text in this block yet.")
            return
        slot = slot_key or key
        set_copy_buffer(text or "", label, slot)
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


def _render_story_summary(story: dict, selected: bool = False):
    story = story or {}
    header_cols = st.columns([6, 1.4, 1.6])
    with header_cols[0]:
        st.markdown(f"#### {story.get('title', 'Sem título')}")
        st.caption(f"{story.get('source', 'Fonte desconhecida')} • {story.get('category', 'unknown')}")
    with header_cols[1]:
        score = int(story.get("score", 0) or 0)
        render_status_pill(f"Score {score}", "info" if score >= 50 else "muted")
    with header_cols[2]:
        render_status_pill("Selected" if selected else "Available", "ok" if selected else "muted")

    summary = str(story.get("summary", "") or "").strip()
    if summary:
        st.write(summary[:240])


def _render_story_context(item: dict):
    planner_tags = _safe_list(item.get("planner_tags", []))
    badges = _story_badges(item)
    if badges:
        for label, tone in badges:
            render_status_pill(label, tone)
    else:
        render_status_pill("Manual pool", "muted")

    recommended = _sanitize_platforms(item.get("recommended_platforms", []))
    if recommended:
        labels = [WORKSPACE_PLATFORM_LABELS.get(platform, platform.title()) for platform in recommended]
        st.caption("Recommended platforms: " + " • ".join(labels))
    if planner_tags:
        st.caption("Used in: " + " • ".join(planner_tags))


def _render_source_actions(story: dict, prefix: str, include_preview: bool = False):
    slot = f"{prefix}_copy_slot"
    actions = st.columns(3 if include_preview else 2)
    with actions[0]:
        render_link_action(story.get("link", ""), "Open Source", f"{prefix}_open")
    with actions[1]:
        _copy_button("Copy Link", story.get("link", ""), f"{prefix}_copy_link", slot_key=slot)
    if include_preview:
        with actions[2]:
            if st.button("Open Outputs", key=f"{prefix}_outputs", use_container_width=True):
                st.session_state["dashboard_active_story_key"] = story.get("link") or story.get("title", "")
                _set_navigation("Platform Outputs")
    render_copy_buffer(slot)


def _render_workspace_summary(context: dict):
    status = _safe_dict(context.get("status", {}))
    runtime = _safe_dict(context.get("runtime", {}))
    selected_count = len(_selected_story_keys(context))
    planned_count = len(_safe_list(context.get("selection_seed", [])))
    summary = st.columns(5)
    summary[0].metric("Stories available", status.get("workspace_stories", len(_workspace_items(context))))
    summary[1].metric("Selected now", selected_count)
    summary[2].metric("Planned stories", planned_count)
    summary[3].metric("Agent outputs useful", "Yes" if context.get("agents_useful") else "Partial")
    summary[4].metric("Cards ready", "Yes" if runtime.get("cards_exist") else "No")


def _render_news_feed(context: dict):
    items = _workspace_items(context)
    selected_keys = set(_selected_story_keys(context))

    render_page_header(
        "News Feed",
        "Browse today’s stories first, pick the ones you want, then move straight into publishing outputs.",
    )
    _render_freshness_notice(context)
    _render_workspace_summary(context)

    actions = st.columns(4)
    with actions[0]:
        if st.button("Use Today’s Planned Stories", use_container_width=True, type="primary"):
            if _seed_planned_selection(context):
                st.toast("Planned stories loaded into the workspace")
                st.rerun()
            st.warning("The latest run does not expose a planned story set yet.")
    with actions[1]:
        if st.button("Open Selected News", use_container_width=True):
            _set_navigation("Selected News")
    with actions[2]:
        if st.button("Open Platform Outputs", use_container_width=True):
            _set_navigation("Platform Outputs")
    with actions[3]:
        if st.button("Open Latest Brief", use_container_width=True):
            _open_path_feedback((context.get("brief", {}) or {}).get("path", ""))

    if not items:
        render_empty_state(
            "No story workspace available",
            "Run the normal pipeline first so the dashboard can load the latest structured story set and per-story workspace data.",
        )
        return

    with card_container(soft=True):
        render_section_header("Filters", "These are operator-controlled filters only. The dashboard keeps the broader rated story pool visible by default.", level=3)
        categories = sorted({item.get("story", {}).get("category", "unknown") for item in items})
        sources = sorted({item.get("story", {}).get("source", "Fonte desconhecida") for item in items})
        top_filters = st.columns([1.05, 1.05, 0.8, 1.2, 1.1, 0.8])
        category_filter = top_filters[0].multiselect("Category", categories)
        source_filter = top_filters[1].multiselect("Source", sources)
        min_score = top_filters[2].slider("Min score", min_value=0, max_value=100, value=0)
        search_text = top_filters[3].text_input("Search")
        sort_option = top_filters[4].selectbox(
            "Sort by",
            list(SORT_OPTIONS),
        )
        display_limit_option = top_filters[5].selectbox("Show", list(DISPLAY_COUNT_OPTIONS), index=1)
        bottom_filters = st.columns([1, 1, 1, 1])
        search_scope = bottom_filters[0].selectbox("Search in", list(SEARCH_SCOPE_OPTIONS), index=0)
        recommended_only = bottom_filters[1].toggle("Recommended only", value=False)
        system_only = bottom_filters[2].toggle("System-picked only", value=False)
        digest_only = bottom_filters[3].toggle("In current digest only", value=False)

    filtered = _filter_sort_workspace_items(
        items,
        category_filter=category_filter,
        source_filter=source_filter,
        min_score=min_score,
        search_text=search_text,
        search_scope=search_scope,
        recommended_only=recommended_only,
        system_only=system_only,
        digest_only=digest_only,
        sort_option=sort_option,
    )
    total_matches = len(filtered)
    limit = _display_limit(display_limit_option)
    visible_items = filtered[:limit] if limit else filtered

    with card_container(soft=True):
        render_section_header(
            "Selection tools",
            f"{len(visible_items)} shown • {total_matches} matching • {len(selected_keys)} selected in this session.",
            level=3,
        )
        st.caption("Story selection is session-only. The latest snapshot and brief stay unchanged until you run the pipeline again.")
        action_row = st.columns(5)
        with action_row[0]:
            if st.button("Select All Visible", key="newsfeed_select_all_visible", use_container_width=True, type="primary"):
                added = _select_multiple_stories(visible_items)
                st.toast(f"{added} stories added to the workspace" if added else "All visible stories were already selected")
                st.rerun()
        with action_row[1]:
            if st.button("Select Recommended", key="newsfeed_select_recommended", use_container_width=True):
                recommended_items = [item for item in visible_items if _is_recommended_story(item)]
                added = _select_multiple_stories(recommended_items)
                st.toast(f"{added} recommended stories added" if added else "No new recommended stories were added")
                st.rerun()
        with action_row[2]:
            if st.button("Clear Selection", key="newsfeed_clear_selection", use_container_width=True):
                _clear_story_selection()
                st.rerun()
        with action_row[3]:
            if st.button("Open Selected News", key="newsfeed_open_selected_news", use_container_width=True):
                _set_navigation("Selected News")
        with action_row[4]:
            if st.button("Open Platform Outputs", key="newsfeed_open_platform_outputs", use_container_width=True):
                _set_navigation("Platform Outputs")

    render_section_header("Stories", f"{len(visible_items)} stories ready for manual selection.")
    if not visible_items:
        render_empty_state("No stories match these filters", "Relax the current filters or load today’s planned stories into the workspace.")
        return

    columns = st.columns(2, gap="large")
    for idx, item in enumerate(visible_items):
        story = _safe_dict(item.get("story", {}))
        story_key = _story_key(item)
        selected = story_key in selected_keys
        with columns[idx % 2]:
            with card_container(accent="success" if selected else None, soft=not selected):
                _render_story_summary(story, selected=selected)
                _render_story_context(item)
                _render_source_actions(story, _widget_key("feed_story", story_key))

                action_row = st.columns(2)
                with action_row[0]:
                    if selected:
                        if st.button("Deselect", key=_widget_key("feed_deselect", story_key), use_container_width=True):
                            _deselect_story(story_key)
                            st.rerun()
                    else:
                        if st.button("Select Story", key=_widget_key("feed_select", story_key), use_container_width=True, type="primary"):
                            _select_story(item)
                            st.rerun()
                with action_row[1]:
                    if st.button("Platform Outputs", key=_widget_key("feed_outputs", story_key), use_container_width=True):
                        _select_story(item)
                        _set_navigation("Platform Outputs")


def _render_selected_news(context: dict):
    items = _selected_story_items(context)

    render_page_header(
        "Selected News",
        "This is your manual working set. Choose platforms per story here before you move into copy-ready output cards.",
    )
    _render_freshness_notice(context)
    render_notice(
        "Selection model",
        "Story selection and platform choices are session-only inside the dashboard. Persisted pipeline state still lives in the latest run snapshot, brief, cards, and manual override file.",
        "warn",
    )

    actions = st.columns(4)
    with actions[0]:
        if st.button("Use Today’s Planned Stories", use_container_width=True, type="primary"):
            if _seed_planned_selection(context):
                st.toast("Planned stories loaded into the workspace")
                st.rerun()
            st.warning("The latest run does not expose a planned story set yet.")
    with actions[1]:
        if st.button("Open Platform Outputs", use_container_width=True):
            _set_navigation("Platform Outputs")
    with actions[2]:
        if st.button("Back to News Feed", use_container_width=True):
            _set_navigation("News Feed")
    with actions[3]:
        if st.button("Clear Selection", use_container_width=True):
            _clear_story_selection()
            st.rerun()

    if not items:
        render_empty_state(
            "No stories selected yet",
            "Pick stories in News Feed first, or pull in the stories already used by today’s plan.",
        )
        return

    with card_container(soft=True):
        render_section_header("Bulk actions", f"{len(items)} selected stories ready for platform setup.", level=3)
        bulk_actions = st.columns(3)
        with bulk_actions[0]:
            if st.button("Use Recommended for All", key="selected_use_recommended_all", use_container_width=True):
                changed = _apply_platform_choice_to_selected(items, mode="recommended")
                st.toast(f"Recommended platforms applied to {changed} stories" if changed else "Recommended platforms were already in place")
                st.rerun()
        with bulk_actions[1]:
            if st.button("Use All Platforms for All", key="selected_use_all_platforms", use_container_width=True):
                changed = _apply_platform_choice_to_selected(items, mode="all")
                st.toast(f"All platforms applied to {changed} stories" if changed else "All selected stories already used every platform")
                st.rerun()
        with bulk_actions[2]:
            _copy_button(
                "Copy All Selected Links",
                _collect_story_links(items),
                "selected_copy_all_links",
                slot_key="selected_copy_all_links_slot",
            )
        render_copy_buffer("selected_copy_all_links_slot")

    render_section_header("Selected Stories", f"{len(items)} story cards ready for platform choices.")
    for item in items:
        story = _safe_dict(item.get("story", {}))
        story_key = _story_key(item)
        widget_key = _widget_key("story_platforms", story_key)
        current_platforms = _get_story_platforms(item)
        if widget_key not in st.session_state:
            st.session_state[widget_key] = current_platforms

        with card_container(accent="success"):
            _render_story_summary(story, selected=True)
            _render_story_context(item)
            _render_source_actions(story, _widget_key("selected_story", story_key))

            chosen_platforms = st.multiselect(
                "Platforms for this story",
                list(WORKSPACE_PLATFORMS),
                default=current_platforms,
                key=widget_key,
                format_func=lambda value: WORKSPACE_PLATFORM_LABELS.get(value, value.title()),
            )
            current_platforms = _set_story_platforms(story_key, chosen_platforms)
            label_text = " • ".join(WORKSPACE_PLATFORM_LABELS.get(platform, platform.title()) for platform in current_platforms)
            st.caption("Current output cards: " + (label_text or "No platforms selected yet"))

            action_row = st.columns(4)
            with action_row[0]:
                if st.button("Use Recommended", key=_widget_key("selected_recommended", story_key), use_container_width=True):
                    values = _default_story_platforms(item)
                    st.session_state[widget_key] = values
                    _set_story_platforms(story_key, values)
                    st.rerun()
            with action_row[1]:
                if st.button("Use All Platforms", key=_widget_key("selected_all", story_key), use_container_width=True):
                    values = list(WORKSPACE_PLATFORMS)
                    st.session_state[widget_key] = values
                    _set_story_platforms(story_key, values)
                    st.rerun()
            with action_row[2]:
                if st.button("Open Outputs", key=_widget_key("selected_outputs", story_key), use_container_width=True):
                    st.session_state["dashboard_active_story_key"] = story_key
                    _set_navigation("Platform Outputs")
            with action_row[3]:
                if st.button("Remove Story", key=_widget_key("selected_remove", story_key), use_container_width=True):
                    _deselect_story(story_key)
                    st.rerun()


def _render_instagram_output(item: dict, output: dict):
    render_notice("Instagram workspace", output.get("message", ""), "ok" if output.get("mode") == "agent_ready" else "muted")
    story = _safe_dict(item.get("story", {}))

    cols = st.columns(2, gap="large")
    with cols[0]:
        with card_container(accent="morning", soft=True):
            st.markdown("**Image Text**")
            st.markdown(f"**Hook**  \n{output.get('image_text', {}).get('hook', 'N/A')}")
            st.markdown(f"**Line 1**  \n{output.get('image_text', {}).get('line_1', 'N/A')}")
            st.markdown(f"**Line 2**  \n{output.get('image_text', {}).get('line_2', 'N/A')}")
            actions = st.columns(2)
            with actions[0]:
                _copy_button(
                    "Copy Image Text",
                    output.get("image_text", {}).get("text", ""),
                    _widget_key("ig_image_copy", item.get("key", "")),
                    slot_key=_widget_key("ig_image_slot", item.get("key", "")),
                )
            with actions[1]:
                render_link_action(story.get("link", ""), "Open Source", _widget_key("ig_image_open", item.get("key", "")))
            render_copy_buffer(_widget_key("ig_image_slot", item.get("key", "")))

    with cols[1]:
        with card_container(accent="afternoon", soft=True):
            st.markdown("**Caption**")
            st.code(output.get("caption", {}).get("text", ""), language="text")
            actions = st.columns(3)
            with actions[0]:
                _copy_button(
                    "Copy Caption",
                    output.get("caption", {}).get("text", ""),
                    _widget_key("ig_caption_copy", item.get("key", "")),
                    slot_key=_widget_key("ig_caption_slot", item.get("key", "")),
                )
            with actions[1]:
                _copy_button(
                    "Copy Full Output",
                    output.get("copy_text", ""),
                    _widget_key("ig_full_copy", item.get("key", "")),
                    slot_key=_widget_key("ig_caption_slot", item.get("key", "")),
                )
            with actions[2]:
                render_link_action(story.get("link", ""), "Open Source", _widget_key("ig_caption_open", item.get("key", "")))
            render_copy_buffer(_widget_key("ig_caption_slot", item.get("key", "")))

            hashtags = _safe_list(output.get("hashtags", []))
            if hashtags:
                st.caption("Hashtags")
                st.write(" ".join(hashtags))
                _copy_button(
                    "Copy Hashtags",
                    " ".join(hashtags),
                    _widget_key("ig_hashtags_copy", item.get("key", "")),
                    slot_key=_widget_key("ig_hashtags_slot", item.get("key", "")),
                )
                render_copy_buffer(_widget_key("ig_hashtags_slot", item.get("key", "")))


def _render_text_output(output: dict, title: str, copy_label: str, item: dict, text_key: str = "text"):
    story = _safe_dict(item.get("story", {}))
    render_notice(title, output.get("message", ""), "info" if output.get("mode", "").startswith("planner") else "muted")
    with card_container(soft=True):
        st.code(output.get(text_key, ""), language="text")
        actions = st.columns(3)
        with actions[0]:
            _copy_button(
                copy_label,
                output.get(text_key, ""),
                _widget_key(f"{output.get('platform', title)}_copy", item.get("key", "")),
                slot_key=_widget_key(f"{output.get('platform', title)}_slot", item.get("key", "")),
            )
        with actions[1]:
            _copy_button(
                "Copy Link",
                story.get("link", ""),
                _widget_key(f"{output.get('platform', title)}_link_copy", item.get("key", "")),
                slot_key=_widget_key(f"{output.get('platform', title)}_slot", item.get("key", "")),
            )
        with actions[2]:
            render_link_action(story.get("link", ""), "Open Source", _widget_key(f"{output.get('platform', title)}_open", item.get("key", "")))
        render_copy_buffer(_widget_key(f"{output.get('platform', title)}_slot", item.get("key", "")))


def _render_youtube_output(item: dict, output: dict):
    story = _safe_dict(item.get("story", {}))
    render_notice("YouTube workspace", output.get("message", ""), "ok" if output.get("voice_script") else "muted")
    main_cols = st.columns([1, 1], gap="large")
    with main_cols[0]:
        with card_container(soft=True):
            st.markdown("**Working Title**")
            st.write(output.get("title", ""))
            st.markdown("**Hook**")
            st.write(output.get("hook", ""))
            st.markdown("**Description / Outline**")
            st.code(output.get("description", ""), language="text")
            actions = st.columns(3)
            with actions[0]:
                _copy_button(
                    "Copy Title",
                    output.get("title", ""),
                    _widget_key("yt_title_copy", item.get("key", "")),
                    slot_key=_widget_key("yt_title_slot", item.get("key", "")),
                )
            with actions[1]:
                _copy_button(
                    "Copy Description",
                    output.get("description", ""),
                    _widget_key("yt_desc_copy", item.get("key", "")),
                    slot_key=_widget_key("yt_title_slot", item.get("key", "")),
                )
            with actions[2]:
                render_link_action(story.get("link", ""), "Open Source", _widget_key("yt_open", item.get("key", "")))
            render_copy_buffer(_widget_key("yt_title_slot", item.get("key", "")))
    with main_cols[1]:
        render_prompt_block(
            "Voice Script",
            output.get("voice_script", ""),
            "No voice script is available for this story in the latest run. The rest of the YouTube draft still works.",
        )
        _copy_button(
            "Copy Voice Script",
            output.get("voice_script", ""),
            _widget_key("yt_voice_copy", item.get("key", "")),
            slot_key=_widget_key("yt_voice_slot", item.get("key", "")),
        )
        render_copy_buffer(_widget_key("yt_voice_slot", item.get("key", "")))


def _render_reddit_output(item: dict, output: dict):
    story = _safe_dict(item.get("story", {}))
    render_notice("Reddit workspace", output.get("message", ""), "info" if output.get("mode") == "planner_candidate" else "muted")
    with card_container(soft=True):
        st.markdown("**Title**")
        st.write(output.get("title", ""))
        st.markdown("**Body**")
        st.code(output.get("body", ""), language="text")
        actions = st.columns(3)
        with actions[0]:
            _copy_button(
                "Copy Reddit Title",
                output.get("title", ""),
                _widget_key("reddit_title_copy", item.get("key", "")),
                slot_key=_widget_key("reddit_slot", item.get("key", "")),
            )
        with actions[1]:
            _copy_button(
                "Copy Reddit Body",
                output.get("body", ""),
                _widget_key("reddit_body_copy", item.get("key", "")),
                slot_key=_widget_key("reddit_slot", item.get("key", "")),
            )
        with actions[2]:
            render_link_action(story.get("link", ""), "Open Source", _widget_key("reddit_open", item.get("key", "")))
        render_copy_buffer(_widget_key("reddit_slot", item.get("key", "")))


def _render_email_output(item: dict, output: dict):
    story = _safe_dict(item.get("story", {}))
    render_notice("Email workspace", output.get("message", ""), "muted")
    with card_container(soft=True):
        st.markdown("**Subject**")
        st.write(output.get("subject", ""))
        st.markdown("**Email-ready block**")
        st.code(output.get("body", ""), language="text")
        actions = st.columns(3)
        with actions[0]:
            _copy_button(
                "Copy Subject",
                output.get("subject", ""),
                _widget_key("email_subject_copy", item.get("key", "")),
                slot_key=_widget_key("email_slot", item.get("key", "")),
            )
        with actions[1]:
            _copy_button(
                "Copy Email Block",
                output.get("body", ""),
                _widget_key("email_body_copy", item.get("key", "")),
                slot_key=_widget_key("email_slot", item.get("key", "")),
            )
        with actions[2]:
            render_link_action(story.get("link", ""), "Open Source", _widget_key("email_open", item.get("key", "")))
        render_copy_buffer(_widget_key("email_slot", item.get("key", "")))


def _render_story_platform_output(item: dict, platform: str):
    outputs = _safe_dict(item.get("platform_outputs", {}))
    output = _safe_dict(outputs.get(platform, {}))
    if not output:
        render_empty_state("Output unavailable", "This platform does not have a workspace draft for the selected story.")
        return

    if platform == "instagram":
        _render_instagram_output(item, output)
    elif platform == "x":
        _render_text_output(output, "X workspace", "Copy X Draft", item)
    elif platform == "youtube":
        _render_youtube_output(item, output)
    elif platform == "reddit":
        _render_reddit_output(item, output)
    elif platform == "discord":
        _render_text_output(output, "Discord workspace", "Copy Discord Draft", item)
    elif platform == "email":
        _render_email_output(item, output)
    else:
        render_empty_state("Unsupported platform", "This workspace platform is not configured in the current dashboard build.")


def _render_platform_outputs(context: dict):
    items = _selected_story_items(context)
    active_key = st.session_state.get("dashboard_active_story_key", "")

    render_page_header(
        "Platform Outputs",
        "Open each selected story and work platform by platform, with source links and copy-ready blocks always nearby.",
    )
    _render_freshness_notice(context)
    render_notice(
        "Publishing workspace",
        "The output cards below are designed for fast manual publishing. When agent data is missing, the dashboard stays usable with clear story-based fallback drafts.",
        "muted",
    )

    if not items:
        render_empty_state(
            "No stories selected",
            "Select stories in News Feed first, then choose the platforms you want to publish for each one.",
        )
        return

    toolbar = st.columns([1.2, 1.1, 1.0, 0.9, 0.9])
    platform_filter = toolbar[0].multiselect(
        "Show platforms",
        list(WORKSPACE_PLATFORMS),
        default=list(WORKSPACE_PLATFORMS),
        format_func=lambda value: WORKSPACE_PLATFORM_LABELS.get(value, value.title()),
    )
    story_options = ["All selected stories"] + [item.get("story", {}).get("title", "Sem título") for item in items]
    focused_story = toolbar[1].selectbox("Focus", story_options, index=0)
    with toolbar[2]:
        _copy_button(
            "Copy All Selected Links",
            _collect_story_links(items),
            "outputs_copy_all_links",
            slot_key="outputs_copy_all_links_slot",
        )
    with toolbar[3]:
        if st.button("Back to Selected News", use_container_width=True):
            _set_navigation("Selected News")
    with toolbar[4]:
        if st.button("Clear Selection", use_container_width=True):
            _clear_story_selection()
            st.rerun()
    render_copy_buffer("outputs_copy_all_links_slot")

    for idx, item in enumerate(items):
        story = _safe_dict(item.get("story", {}))
        if focused_story != "All selected stories" and story.get("title", "Sem título") != focused_story:
            continue

        selected_platforms = [
            platform for platform in _get_story_platforms(item)
            if platform in (platform_filter or list(WORKSPACE_PLATFORMS))
        ]
        expanded = item.get("key") == active_key or (not active_key and idx == 0)
        with st.expander(story.get("title", "Sem título"), expanded=expanded):
            with card_container(accent="success"):
                _render_story_summary(story, selected=True)
                _render_story_context(item)
                _render_source_actions(story, _widget_key("outputs_story", item.get("key", "")))

                action_row = st.columns(3)
                with action_row[0]:
                    if st.button("Edit Platforms", key=_widget_key("outputs_edit", item.get("key", "")), use_container_width=True):
                        _set_navigation("Selected News")
                with action_row[1]:
                    if st.button("Back to Feed", key=_widget_key("outputs_feed", item.get("key", "")), use_container_width=True):
                        _set_navigation("News Feed")
                with action_row[2]:
                    if st.button("Remove Story", key=_widget_key("outputs_remove", item.get("key", "")), use_container_width=True):
                        _deselect_story(item.get("key", ""))
                        st.rerun()

            if not selected_platforms:
                render_empty_state(
                    "No platforms selected for this story",
                    "Choose one or more platforms in Selected News to populate this workspace.",
                )
                continue

            tabs = st.tabs([WORKSPACE_PLATFORM_LABELS.get(platform, platform.title()) for platform in selected_platforms])
            for tab, platform in zip(tabs, selected_platforms):
                with tab:
                    _render_story_platform_output(item, platform)


def _render_digest_snapshot(context: dict):
    plan = _safe_dict((context.get("snapshot", {}) or {}).get("plan", {}))
    if not plan:
        render_empty_state("No structured plan available", "Run the normal pipeline first so the dashboard can load digest state and variants.")
        return

    instagram = _safe_dict(context.get("instagram", {}))
    cards = _safe_dict(context.get("cards", {}))
    card_lookup = {
        card.get("key", ""): card.get("path", "")
        for card in _safe_list(cards.get("cards", []))
        if card.get("key")
    }
    tabs = st.tabs(["Morning Digest", "Afternoon Digest"])
    specs = [
        ("instagram_morning_digest", "Morning Digest", "morning", tabs[0]),
        ("instagram_afternoon_digest", "Afternoon Digest", "afternoon", tabs[1]),
    ]

    for field, label, accent, tab in specs:
        with tab:
            variant = int(_safe_dict(instagram.get("active_variants", {})).get(field, 0))
            stories = _safe_list(resolve_preview_selection(plan, field, variant))
            output_key = f"{field.replace('_digest', '')}_output"
            output = _safe_dict(plan.get(output_key, {}))
            if field == "instagram_morning_digest":
                pack = _safe_dict(plan.get("instagram_morning_pack", {}))
                card_path = card_lookup.get("morning_digest", "")
            else:
                pack = _safe_dict(plan.get("instagram_afternoon_pack", {}))
                card_path = card_lookup.get("afternoon_digest", "")

            with card_container(accent=accent):
                summary = st.columns(4)
                summary[0].metric("Stories", len(stories))
                summary[1].metric("Active variant", variant)
                summary[2].metric("Pack ready", "Yes" if pack else "Fallback")
                summary[3].metric("Card", "Yes" if card_path and Path(card_path).exists() else "No")
                if pack.get("cover_hook"):
                    st.markdown(f"**Cover Hook**  \n{pack.get('cover_hook', '')}")
                if pack.get("community_question"):
                    st.caption(f"Community question: {pack.get('community_question', '')}")
                if stories:
                    for idx, story in enumerate(stories[:7], 1):
                        st.markdown(f"**{idx}. {story.get('title', 'Sem título')}**")
                        st.caption(story.get("source", "Fonte desconhecida"))
                        render_link_action(story.get("link", ""), "Open Source", _widget_key(f"digest_{field}_{idx}", story.get("link", "")))
                else:
                    render_empty_state("No stories in this digest", "This active digest variant does not currently expose stories in the snapshot.")

                if output.get("image_prompt"):
                    with st.expander("Image prompt", expanded=False):
                        st.code(output.get("image_prompt", ""), language="text")
                if output.get("voice_script"):
                    with st.expander("Voice script", expanded=False):
                        st.code(output.get("voice_script", ""), language="text")


def _render_override_controls(context: dict):
    snapshot = context.get("snapshot", {}) or {}
    plan = _safe_dict(snapshot.get("plan", {}))
    current_saved = load_current_overrides()

    render_notice(
        "Persistence model",
        "Only integer override selections are persisted here. Story-by-story dashboard selection stays session-only and does not rewrite the pipeline state.",
        "warn",
    )

    actions = st.columns(3)
    with actions[0]:
        if st.button("Save Overrides", key="advanced_save_overrides", use_container_width=True, type="primary"):
            _save_overrides_feedback()
    with actions[1]:
        if st.button("Reset Overrides", key="advanced_reset_overrides", use_container_width=True):
            ok, message = reset_current_overrides()
            if ok:
                st.session_state["dashboard_override_draft"] = {field: 0 for field in SUPPORTED_OVERRIDE_FIELDS}
                st.success(f"Overrides limpos em {message}")
            else:
                st.error(message)
    with actions[2]:
        if st.button("Open Overrides File", key="advanced_open_overrides_from_overrides_tab", use_container_width=True):
            _open_path_feedback(ensure_overrides_file())

    if not plan:
        render_empty_state("Plan not available", "Override preview is limited until a normal run persists a structured plan into the latest snapshot.")
        return

    main_cols = st.columns([1, 1], gap="large")
    with main_cols[0]:
        with card_container():
            render_section_header("Variant controls", "Change saved morning/afternoon/channel variants without editing raw JSON.", level=3)
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
                    key=_widget_key("override_selector", field),
                )
                st.session_state["dashboard_override_draft"][field] = chosen

    with main_cols[1]:
        with card_container():
            render_section_header("Resolved summary", "Preview the effective selection before you persist anything.", level=3)
            summary_text = build_selection_summary(context, st.session_state.get("dashboard_override_draft", {}))
            st.code(summary_text, language="text")

    with st.expander("Current saved JSON", expanded=False):
        st.code(json.dumps(current_saved, indent=2, ensure_ascii=False), language="json")


def _render_brief_and_files(context: dict):
    brief = _safe_dict(context.get("brief", {}))
    paths = _safe_dict(context.get("paths", {}))
    export_text = build_selection_summary(context, st.session_state.get("dashboard_override_draft", {}))

    actions = st.columns(4)
    with actions[0]:
        if st.button("Open Brief File", key="advanced_open_brief_file", use_container_width=True):
            _open_path_feedback(brief.get("path", ""))
    with actions[1]:
        if st.button("Open Brief Folder", key="advanced_open_brief_folder", use_container_width=True):
            _open_path_feedback(brief.get("folder", ""))
    with actions[2]:
        if st.button("Open Cards Folder", key="advanced_open_cards_folder", use_container_width=True):
            _open_path_feedback(paths.get("cards_folder", ""))
    with actions[3]:
        if st.button("Open Overrides File", key="advanced_open_overrides_from_files_tab", use_container_width=True):
            _open_path_feedback(ensure_overrides_file())

    st.download_button(
        "Export selection summary",
        data=export_text,
        file_name="simula_selection_summary.txt",
        mime="text/plain",
        use_container_width=True,
    )

    with card_container():
        render_path_block("Brief path", brief.get("path", ""))
        render_path_block("Brief folder", brief.get("folder", ""))
        render_path_block("Cards folder", paths.get("cards_folder", ""))
        render_path_block("Overrides file", paths.get("overrides", ""))

    if brief.get("exists"):
        with st.expander("Latest brief preview", expanded=False):
            st.markdown(brief.get("content", ""))
    else:
        render_empty_state("Brief not available", "The latest brief file does not exist yet for this environment or run state.")


def _render_system_status(context: dict):
    runtime = _safe_dict(context.get("runtime", {}))
    freshness = _safe_dict(context.get("freshness", {}))
    agent_runtime = _safe_dict(context.get("agent_runtime", {}))
    paths = _safe_dict(runtime.get("paths", {}))

    metrics = st.columns(4)
    metrics[0].metric("MiniMax", "Configured" if runtime.get("minimax_configured") else "Missing")
    metrics[1].metric("Email", "Ready" if runtime.get("email_ready") else "Off / incomplete")
    metrics[2].metric("Cards", "Ready" if runtime.get("cards_exist") else "Missing")
    metrics[3].metric("Snapshot", freshness.get("label", "Missing"))

    with card_container():
        render_section_header("Runtime signals", "Operational state that still matters, without crowding the main workspace.", level=3)
        render_status_pill("Snapshot ready" if runtime.get("snapshot_exists") else "No snapshot", "ok" if runtime.get("snapshot_exists") else "warn")
        render_status_pill("Cards enabled" if runtime.get("card_generation_enabled") else "Cards disabled", "ok" if runtime.get("card_generation_enabled") else "muted")
        render_status_pill("Email enabled" if runtime.get("email_enabled") else "Email disabled", "ok" if runtime.get("email_enabled") else "muted")
        render_status_pill("Assets ready" if runtime.get("assets_ready") else "Assets missing", "ok" if runtime.get("assets_ready") else "warn")
        st.caption(f"Data source: {freshness.get('source', 'missing')}")

    with card_container():
        render_section_header("Agent runtime", "Small operational summary for the latest persisted agent activity.", level=3)
        cols = st.columns(5)
        cols[0].metric("Pipelines", agent_runtime.get("pipelines", 0))
        cols[1].metric("Useful outputs", agent_runtime.get("useful_outputs", 0))
        cols[2].metric("Calls attempted", agent_runtime.get("calls_attempted", 0))
        cols[3].metric("Timed out", agent_runtime.get("calls_timed_out", 0))
        cols[4].metric("Duration", f"{agent_runtime.get('total_duration_sec', 0.0)}s")

    with card_container():
        render_section_header("Paths", "Useful operational paths kept in one quiet place.", level=3)
        for label, path in paths.items():
            render_path_block(label.replace("_", " ").title(), path)


def _render_advanced_system(context: dict):
    render_page_header(
        "Advanced / System",
        "The main workflow now lives in stories and platform outputs. This area keeps digest controls, files, overrides, and runtime state available without taking over the dashboard.",
    )
    _render_freshness_notice(context)

    tabs = st.tabs(["Digests", "Overrides", "Brief & Files", "Status"])
    with tabs[0]:
        _render_digest_snapshot(context)
    with tabs[1]:
        _render_override_controls(context)
    with tabs[2]:
        _render_brief_and_files(context)
    with tabs[3]:
        _render_system_status(context)


def _render_sidebar(context: dict):
    run_summary = _safe_dict(context.get("run_summary", {}))
    status = _safe_dict(context.get("status", {}))
    freshness = _safe_dict(context.get("freshness", {}))
    runtime = _safe_dict(context.get("runtime", {}))
    selected_count = len(_selected_story_keys(context))

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

    st.sidebar.title("Simula Workspace")
    st.sidebar.caption("News-first publishing control center")
    _sidebar_pill(
        f"Run {run_summary.get('status', status.get('run_status', 'UNKNOWN'))}",
        "ok" if run_summary.get("status", status.get("run_status", "UNKNOWN")) == "OK" else "warn",
    )
    _sidebar_pill(
        f"{freshness.get('label', 'Missing')} data",
        freshness.get("tone", "muted"),
    )
    _sidebar_pill(f"{selected_count} selected", "info" if selected_count else "muted")
    if status.get("timestamp"):
        st.sidebar.caption(status.get("timestamp"))

    metrics = st.sidebar.columns(2)
    metrics[0].metric("Stories", status.get("workspace_stories", len(_workspace_items(context))))
    metrics[1].metric("Planned", len(_safe_list(context.get("selection_seed", []))))

    st.sidebar.radio("Navigate", NAV_ITEMS, key="dashboard_nav")

    st.sidebar.markdown("---")
    st.sidebar.caption("Quick actions")
    if st.sidebar.button("Use planned stories", use_container_width=True, type="primary"):
        if _seed_planned_selection(context):
            st.rerun()
        st.sidebar.warning("No planned stories available in the latest snapshot.")
    if st.sidebar.button("Clear session selection", use_container_width=True):
        _clear_story_selection()
        st.rerun()
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
    _sidebar_pill("Email ready" if runtime.get("email_ready") else "Email partial", "ok" if runtime.get("email_ready") else "muted")
    _sidebar_pill("Cards ready" if runtime.get("cards_exist") else "No cards", "ok" if runtime.get("cards_exist") else "muted")
    _sidebar_pill("Snapshot ready" if runtime.get("snapshot_exists") else "No snapshot", "ok" if runtime.get("snapshot_exists") else "warn")


def main():
    st.set_page_config(
        page_title="Simula Workspace",
        page_icon="📰",
        layout="wide",
    )
    inject_custom_css()

    context = load_dashboard_context()
    _init_state(context)
    _render_sidebar(context)

    nav = st.session_state.get("dashboard_nav", "News Feed")
    if nav == "News Feed":
        _render_news_feed(context)
    elif nav == "Selected News":
        _render_selected_news(context)
    elif nav == "Platform Outputs":
        _render_platform_outputs(context)
    elif nav == "Advanced / System":
        _render_advanced_system(context)


if __name__ == "__main__":
    main()
