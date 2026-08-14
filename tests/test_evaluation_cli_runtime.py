import importlib
import subprocess
import sys
import unittest


MODULES_WITH_HELP = (
    "synthladder.evaluation.student_validation",
    "synthladder.evaluation.llm_judge",
    "synthladder.evaluation.run_full_matrix",
)

MODULES_IMPORTABLE = (
    "synthladder",
    "synthladder.evaluation.cli.student_validation",
    "synthladder.evaluation.cli.llm_judge",
    "synthladder.evaluation.cli.run_full_matrix",
    "synthladder.evaluation.pipeline.student_validation",
    "synthladder.evaluation.pipeline.llm_judge",
    "synthladder.evaluation.pipeline.run_full_matrix",
    "synthladder.evaluation.io.jsonl",
)

SCRIPT_HELP_COMMANDS = (
    ("synthladder-student",),
    ("synthladder-judge",),
    ("synthladder-matrix",),
    ("synthladder-materialize",),
    ("synthladder-build",),
    ("synthladder-build-levels",),
    ("synthladder-build-paper-eval",),
)


class EvaluationCliHelpTests(unittest.TestCase):
    def test_module_entrypoints_support_help(self):
        for module_name in MODULES_WITH_HELP:
            with self.subTest(module_name=module_name):
                result = subprocess.run(
                    [sys.executable, "-m", module_name, "--help"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, msg=result.stderr)
                self.assertIn("usage:", result.stdout.lower())

    def test_console_scripts_support_help(self):
        for command in SCRIPT_HELP_COMMANDS:
            with self.subTest(command=command):
                result = subprocess.run(
                    ["uv", "run", *command, "--help"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, msg=result.stderr)
                self.assertIn("usage:", result.stdout.lower())


class EvaluationImportabilityTests(unittest.TestCase):
    def test_evaluation_split_modules_import(self):
        for module_name in MODULES_IMPORTABLE:
            with self.subTest(module_name=module_name):
                imported = importlib.import_module(module_name)
                self.assertIsNotNone(imported)


if __name__ == "__main__":
    unittest.main()
