import hashlib
import importlib.util
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("prepare_android_runtime", ROOT / "scripts" / "prepare_android_runtime.py")
runtime = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runtime)


class RuntimePreparationTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = pathlib.Path(self.temporary.name)
        self.apk = self.root / "runtime.apk"
        self.output = self.root / "native"
        header = bytearray(64)
        header[:6] = b"\x7fELF\x02\x01"
        header[16:20] = b"\x03\x00\xb7\x00"
        self.header = bytes(header)

    def write_apk(self, entries=None):
        if entries is None:
            entries = {f"lib/{runtime.ABI}/{name}": self.header for name in runtime.LIBRARIES}
        with zipfile.ZipFile(self.apk, "w") as archive:
            for name, contents in entries.items():
                archive.writestr(name, contents)
        digest = hashlib.sha256(self.apk.read_bytes()).hexdigest()
        patch = mock.patch.object(runtime, "APK_SHA256", digest)
        patch.start()
        self.addCleanup(patch.stop)

    def test_extracts_only_runtime_libraries(self):
        entries = {f"lib/{runtime.ABI}/{name}": self.header for name in runtime.LIBRARIES}
        entries["assets/SPEED2.EXE"] = b"fixture, not game data"
        entries["assets/LANGUAGES/English.bin"] = b"fixture, not game data"
        self.write_apk(entries)
        runtime.extract_runtime(self.apk, self.output)
        self.assertEqual({path.name for path in (self.output / runtime.ABI).iterdir()}, runtime.LIBRARIES)
        self.assertEqual(len(list(self.output.rglob("*"))), len(runtime.LIBRARIES) + 1)
        for name in runtime.LIBRARIES:
            self.assertEqual((self.output / runtime.ABI / name).read_bytes(), self.header)

    def test_rejects_checksum_mismatch(self):
        self.apk.write_bytes(b"invalid APK")
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            runtime.extract_runtime(self.apk, self.output)
        self.assertFalse(self.output.exists())

    def test_rejects_missing_libraries(self):
        entries = {f"lib/{runtime.ABI}/libnfsu2_android.so": self.header}
        self.write_apk(entries)
        with self.assertRaisesRegex(ValueError, "missing native libraries"):
            runtime.extract_runtime(self.apk, self.output)
        self.assertFalse(self.output.exists())

    def test_rejects_invalid_elf(self):
        entries = {f"lib/{runtime.ABI}/{name}": self.header for name in runtime.LIBRARIES}
        entries[f"lib/{runtime.ABI}/libnfsu2_android.so"] = b"not an ELF library"
        self.write_apk(entries)
        with self.assertRaisesRegex(ValueError, "Not an Android ARM64"):
            runtime.extract_runtime(self.apk, self.output)
        self.assertFalse(self.output.exists())

    def test_rejects_unsafe_library_paths(self):
        entries = {f"lib/{runtime.ABI}/{name}": self.header for name in runtime.LIBRARIES}
        entries[f"lib/{runtime.ABI}/../../escape.so"] = self.header
        self.write_apk(entries)
        with self.assertRaisesRegex(ValueError, "Unexpected or duplicate"):
            runtime.extract_runtime(self.apk, self.output)
        self.assertFalse(self.output.exists())

    def test_jni_interface_is_verified(self):
        java = self.root / "java"
        java.mkdir()
        (java / "GameActivity.java").write_text("private static native void nativeKey(int scan, boolean down);")
        (java / "GpuProbeActivity.java").write_text("private static native String nativeGpuReport();")
        symbols = [
            "ANativeActivity_onCreate T 0 0\nJava_com_nfsu2_androidevolved_GameActivity_nativeKey T 0 0\n",
            "Java_com_nfsu2_androidevolved_GpuProbeActivity_nativeGpuReport T 0 0\n",
        ]
        with mock.patch.object(runtime.subprocess, "check_output", side_effect=symbols):
            runtime.verify_jni(self.output, java, pathlib.Path("llvm-nm"))
        with mock.patch.object(runtime.subprocess, "check_output", return_value=""):
            with self.assertRaisesRegex(ValueError, "missing JNI exports"):
                runtime.verify_jni(self.output, java, pathlib.Path("llvm-nm"))

    def built_apk(self, extra=None, changed_library=False):
        self.write_apk()
        runtime.extract_runtime(self.apk, self.output)
        built = self.root / "built.apk"
        with zipfile.ZipFile(built, "w") as archive:
            for name in runtime.LIBRARIES:
                data = self.header + (b"changed" if changed_library and name == "libnfsu2_android.so" else b"")
                archive.writestr(f"lib/{runtime.ABI}/{name}", data)
            archive.writestr("classes.dex", b"GAME FILES PLAY Game language Lcom/nfsu2/androidevolved/NativeMessages;")
            if extra:
                archive.writestr(extra, b"fixture")
        return built

    def test_built_apk_preserves_runtime_and_english_launcher(self):
        runtime.verify_apk(self.built_apk(), self.output)

    def test_built_apk_rejects_changed_runtime(self):
        with self.assertRaisesRegex(ValueError, "changed the prebuilt runtime"):
            runtime.verify_apk(self.built_apk(changed_library=True), self.output)

    def test_built_apk_rejects_game_files(self):
        for name in ("assets/SPEED2.EXE", "assets/LANGUAGES/English.bin"):
            with self.subTest(name=name):
                with self.assertRaisesRegex(ValueError, "provided on the device"):
                    runtime.verify_apk(self.built_apk(extra=name), self.output)


class NativeMessagesTest(unittest.TestCase):
    def test_legacy_native_messages_are_english(self):
        java_home = os.environ.get("JAVA_HOME")
        suffix = ".exe" if os.name == "nt" else ""
        javac = str(pathlib.Path(java_home) / "bin" / ("javac" + suffix)) if java_home else shutil.which("javac")
        java = str(pathlib.Path(java_home) / "bin" / ("java" + suffix)) if java_home else shutil.which("java")
        if not javac or not java:
            self.fail("A JDK is required for native message translation checks")
        source = ROOT / "android" / "app" / "src" / "main" / "java" / "com" / "nfsu2" / "androidevolved" / "NativeMessages.java"
        with tempfile.TemporaryDirectory() as directory:
            subprocess.run(
                [javac, "-encoding", "UTF-8", "-d", directory, str(source), str(ROOT / "tests" / "android_launcher" / "NativeMessagesCheck.java")],
                check=True,
            )
            subprocess.run([java, "-cp", directory, "com.nfsu2.androidevolved.NativeMessagesCheck"], check=True)


class SigningWorkflowTest(unittest.TestCase):
    def test_private_key_is_restored_from_an_encrypted_secret(self):
        workflow = (ROOT / ".github" / "workflows" / "android-release.yml").read_text(encoding="utf-8")
        self.assertIn("${{ secrets.ANDROID_DEBUG_KEYSTORE_BASE64 }}", workflow)
        self.assertNotIn("vars.ANDROID_DEBUG_KEYSTORE_BASE64", workflow)
        self.assertNotIn("react-native-community/template", workflow)
        self.assertNotIn("-genkeypair", workflow)
        self.assertIn("umask 077", workflow)
        self.assertIn('rm -f "$RUNNER_TEMP/nfsu2-debug.keystore"', workflow)


class WorkflowTriggersTest(unittest.TestCase):
    def test_main_and_feature_branch_support_push_and_manual_runs(self):
        workflow = (ROOT / ".github" / "workflows" / "android-release.yml").read_text(encoding="utf-8")
        triggers = workflow.split("\non:\n", 1)[1].split("\npermissions:", 1)[0]
        self.assertIn("  workflow_dispatch:", triggers)
        self.assertIn("  push:", triggers)
        self.assertIn("      - main", triggers)
        self.assertIn("      - feat/english-launcher-android-release", triggers)
        self.assertNotIn("paths:", triggers)
        self.assertIn("          overwrite: true", workflow)


if __name__ == "__main__":
    unittest.main()
