import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

import launch_dashboard


class _ReadyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, format, *args):
        return


class LaunchDashboardTests(unittest.TestCase):
    def test_build_dashboard_url(self):
        self.assertEqual(
            launch_dashboard.build_dashboard_url("127.0.0.1", 8501),
            "http://127.0.0.1:8501/",
        )

    def test_build_port_candidates_uses_small_safe_range(self):
        self.assertEqual(
            launch_dashboard.build_port_candidates(8501, attempts=5),
            [8501, 8502, 8503, 8504, 8505],
        )

    def test_wait_for_dashboard_detects_ready_endpoint(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), _ReadyHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            port = server.server_address[1]
            url = launch_dashboard.build_dashboard_url("127.0.0.1", port)
            self.assertTrue(launch_dashboard.wait_for_dashboard(url, timeout_seconds=2.0, poll_interval=0.1))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2.0)

    def test_browser_opens_only_after_readiness(self):
        events = []
        fake_process = mock.Mock()
        fake_process.poll.return_value = None

        with mock.patch.object(launch_dashboard, "is_dashboard_ready", return_value=False), \
             mock.patch.object(launch_dashboard, "is_port_available", return_value=True), \
             mock.patch.object(launch_dashboard, "start_streamlit_dashboard", side_effect=lambda **kwargs: events.append("start") or fake_process), \
             mock.patch.object(launch_dashboard, "wait_for_dashboard", side_effect=lambda *args, **kwargs: events.append("wait") or True), \
             mock.patch.object(launch_dashboard.webbrowser, "open", side_effect=lambda url: events.append("browser") or True):
            result = launch_dashboard.open_browser_when_ready(open_browser_flag=True)

        self.assertEqual(result, 0)
        self.assertEqual(events, ["start", "wait", "browser"])

    def test_choose_dashboard_port_prefers_default_when_available(self):
        with mock.patch.object(launch_dashboard, "is_port_available", return_value=True):
            chosen = launch_dashboard.choose_dashboard_port(host="127.0.0.1", preferred_port=8501)

        self.assertEqual(chosen, 8501)

    def test_choose_dashboard_port_uses_fallback_when_default_is_busy(self):
        def _is_available(_host, port):
            return port == 8502

        with mock.patch.object(launch_dashboard, "is_port_available", side_effect=_is_available):
            chosen = launch_dashboard.choose_dashboard_port(host="127.0.0.1", preferred_port=8501)

        self.assertEqual(chosen, 8502)

    def test_choose_dashboard_port_returns_none_when_all_candidates_are_busy(self):
        with mock.patch.object(launch_dashboard, "is_port_available", return_value=False):
            chosen = launch_dashboard.choose_dashboard_port(host="127.0.0.1", preferred_port=8501)

        self.assertIsNone(chosen)

    def test_already_ready_dashboard_does_not_restart_streamlit(self):
        with mock.patch.object(launch_dashboard, "is_dashboard_ready", return_value=True), \
             mock.patch.object(launch_dashboard, "start_streamlit_dashboard") as starter, \
             mock.patch.object(launch_dashboard.webbrowser, "open", return_value=True):
            result = launch_dashboard.open_browser_when_ready(open_browser_flag=True)

        self.assertEqual(result, 0)
        starter.assert_not_called()

    def test_fallback_port_is_used_for_startup_readiness_and_browser(self):
        events = []
        fake_process = mock.Mock()
        fake_process.poll.return_value = None

        def _is_available(_host, port):
            return port == 8502

        with mock.patch.object(launch_dashboard, "is_dashboard_ready", return_value=False), \
             mock.patch.object(launch_dashboard, "is_port_available", side_effect=_is_available), \
             mock.patch.object(
                 launch_dashboard,
                 "start_streamlit_dashboard",
                 side_effect=lambda **kwargs: events.append(("start", kwargs["port"])) or fake_process,
             ), \
             mock.patch.object(
                 launch_dashboard,
                 "wait_for_dashboard",
                 side_effect=lambda url, **kwargs: events.append(("wait", url)) or True,
             ), \
             mock.patch.object(
                 launch_dashboard.webbrowser,
                 "open",
                 side_effect=lambda url: events.append(("browser", url)) or True,
             ):
            result = launch_dashboard.open_browser_when_ready(open_browser_flag=True)

        self.assertEqual(result, 0)
        self.assertEqual(
            events,
            [
                ("start", 8502),
                ("wait", "http://127.0.0.1:8502/"),
                ("browser", "http://127.0.0.1:8502/"),
            ],
        )

    def test_no_available_port_fails_with_readable_message(self):
        with mock.patch.object(launch_dashboard, "is_dashboard_ready", return_value=False), \
             mock.patch.object(launch_dashboard, "is_port_available", return_value=False), \
             mock.patch("builtins.print") as print_mock:
            result = launch_dashboard.open_browser_when_ready(open_browser_flag=False)

        self.assertEqual(result, 1)
        printed = " ".join(
            " ".join(str(part) for part in call.args)
            for call in print_mock.call_args_list
        )
        self.assertIn("não foi possível encontrar uma porta disponível", printed.lower())

    def test_start_streamlit_dashboard_uses_explicit_chosen_port(self):
        with mock.patch.object(launch_dashboard.subprocess, "Popen") as popen_mock:
            launch_dashboard.start_streamlit_dashboard(
                python_executable="python",
                host="127.0.0.1",
                port=8503,
            )

        command = popen_mock.call_args.args[0]
        self.assertIn("--server.port", command)
        self.assertIn("8503", command)

    def test_resolve_operational_targets_match_real_project_layout(self):
        with mock.patch.object(
            launch_dashboard,
            "ensure_overrides_file",
            return_value=launch_dashboard.PROJECT_ROOT / "data" / "manual_overrides.json",
        ):
            overrides = launch_dashboard.resolve_operational_target("overrides")

        brief_folder = launch_dashboard.resolve_operational_target("brief-folder")
        cards_folder = launch_dashboard.resolve_operational_target("cards-folder")
        project_root = launch_dashboard.resolve_operational_target("project-root")

        self.assertEqual(overrides, launch_dashboard.PROJECT_ROOT / "data" / "manual_overrides.json")
        self.assertEqual(brief_folder, Path(launch_dashboard.OUTPUT_FILE).parent)
        self.assertEqual(cards_folder, launch_dashboard.CARDS_DIR)
        self.assertEqual(project_root, launch_dashboard.PROJECT_ROOT)


if __name__ == "__main__":
    unittest.main()
