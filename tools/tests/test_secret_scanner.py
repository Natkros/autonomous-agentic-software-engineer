"""Every 'secret' below is a fake, invalid example matching the expected
SHAPE of a real credential (per each provider's public documentation) —
none of these are live or ever were.

Each fake is assembled via string concatenation rather than written as
one contiguous literal, specifically so the SOURCE FILE never contains
the matching substring verbatim — GitHub's own push-protection secret
scanner (rightly) does not know these are test fixtures and will block a
push that contains one written out directly, exactly like the tool under
test here is designed to catch. Concatenating still produces the real
runtime string `scan_text_for_secrets` receives, so the tests are
unaffected.
"""
from tools.security.secret_scanner import scan_text_for_secrets


def _rule_ids(findings):
    return {f.rule_id for f in findings}


_FAKE_AWS_KEY = "AKIA" + "ABCDEFGHIJKLMNOP"
_FAKE_SLACK_TOKEN = "xoxb-" + "1234567890" + "-abcdefghijklmnop"
_FAKE_GITHUB_TOKEN = "ghp_" + "a" * 36


def test_detects_aws_access_key_id():
    findings = scan_text_for_secrets(f"AWS_KEY = '{_FAKE_AWS_KEY}'", "config.py")
    assert "aws-access-key-id" in _rule_ids(findings)


def test_detects_private_key_header():
    content = "-----BEGIN RSA PRIVATE KEY-----\nMIIExampleFakeKeyMaterial\n-----END RSA PRIVATE KEY-----\n"
    findings = scan_text_for_secrets(content, "id_rsa")
    assert "generic-private-key" in _rule_ids(findings)


def test_detects_slack_token():
    findings = scan_text_for_secrets(f"SLACK_TOKEN={_FAKE_SLACK_TOKEN}", ".env")
    assert "slack-token" in _rule_ids(findings)


def test_detects_github_token():
    findings = scan_text_for_secrets(f"token: {_FAKE_GITHUB_TOKEN}", "config.yaml")
    assert "github-token" in _rule_ids(findings)


def test_detects_generic_secret_assignment():
    findings = scan_text_for_secrets('password = "SuperSecret' + 'Passw0rd!"', "settings.py")
    assert "generic-secret-assignment" in _rule_ids(findings)


def test_does_not_flag_clean_text():
    findings = scan_text_for_secrets("def greet(name):\n    return f'hello {name}'\n", "app.py")
    assert findings == []


def test_reports_correct_line_number():
    content = f"line one\nline two\nAWS_KEY = '{_FAKE_AWS_KEY}'\n"
    findings = scan_text_for_secrets(content, "config.py")
    assert findings[0].line == 3


def test_all_secret_findings_are_blocker_severity():
    findings = scan_text_for_secrets(f"AWS_KEY = '{_FAKE_AWS_KEY}'", "config.py")
    assert all(f.severity.value == "blocker" for f in findings)
