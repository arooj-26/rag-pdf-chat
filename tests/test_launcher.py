import io
import json
from unittest.mock import Mock
from scripts import start_local


class HealthResponse(io.BytesIO):
    status = 200


def test_launcher_does_not_open_old_server(monkeypatch):
    server = Mock()
    server.poll.side_effect = [None, 1]
    monkeypatch.setattr(start_local, "urlopen", lambda *a, **kw: HealthResponse(json.dumps({"instance_id": "old-run"}).encode()))
    monkeypatch.setattr(start_local.time, "sleep", lambda *a: None)
    launch = Mock()
    monkeypatch.setattr(start_local.subprocess, "Popen", launch)
    start_local.open_when_ready(server, "http://127.0.0.1:8000", "new-run")
    launch.assert_not_called()


def test_launcher_opens_its_own_ready_server(monkeypatch):
    server = Mock()
    server.poll.return_value = None
    monkeypatch.setattr(start_local, "urlopen", lambda *a, **kw: HealthResponse(json.dumps({"instance_id": "new-run"}).encode()))
    monkeypatch.setattr(start_local, "chrome_executable", lambda: "chrome.exe")
    launch = Mock()
    monkeypatch.setattr(start_local.subprocess, "Popen", launch)
    start_local.open_when_ready(server, "http://127.0.0.1:8000", "new-run")
    launch.assert_called_once_with(["chrome.exe", "--new-tab", "http://127.0.0.1:8000/login"])
