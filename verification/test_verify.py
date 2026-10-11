import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from verify import ExecutionError, command, compare, compare_rows, compare_memory, read_trace

GOOD = "00000000 00100093  1 00000001\n00000004 00000073  0 00000000\n"


class TraceControls(unittest.TestCase):
    def setUp(self):
        base = ROOT / "build/test-temp"
        base.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=base)
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def traces(self, a, b):
        paths = [self.root / "iss", self.root / "rtl"]
        for p, text in zip(paths, (a, b)):
            p.write_text(text)
        return paths

    def test_valid(self):
        self.assertEqual(compare(*self.traces(GOOD, GOOD)), {"status": "PASS", "instructions": 2})

    def test_empty(self):
        with self.assertRaises(ExecutionError): compare(*self.traces("", ""))

    def test_equal_truncated(self):
        with self.assertRaises(ExecutionError): compare(*self.traces(GOOD.splitlines()[0]+"\n", GOOD.splitlines()[0]+"\n"))

    def test_malformed(self):
        with self.assertRaises(ExecutionError): read_trace(self.traces("bad\n", GOOD)[0])

    def test_missing(self):
        with self.assertRaises(FileNotFoundError): read_trace(self.root / "missing")

    def test_unequal_length(self):
        result = compare(*self.traces(GOOD, "00000000 00000073  0 00000000\n"))
        self.assertEqual(result["status"], "DIFF")

    def test_divergent_value(self):
        result = compare(*self.traces(GOOD, GOOD.replace("1 00000001", "1 00000002")))
        self.assertEqual(result["first_divergence"], 1)

    def test_after_halt(self):
        with self.assertRaises(ExecutionError): read_trace(self.traces(GOOD+GOOD, GOOD)[0])

    def test_failed_process(self):
        with self.assertRaises(ExecutionError): command([sys.executable, "-c", "raise SystemExit(3)"], self.root / "log")

    def test_wall_timeout(self):
        with self.assertRaises(ExecutionError): command([sys.executable, "-c", "import time; time.sleep(2)"], self.root / "log", .05)

    def test_process_launch_failure(self):
        with self.assertRaises(ExecutionError): command([str(self.root / "no-program")], self.root / "log")

    def test_incomplete_divergent_prefix(self):
        paths = self.traces(GOOD, GOOD.splitlines()[0].replace("00000001", "00000002")+"\n")
        result = compare_rows(read_trace(paths[0]), read_trace(paths[1], complete=False), prefix=True)
        self.assertEqual(result["first_divergence"], 1)

    def test_memory_without_reload(self):
        result = compare_memory(*self.traces("WORDS 4096\n00002000 00000001\nEND 1\n", "WORDS 4096\nEND 0\n"))
        self.assertEqual(result, {"status": "DIFF", "kind": "memory", "address": 8192, "iss": 1, "rtl": 0})

    def test_zero_memory(self):
        self.assertEqual(compare_memory(*self.traces("WORDS 4096\nEND 0\n", "WORDS 4096\nEND 0\n"))["words_compared"], 4096)

    def test_memory_invalid(self):
        for text in ("", "WORDS 4095\nEND 0\n", "WORDS 4096\nbad\nEND 1\n", "WORDS 4096\n00004000 00000001\nEND 1\n",
                     "WORDS 4096\n00002000 00000000\nEND 1\n", "WORDS 4096\n00002000 00000001\n00002000 00000002\nEND 2\n",
                     "WORDS 4096\nEND 1\n", "WORDS 4096\n00002000 00000001\nEND 0\n"):
            with self.subTest(text=text), self.assertRaises(ExecutionError):
                compare_memory(*self.traces(text, "WORDS 4096\nEND 0\n"))

    def test_memory_equal_truncated(self):
        text = "WORDS 4096\n00002000 00000001\n"
        with self.assertRaises(ExecutionError): compare_memory(*self.traces(text, text))


if __name__ == "__main__": unittest.main()
