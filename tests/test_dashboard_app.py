import json
import unittest

import dashboard_app
from streamlit.testing.v1 import AppTest


def make_story(
    title="Story One",
    link="https://example.com/story",
    *,
    source="Source",
    category="sim_racing",
    score=88,
):
    return {
        "title": title,
        "source": source,
        "category": category,
        "summary": f"Summary for {title}",
        "score": score,
        "link": link,
    }


def make_workspace_item(
    title="Story One",
    link="https://example.com/story",
    *,
    source="Source",
    category="sim_racing",
    score=88,
    planner_tags=None,
    recommended_platforms=None,
    in_active_plan=True,
    selected_by_system=False,
    in_current_digest=False,
):
    story = make_story(title=title, link=link, source=source, category=category, score=score)
    return {
        "key": link,
        "story": story,
        "planner_tags": planner_tags if planner_tags is not None else ["Morning Digest", "X Thread 1"],
        "recommended_platforms": recommended_platforms if recommended_platforms is not None else ["instagram", "x", "email"],
        "available_platforms": ["instagram", "x", "youtube", "reddit", "discord", "email"],
        "platform_outputs": {
            "instagram": {
                "platform": "instagram",
                "label": "Instagram",
                "mode": "fallback_story_draft",
                "message": "Built from story metadata.",
                "source_link": link,
                "image_text": {
                    "hook": "Hook",
                    "line_1": "Line 1",
                    "line_2": "Line 2",
                    "text": "Hook\nLine 1\nLine 2",
                },
                "caption": {
                    "title": title,
                    "lines": ["Caption line 1", "Caption line 2"],
                    "text": f"{title}\nCaption line 1\nCaption line 2\n{link}",
                },
                "hashtags": [],
                "copy_text": f"IMAGE TEXT\nHook\nLine 1\nLine 2\n\nCAPTION\n{title}\nCaption line 1\nCaption line 2\n{link}",
            },
            "x": {
                "platform": "x",
                "label": "X",
                "mode": "manual_story_draft",
                "message": "Manual X draft.",
                "source_link": link,
                "text": f"X draft for {title}\n{link}",
            },
            "email": {
                "platform": "email",
                "label": "Email",
                "mode": "story_ready",
                "message": "Email-ready block.",
                "source_link": link,
                "subject": title,
                "body": f"Email body for {title}\n{link}",
            },
        },
        "agent_output": {},
        "in_active_plan": in_active_plan,
        "selected_by_system": selected_by_system,
        "in_current_digest": in_current_digest,
    }


def make_context(story_workspace=None, selection_seed=None, freshness_label="Fresh", freshness_source="structured_snapshot"):
    return {
        "story_workspace": story_workspace if story_workspace is not None else [make_workspace_item()],
        "selection_seed": selection_seed if selection_seed is not None else ["https://example.com/story"],
        "status": {
            "workspace_stories": len(story_workspace if story_workspace is not None else [make_workspace_item()]),
            "timestamp": "2026-03-27T10:00:00+00:00",
            "run_status": "OK",
        },
        "freshness": {
            "label": freshness_label,
            "tone": "ok" if freshness_label == "Fresh" else "warn",
            "source": freshness_source,
            "message": "Dashboard data status.",
            "age_hours": 1 if freshness_label == "Fresh" else 36,
        },
        "brief": {"path": "", "folder": "", "exists": False, "content": ""},
        "runtime": {
            "cards_exist": False,
            "snapshot_exists": freshness_source == "structured_snapshot",
            "minimax_configured": False,
            "email_ready": False,
            "card_generation_enabled": False,
            "email_enabled": False,
            "assets_ready": False,
            "paths": {"brief_folder": "", "cards_folder": "", "overrides": ""},
        },
        "run_summary": {"status": "OK"},
        "snapshot": {"plan": {}, "run_status": "OK"},
        "instagram": {"active_variants": {}},
        "cards": {"cards": []},
        "paths": {"brief_folder": "", "cards_folder": "", "overrides": ""},
        "agent_runtime": {},
        "agents_useful": False,
    }


class DashboardAppTests(unittest.TestCase):
    def _build_script(self, context: dict) -> str:
        payload = json.dumps(context, ensure_ascii=False)
        return f"""
from unittest import mock
import json
import dashboard_app

context = json.loads({payload!r})

with mock.patch.object(dashboard_app, "load_dashboard_context", return_value=context), \\
     mock.patch.object(dashboard_app, "load_current_overrides", return_value={{}}):
    dashboard_app.main()
"""

    def _run_app(self, context: dict, nav: str, selected=None, platforms=None) -> AppTest:
        at = AppTest.from_string(self._build_script(context), default_timeout=10)
        at.session_state["dashboard_nav"] = nav
        at.session_state["dashboard_selected_story_keys"] = selected or []
        at.session_state["dashboard_story_platforms"] = platforms or {}
        at.run()
        return at

    def _button_by_label(self, at: AppTest, label: str):
        for button in at.button:
            if getattr(button, "label", "") == label:
                return button
        self.fail(f"Button not found: {label}")

    def test_filter_sort_workspace_items_supports_search_scope_recommended_and_sorting(self):
        items = [
            make_workspace_item(
                title="GT7 Patch Notes",
                link="https://example.com/gt7",
                source="PlayStation Blog",
                score=72,
                in_active_plan=False,
                planner_tags=[],
            ),
            make_workspace_item(
                title="Endurance Update",
                link="https://example.com/endurance",
                source="PT Sim Hub",
                score=91,
                in_active_plan=True,
                selected_by_system=True,
                in_current_digest=True,
            ),
            make_workspace_item(
                title="Archive Item",
                link="https://example.com/archive",
                source="Archive Source",
                score=25,
                in_active_plan=True,
            ),
        ]

        filtered = dashboard_app._filter_sort_workspace_items(
            items,
            source_filter=["PT Sim Hub"],
            min_score=50,
            search_text="PT Sim",
            search_scope="Source only",
            recommended_only=True,
            system_only=True,
            digest_only=True,
            sort_option="Score ↓",
        )
        self.assertEqual([item["key"] for item in filtered], ["https://example.com/endurance"])

        title_filtered = dashboard_app._filter_sort_workspace_items(
            items,
            search_text="GT7",
            search_scope="Title only",
            sort_option="Title A-Z",
        )
        self.assertEqual([item["key"] for item in title_filtered], ["https://example.com/gt7"])

    def test_collect_story_links_deduplicates_and_preserves_order(self):
        items = [
            make_workspace_item(title="One", link="https://example.com/one"),
            make_workspace_item(title="Duplicate", link="https://example.com/one"),
            make_workspace_item(title="Two", link="https://example.com/two"),
        ]

        self.assertEqual(
            dashboard_app._collect_story_links(items),
            "https://example.com/one\nhttps://example.com/two",
        )

    def test_news_feed_allows_story_selection(self):
        context = make_context()

        at = self._run_app(context, nav="News Feed")
        self.assertEqual(len(at.exception), 0)

        self._button_by_label(at, "Select Story").click().run()

        self.assertIn("https://example.com/story", at.session_state["dashboard_selected_story_keys"])
        labels = [button.label for button in at.button]
        self.assertIn("Deselect", labels)

    def test_news_feed_programmatic_navigation_is_streamlit_safe(self):
        context = make_context()

        at = self._run_app(context, nav="News Feed")
        self.assertEqual(len(at.exception), 0)

        self._button_by_label(at, "Open Selected News").click().run()

        self.assertEqual(len(at.exception), 0)
        self.assertEqual(at.session_state["dashboard_nav"], "Selected News")
        self.assertNotIn("_dashboard_nav_target", at.session_state)

    def test_news_feed_select_all_visible_adds_multiple_stories(self):
        stories = [
            make_workspace_item(title="Story One", link="https://example.com/story-one", score=96),
            make_workspace_item(title="Story Two", link="https://example.com/story-two", score=84, in_active_plan=False),
            make_workspace_item(title="Story Three", link="https://example.com/story-three", score=73),
        ]
        context = make_context(story_workspace=stories, selection_seed=[])

        at = self._run_app(context, nav="News Feed", selected=[], platforms={})
        self.assertEqual(len(at.exception), 0)

        self._button_by_label(at, "Select All Visible").click().run()

        self.assertEqual(
            at.session_state["dashboard_selected_story_keys"],
            [
                "https://example.com/story-one",
                "https://example.com/story-two",
                "https://example.com/story-three",
            ],
        )

    def test_selected_news_bulk_actions_render_for_multi_story_selection(self):
        stories = [
            make_workspace_item(title="Story One", link="https://example.com/story-one"),
            make_workspace_item(title="Story Two", link="https://example.com/story-two", in_active_plan=False),
        ]
        context = make_context(story_workspace=stories, selection_seed=[])
        at = self._run_app(
            context,
            nav="Selected News",
            selected=["https://example.com/story-one", "https://example.com/story-two"],
            platforms={},
        )

        self.assertEqual(len(at.exception), 0)
        labels = [button.label for button in at.button]
        self.assertIn("Use Recommended for All", labels)
        self.assertIn("Use All Platforms for All", labels)
        self.assertIn("Copy All Selected Links", labels)

    def test_platform_outputs_render_selected_story_outputs(self):
        context = make_context()
        at = self._run_app(
            context,
            nav="Platform Outputs",
            selected=["https://example.com/story"],
            platforms={"https://example.com/story": ["instagram", "x", "email"]},
        )

        self.assertEqual(len(at.exception), 0)
        labels = [button.label for button in at.button]
        self.assertIn("Copy Caption", labels)
        self.assertIn("Copy X Draft", labels)
        self.assertIn("Copy Email Block", labels)
        self.assertIn("Copy Link", labels)

        code_values = [node.value for node in at.code]
        self.assertIn("Story One\nCaption line 1\nCaption line 2\nhttps://example.com/story", code_values)
        self.assertIn("X draft for Story One\nhttps://example.com/story", code_values)
        self.assertIn("Email body for Story One\nhttps://example.com/story", code_values)

    def test_platform_outputs_show_bulk_link_copy_action(self):
        stories = [
            make_workspace_item(title="Story One", link="https://example.com/story-one"),
            make_workspace_item(title="Story Two", link="https://example.com/story-two"),
        ]
        context = make_context(story_workspace=stories, selection_seed=[])
        at = self._run_app(
            context,
            nav="Platform Outputs",
            selected=["https://example.com/story-one", "https://example.com/story-two"],
            platforms={
                "https://example.com/story-one": ["instagram"],
                "https://example.com/story-two": ["x"],
            },
        )

        self.assertEqual(len(at.exception), 0)
        labels = [button.label for button in at.button]
        self.assertIn("Copy All Selected Links", labels)

    def test_platform_outputs_with_zero_selected_stories_do_not_crash(self):
        context = make_context()
        at = self._run_app(context, nav="Platform Outputs", selected=[], platforms={})

        self.assertEqual(len(at.exception), 0)
        markdown_values = [node.value for node in at.markdown]
        self.assertTrue(any("No stories selected" in value for value in markdown_values))

    def test_news_feed_fallback_mode_without_story_workspace_does_not_crash(self):
        context = make_context(story_workspace=[], selection_seed=[], freshness_label="Partial", freshness_source="fallback_files")
        at = self._run_app(context, nav="News Feed")

        self.assertEqual(len(at.exception), 0)
        markdown_values = [node.value for node in at.markdown]
        self.assertTrue(any("No story workspace available" in value for value in markdown_values))

    def test_advanced_system_renders_without_duplicate_widget_errors(self):
        context = make_context()
        context["brief"] = {"path": "", "folder": "", "exists": False, "content": ""}
        context["runtime"]["paths"] = {"brief_folder": "", "cards_folder": "", "overrides": ""}
        context["paths"] = {"brief_folder": "", "cards_folder": "", "overrides": ""}

        at = self._run_app(context, nav="Advanced / System")

        self.assertEqual(len(at.exception), 0)
        markdown_values = [node.value for node in at.markdown]
        self.assertTrue(any("Persistence model" in value for value in markdown_values))


if __name__ == "__main__":
    unittest.main()
