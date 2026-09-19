from tools.security.static_analysis import analyze_python_source


def _rule_ids(findings):
    return {f.rule_id for f in findings}


def test_detects_eval_and_exec():
    findings = analyze_python_source("eval(user_input)\nexec(other_input)\n", "a.py")
    assert "dangerous-eval-exec" in _rule_ids(findings)
    assert sum(1 for f in findings if f.rule_id == "dangerous-eval-exec") == 2


def test_detects_shell_true():
    source = "import subprocess\nsubprocess.run(cmd, shell=True)\n"
    findings = analyze_python_source(source, "a.py")
    assert "shell-true-command-injection" in _rule_ids(findings)


def test_does_not_flag_subprocess_without_shell_true():
    source = "import subprocess\nsubprocess.run(['ls', '-la'])\n"
    findings = analyze_python_source(source, "a.py")
    assert "shell-true-command-injection" not in _rule_ids(findings)


def test_detects_bare_except():
    source = "try:\n    do_thing()\nexcept:\n    pass\n"
    findings = analyze_python_source(source, "a.py")
    assert "bare-except" in _rule_ids(findings)


def test_does_not_flag_specific_except():
    source = "try:\n    do_thing()\nexcept ValueError:\n    pass\n"
    findings = analyze_python_source(source, "a.py")
    assert "bare-except" not in _rule_ids(findings)


def test_detects_pickle_loads():
    source = "import pickle\ndata = pickle.loads(raw_bytes)\n"
    findings = analyze_python_source(source, "a.py")
    assert "insecure-deserialization" in _rule_ids(findings)


def test_detects_unsafe_yaml_load():
    source = "import yaml\ndata = yaml.load(raw)\n"
    findings = analyze_python_source(source, "a.py")
    assert "insecure-yaml-load" in _rule_ids(findings)


def test_does_not_flag_yaml_safe_load_with_explicit_loader():
    source = "import yaml\ndata = yaml.load(raw, Loader=yaml.SafeLoader)\n"
    findings = analyze_python_source(source, "a.py")
    assert "insecure-yaml-load" not in _rule_ids(findings)


def test_detects_sql_injection_via_fstring():
    source = 'name = input()\ncursor.execute(f"SELECT * FROM users WHERE name = \'{name}\'")\n'
    findings = analyze_python_source(source, "a.py")
    assert "possible-sql-injection" in _rule_ids(findings)


def test_does_not_flag_parameterized_query():
    source = 'cursor.execute("SELECT * FROM users WHERE name = %s", (name,))\n'
    findings = analyze_python_source(source, "a.py")
    assert "possible-sql-injection" not in _rule_ids(findings)


def test_detects_hardcoded_secret_assignment():
    # Built via concatenation (not a contiguous literal) so this file's own
    # source never contains a real-looking secret verbatim for a scanner
    # like GitHub's push protection to (rightly) flag.
    source = 'api_key = "sk_live_' + 'abcdef1234567890"\n'
    findings = analyze_python_source(source, "a.py")
    assert "hardcoded-secret" in _rule_ids(findings)


def test_does_not_flag_short_or_unrelated_assignments():
    source = 'name = "bob"\ncount = 5\n'
    findings = analyze_python_source(source, "a.py")
    assert findings == []


def test_clean_code_produces_no_findings():
    source = (
        "def add(a: int, b: int) -> int:\n"
        "    return a + b\n\n"
        "try:\n"
        "    add(1, 2)\n"
        "except TypeError:\n"
        "    pass\n"
    )
    assert analyze_python_source(source, "clean.py") == []


def test_returns_empty_list_for_unparseable_source():
    assert analyze_python_source("def broken(:\n", "broken.py") == []


def test_findings_carry_the_file_path_and_line_number():
    findings = analyze_python_source("\n\neval(x)\n", "app/dangerous.py")
    assert findings[0].file == "app/dangerous.py"
    assert findings[0].line == 3
