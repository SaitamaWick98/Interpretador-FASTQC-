"""Pruebas sin red, Java, FastQC ni SDK de Google instalados."""
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock, patch

import analyzer
from ai_interpreter import AIError, build_prompt, interpret_with_ai
from fastqc_reader import parse_fastqc_data, read_fastqc_data
from fastqc_runner import run_fastqc


DATA = (
    "##FastQC\t0.12.1\n>>Basic Statistics\tpass\n"
    "#Measure\tValue\nFilename\tmuestra.fastq\n>>END_MODULE\n"
    ">>Per base sequence quality\twarn\n#Base\tMean\n1\t25\n>>END_MODULE\n"
)


def archive(path, content=DATA, member="original_fastqc/fastqc_data.txt"):
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(member, content)


class ReaderTests(unittest.TestCase):
    def test_preserves_headers_and_states(self):
        results = parse_fastqc_data(DATA)
        self.assertEqual(results["Per base sequence quality"]["status"], "warn")
        self.assertIn("#Base\tMean", results["Per base sequence quality"]["data"])

    def test_rejects_malformed_modules(self):
        for content in ("", ">>END_MODULE", ">>Test", ">>Test\tunknown\n>>END_MODULE",
                        ">>Test\tpass\n1", ">>Test\tpass\n>>Other\tpass", DATA + DATA,
                        DATA + "orphan data"):
            with self.subTest(content=content), self.assertRaises(ValueError):
                parse_fastqc_data(content)

    def test_renamed_zip_and_internal_fastqc_in_name(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            archive(path / "test_fastqc_copy_fastqc.zip")
            (path / "unrelated.zip").write_text("not a ZIP")
            result = read_fastqc_data(path)
            self.assertEqual(list(result), ["test_fastqc_copy"])

    def test_rejects_missing_ambiguous_and_corrupt_data(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            target = path / "sample_fastqc.zip"
            for kind in ("missing", "ambiguous", "corrupt", "encoding"):
                with self.subTest(kind=kind):
                    if kind == "corrupt":
                        target.write_text("broken")
                    else:
                        with zipfile.ZipFile(target, "w") as zf:
                            if kind == "missing":
                                zf.writestr("other.txt", "data")
                            elif kind == "encoding":
                                zf.writestr("fastqc_data.txt", b"\xff")
                            else:
                                zf.writestr("a/fastqc_data.txt", DATA)
                                zf.writestr("b/fastqc_data.txt", DATA)
                    with self.assertRaisesRegex(ValueError, "sample_fastqc.zip"):
                        read_fastqc_data(path)

    def test_no_reports(self):
        with tempfile.TemporaryDirectory() as directory, self.assertRaises(ValueError):
            read_fastqc_data(Path(directory))


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.sample = self.root / "sample with spaces.fastq"
        self.sample.write_text("@read\nACGT\n+\nIIII\n")

    def fake_run(self, command, **kwargs):
        directory = Path(command[-1])
        for name in command[1:command.index("--noextract")]:
            archive(directory / (Path(name).stem + "_fastqc.zip"))
        return SimpleNamespace(returncode=0, stdout="done", stderr="")

    def test_isolated_runs_do_not_read_old_archives(self):
        output = self.root / "nested" / "output"
        output.mkdir(parents=True)
        archive(output / "old_fastqc.zip")
        with patch("fastqc_runner.shutil.which", return_value="/fake/fastqc"), \
             patch("fastqc_runner.subprocess.run", side_effect=self.fake_run) as run:
            first = run_fastqc(str(self.sample), output_dir=str(output))
            second = run_fastqc(str(self.sample), output_dir=str(output))
        self.assertNotEqual(first, second)
        self.assertNotIn("old", read_fastqc_data(first))
        self.assertEqual(run.call_args.args[0][1], str(self.sample.resolve()))

    def test_invalid_inputs(self):
        empty = self.root / "empty.fastq"
        empty.touch()
        for files in ((), (str(self.root),), (str(empty),), (str(self.root / "absent"),)):
            with self.subTest(files=files), self.assertRaises(ValueError):
                run_fastqc(*files)

    def test_duplicate_output_names(self):
        duplicate = self.root / "sample with spaces.fastq.gz"
        duplicate.write_text("dummy")
        with self.assertRaisesRegex(ValueError, "mismo nombre"):
            run_fastqc(str(self.sample), str(duplicate))

    def test_missing_executable(self):
        with patch("fastqc_runner.shutil.which", return_value=None), self.assertRaisesRegex(RuntimeError, "PATH"):
            run_fastqc(str(self.sample))

    def test_failed_process_keeps_logs(self):
        output = self.root / "output"
        with patch("fastqc_runner.shutil.which", return_value="fastqc"), \
             patch("fastqc_runner.subprocess.run", return_value=SimpleNamespace(returncode=1, stdout="", stderr="Java error")), \
             self.assertRaisesRegex(RuntimeError, "código 1"):
            run_fastqc(str(self.sample), output_dir=str(output))
        self.assertEqual(next(output.glob("run-*/fastqc.stderr.log")).read_text(), "Java error")

    def test_success_without_zip_is_error(self):
        with patch("fastqc_runner.shutil.which", return_value="fastqc"), \
             patch("fastqc_runner.subprocess.run", return_value=SimpleNamespace(returncode=0, stdout="", stderr="")), \
             self.assertRaisesRegex(RuntimeError, "ZIP por entrada"):
            run_fastqc(str(self.sample), output_dir=str(self.root / "output"))


class AITests(unittest.TestCase):
    def test_missing_key(self):
        with patch.dict(os.environ, {}, clear=True), self.assertRaisesRegex(AIError, "GOOGLE_API_KEY"):
            interpret_with_ai({})

    def test_prompt_keeps_headers(self):
        prompt = build_prompt({"sample": parse_fastqc_data(DATA)})
        self.assertIn("#Measure", prompt)
        self.assertIn("No emitas una clasificación definitiva", prompt)

    def test_oversized_prompt(self):
        with self.assertRaisesRegex(AIError, "límite local"):
            build_prompt({"data": "x" * 200_001})

    def test_sdk_success_empty_and_failure(self):
        google = ModuleType("google")
        google.genai = SimpleNamespace(Client=MagicMock())
        client = google.genai.Client.return_value.__enter__.return_value
        with patch.dict(sys.modules, {"google": google}), patch.dict(os.environ, {"GOOGLE_API_KEY": "fake-secret"}):
            client.models.generate_content.return_value = SimpleNamespace(text=" interpretation ")
            self.assertEqual(interpret_with_ai({}, model="chosen-model"), "interpretation")
            self.assertEqual(client.models.generate_content.call_args.kwargs["model"], "chosen-model")
            client.models.generate_content.return_value = SimpleNamespace(text=None)
            with self.assertRaisesRegex(AIError, "no devolvió texto"):
                interpret_with_ai({})
            client.models.generate_content.side_effect = RuntimeError("fake-secret")
            with self.assertRaises(AIError) as error:
                interpret_with_ai({})
            self.assertNotIn("fake-secret", str(error.exception))


class CLITests(unittest.TestCase):
    def test_full_cli_without_sdk_and_with_fake_fastqc(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            executable = root / "fastqc"
            executable.write_text(
                f"#!{sys.executable}\n"
                "import pathlib, sys, zipfile\n"
                "output = pathlib.Path(sys.argv[-1])\n"
                "for name in sys.argv[1:sys.argv.index('--noextract')]:\n"
                "    sample = pathlib.Path(name).stem\n"
                "    with zipfile.ZipFile(output / (sample + '_fastqc.zip'), 'w') as zf:\n"
                f"        zf.writestr(sample + '_fastqc/fastqc_data.txt', {DATA!r})\n"
            )
            executable.chmod(0o755)
            sample = root / "sample with spaces.fastq"
            sample.write_text("@read\nACGT\n+\nIIII\n")
            output = root / "output"
            output.mkdir()
            archive(output / "old_fastqc.zip")
            env = dict(os.environ, PATH=str(root))
            env.pop("GOOGLE_API_KEY", None)
            for _ in range(2):
                result = subprocess.run(
                    [sys.executable, "-S", "analyzer.py", str(sample), "--no-ai", "-o", str(output)],
                    capture_output=True, text=True, env=env,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertNotIn("Muestra: old", result.stdout)
            reports = list(output.glob("run-*/results.json"))
            self.assertEqual(len(reports), 2)
            for report in reports:
                self.assertEqual(list(json.loads(report.read_text())), ["sample with spaces"])

    def test_help_without_site_packages(self):
        result = subprocess.run([sys.executable, "-S", "analyzer.py", "--help"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--no-ai", result.stdout)

    def test_no_ai_and_ai_error_preserve_reports(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            archive(path / "sample_fastqc.zip")
            with patch("analyzer.run_fastqc", return_value=path), \
                 patch("analyzer.interpret_with_ai", side_effect=AIError("API unavailable")) as ai, \
                 contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(analyzer.main(["sample.fastq", "--no-ai"]), 0)
                ai.assert_not_called()
                self.assertEqual(analyzer.main(["sample.fastq"]), 3)
            self.assertIn("API unavailable", (path / "reporte.txt").read_text())
            results = json.loads((path / "results.json").read_text())
            self.assertIn("#Measure", results["sample"]["Basic Statistics"]["data"])

    def test_ai_success_saved(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            archive(path / "sample_fastqc.zip")
            with patch("analyzer.run_fastqc", return_value=path), \
                 patch("analyzer.interpret_with_ai", return_value="Interpretación de prueba") as ai, \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(analyzer.main(["sample.fastq", "--model", "model-test"]), 0)
            self.assertEqual(ai.call_args.kwargs["model"], "model-test")
            self.assertIn("Interpretación de prueba", (path / "reporte.txt").read_text())


if __name__ == "__main__":
    unittest.main()
