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
             mock.patch.object(launch_dashboard, "is_port_in_use", return_value=False), \
             mock.patch.object(launch_dashboard, "start_streamlit_dashboard", side_effect=lambda **kwargs: events.append("start") or fake_process), \
             mock.patch.object(launch_dashboard, "wait_for_dashboard", side_effect=lambda *args, **kwargs: events.append("wait") or True), \
             mock.patch.object(launch_dashboard.webbrowser, "open", side_effect=lambda url: events.append("browser") or True):
            result = launch_dashboard.open_browser_when_ready(open_browser_flag=True)

        self.assertEqual(result, 0)
        self.assertEqual(events, ["start", "wait", "browser"])

    def test_already_ready_dashboard_does_not_restart_streamlit(self):
        with mock.patch.object(launch_dashboard, "is_dashboard_ready", return_value=True), \
             mock.patch.object(launch_dashboard, "start_streamlit_dashboard") as starter, \
             mock.patch.object(launch_dashboard.webbrowser, "open", return_value=True):
            result = launch_dashboard.open_browser_when_ready(open_browser_flag=True)

        self.assertEqual(result, 0)
        starter.assert_not_called()

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
