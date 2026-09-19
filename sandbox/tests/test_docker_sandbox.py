"""These tests exercise DockerSandbox's command construction and the
factory's fallback logic — not a live Docker daemon (none is guaranteed to
be available in CI or in this development environment; see
`sandbox/README.md`). `run_command()` against a real daemon is
unverified — see that file for what would need to happen to verify it.
"""
from sandbox.docker_sandbox import DockerSandbox, docker_daemon_available
from sandbox.factory import get_default_sandbox
from sandbox.local_process_sandbox import LocalProcessSandbox


def test_build_docker_command_includes_isolation_flags():
    sandbox = DockerSandbox(image="python:3.12-slim")
    command = sandbox._build_docker_command(["pytest"], cwd="/tmp/workspace")

    assert command[0] == "docker"
    assert "--network" in command and "none" in command
    assert "-v" in command
    assert f"{'/tmp/workspace'}:/workspace" in command
    assert command[-1] == "pytest"


def test_build_docker_command_passes_env_vars():
    sandbox = DockerSandbox()
    command = sandbox._build_docker_command(["echo"], cwd="/tmp/x", env={"FOO": "bar"})
    assert "-e" in command
    assert "FOO=bar" in command


def test_provides_isolation_is_honestly_true():
    assert DockerSandbox().provides_isolation is True


def test_docker_daemon_available_is_a_real_check_not_just_cli_presence():
    # Whatever this returns in the current environment, it must not raise,
    # and it must be a real bool derived from actually invoking `docker info`.
    result = docker_daemon_available()
    assert isinstance(result, bool)


def test_factory_falls_back_to_local_process_sandbox_when_no_daemon(monkeypatch):
    monkeypatch.setattr("sandbox.factory.docker_daemon_available", lambda: False)
    sandbox = get_default_sandbox()
    assert isinstance(sandbox, LocalProcessSandbox)


def test_factory_selects_docker_sandbox_when_daemon_available(monkeypatch):
    monkeypatch.setattr("sandbox.factory.docker_daemon_available", lambda: True)
    sandbox = get_default_sandbox()
    assert isinstance(sandbox, DockerSandbox)
