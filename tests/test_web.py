import subprocess


def test_web_answer_isolation():
    run = subprocess.run(["node", "--test", "tests/test_web_answer_isolation.js"], capture_output=True, text=True, timeout=15)
    assert run.returncode == 0, run.stdout + run.stderr
