"""Tests for swarm_specialists — task classification and static-analysis auditors."""

import unittest

from app.engine.swarm_specialists import (
    classify_task,
    SecurityAuditorAgent,
    PerformanceAuditorAgent,
    CriticAgent,
)


class TestClassifyTask(unittest.TestCase):
    def test_flags_security_from_filepath(self):
        tags = classify_task({"filepath": "app/auth/login.py", "instructions": "add a new endpoint"})
        self.assertIn("security", tags)

    def test_flags_security_from_instructions(self):
        tags = classify_task({"filepath": "utils.py", "instructions": "hash the password with a stronger algorithm"})
        self.assertIn("security", tags)

    def test_flags_performance_from_instructions(self):
        tags = classify_task({"filepath": "utils.py", "instructions": "optimize the loop for better throughput"})
        self.assertIn("performance", tags)

    def test_unrelated_task_gets_no_tags(self):
        tags = classify_task({"filepath": "README.md", "instructions": "fix a typo in the docs"})
        self.assertEqual(tags, [])

    def test_can_flag_both(self):
        tags = classify_task({
            "filepath": "auth.py",
            "instructions": "optimize the login loop and cache the session token",
        })
        self.assertIn("security", tags)
        self.assertIn("performance", tags)


class TestSecurityAuditorAgent(unittest.TestCase):
    def setUp(self):
        self.auditor = SecurityAuditorAgent()

    def test_flags_eval(self):
        result = self.auditor.review("x.py", "result = eval(user_input)\n")
        self.assertEqual(result["verdict"], "revise")
        self.assertTrue(result["concerns"])

    def test_flags_shell_true(self):
        result = self.auditor.review("x.py", "subprocess.run(cmd, shell=True)\n")
        self.assertEqual(result["verdict"], "revise")

    def test_flags_sql_string_concat(self):
        result = self.auditor.review("x.py", 'query = "SELECT * FROM users WHERE id=" + user_id\n')
        self.assertEqual(result["verdict"], "revise")

    def test_flags_hardcoded_credential(self):
        result = self.auditor.review("x.py", 'api_key = "sk-abcdef1234567890"\n')
        self.assertEqual(result["verdict"], "revise")

    def test_clean_code_approves(self):
        result = self.auditor.review("x.py", "def add(a, b):\n    return a + b\n")
        self.assertEqual(result["verdict"], "approve")
        self.assertEqual(result["concerns"], [])
        self.assertEqual(result["risk_score"], 0.0)


class TestPerformanceAuditorAgent(unittest.TestCase):
    def setUp(self):
        self.auditor = PerformanceAuditorAgent()

    def test_flags_nested_loops(self):
        code = "def f(items):\n    for i in items:\n        for j in items:\n            pass\n"
        result = self.auditor.review("x.py", code)
        self.assertTrue(any("Nested loop" in c for c in result["concerns"]))
        self.assertEqual(result["verdict"], "advisory")

    def test_never_gates_even_when_concerns_found(self):
        code = "def f(items):\n    for i in items:\n        for j in items:\n            pass\n"
        result = self.auditor.review("x.py", code)
        self.assertEqual(result["verdict"], "advisory")

    def test_syntax_error_produces_no_concerns_not_a_crash(self):
        result = self.auditor.review("x.py", "def f(\n    broken")
        self.assertEqual(result["concerns"], [])

    def test_non_python_file_is_a_no_op(self):
        result = PerformanceAuditorAgent().review("README.md", "for for for" * 100)
        self.assertEqual(result["concerns"], [])


class TestCriticAgent(unittest.TestCase):
    def setUp(self):
        self.critic = CriticAgent()

    def test_flags_todo_markers(self):
        result = self.critic.review("x.py", "def f():\n    # TODO: fix this\n    pass\n")
        self.assertTrue(any("TODO" in c for c in result["concerns"]))

    def test_flags_bare_except_pass(self):
        code = "def f():\n    try:\n        risky()\n    except:\n        pass\n"
        result = self.critic.review("x.py", code)
        self.assertTrue(any("swallows" in c for c in result["concerns"]))

    def test_does_not_flag_except_with_handling(self):
        code = "def f():\n    try:\n        risky()\n    except ValueError:\n        logger.warning('oops')\n"
        result = self.critic.review("x.py", code)
        self.assertFalse(any("swallows" in c for c in result["concerns"]))

    def test_clean_code_has_no_concerns(self):
        result = self.critic.review("x.py", "def add(a, b):\n    return a + b\n")
        self.assertEqual(result["concerns"], [])


if __name__ == "__main__":
    unittest.main()
