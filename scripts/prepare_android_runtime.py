"""Prepare the pinned ARM64 native runtime without game files or generated game C."""
import argparse
import hashlib
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
ABI = "arm64-v8a"
APK_URL = (
    "https://github.com/codepdbh/nfsu2-recompiled/releases/download/v0.14.10/"
    "NFSU2-AndroidEvolved-v0.14.10-arm64.apk"
)
APK_SHA256 = "9c6c80b364bbe1399355b22a06fa9f4c16f425229cae00ebee425843cb9cf282"
LIBRARIES = {
    "libfile_redirect_hook.so", "libgsl_alloc_hook.so", "libhook_impl.so",
    "libmain_hook.so", "libnfsu2_android.so", "libnfsu2_diagnostics.so",
}


def sha256(source):
    digest = hashlib.sha256()
    for block in iter(lambda: source.read(1024 * 1024), b""):
        digest.update(block)
    return digest.hexdigest()


def extract_runtime(apk, output):
    with apk.open("rb") as source:
        if sha256(source) != APK_SHA256:
            raise ValueError("Upstream runtime APK SHA-256 mismatch")

    prefix = f"lib/{ABI}/"
    with zipfile.ZipFile(apk) as archive:
        libraries = {}
        for entry in archive.infolist():
            if not entry.filename.startswith(prefix) or entry.is_dir():
                continue
            name = entry.filename[len(prefix):]
            if name not in LIBRARIES or name in libraries:
                raise ValueError(f"Unexpected or duplicate native library: {entry.filename}")
            with archive.open(entry) as source:
                header = source.read(64)
            if len(header) != 64 or header[:6] != b"\x7fELF\x02\x01" or header[16:20] != b"\x03\x00\xb7\x00":
                raise ValueError(f"Not an Android ARM64 shared library: {name}")
            libraries[name] = entry
        missing = LIBRARIES - libraries.keys()
        if missing:
            raise ValueError(f"Runtime APK is missing native libraries: {', '.join(sorted(missing))}")

        destination = output / ABI
        destination.mkdir(parents=True, exist_ok=True)
        for name, entry in libraries.items():
            with archive.open(entry) as source, (destination / name).open("wb") as target:
                shutil.copyfileobj(source, target)


def verify_jni(output, java, nm):
    for activity, library in (
        ("GameActivity", "libnfsu2_android.so"),
        ("GpuProbeActivity", "libnfsu2_diagnostics.so"),
    ):
        methods = re.findall(r"\bnative\s+\S+\s+(\w+)\s*\(", (java / f"{activity}.java").read_text(encoding="utf-8"))
        expected = {f"Java_com_nfsu2_androidevolved_{activity}_{method}" for method in methods}
        if activity == "GameActivity":
            expected.add("ANativeActivity_onCreate")
        symbols = subprocess.check_output(
            [str(nm), "--dynamic", "--defined-only", "--format=posix", str(output / ABI / library)],
            text=True,
        )
        exports = {line.split()[0] for line in symbols.splitlines() if line.strip()}
        missing = expected - exports
        if missing:
            raise ValueError(f"{library} is missing JNI exports: {', '.join(sorted(missing))}")


def verify_apk(apk, runtime):
    with zipfile.ZipFile(apk) as archive:
        names = archive.namelist()
        expected = {f"lib/{ABI}/{name}" for name in LIBRARIES}
        packaged = [name for name in names if name.startswith("lib/") and name.endswith(".so")]
        if set(packaged) != expected or len(packaged) != len(expected):
            raise ValueError("Built APK does not contain exactly the expected ARM64 runtime libraries")
        for name in expected:
            source_path = runtime.joinpath(*name.split("/")[1:])
            with archive.open(name) as packaged_library, source_path.open("rb") as source_library:
                if sha256(packaged_library) != sha256(source_library):
                    raise ValueError(f"Built APK changed the prebuilt runtime: {name}")
        for name in names:
            if name.upper().split("/")[-1] == "SPEED2.EXE" or re.match(
                r"assets/(CARS|CREDITS|FRONTEND|GLOBAL|LANGUAGES|MOVIES|NIS|SDATA|SOUND|SUBTITLES|TRACKS)/",
                name, re.IGNORECASE,
            ):
                raise ValueError(f"Game files must be provided on the device, not bundled: {name}")
        dex = b"".join(archive.read(name) for name in names if re.fullmatch(r"classes\d*\.dex", name))
        for text in (b"GAME FILES", b"PLAY", b"Game language", b"Lcom/nfsu2/androidevolved/NativeMessages;"):
            if text not in dex:
                raise ValueError(f"English launcher code is missing from the APK: {text.decode()}")


def find_nm():
    sdk = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
    if not sdk:
        raise RuntimeError("Set ANDROID_HOME to the Android SDK, or pass --nm")
    host = {"win32": "windows-x86_64", "linux": "linux-x86_64", "darwin": "darwin-x86_64"}.get(sys.platform)
    if host is None:
        raise RuntimeError(f"Unsupported NDK host: {sys.platform}")
    tool = "llvm-nm.exe" if sys.platform == "win32" else "llvm-nm"
    nm = pathlib.Path(sdk) / "ndk" / "28.2.13676358" / "toolchains" / "llvm" / "prebuilt" / host / "bin" / tool
    if not nm.is_file():
        raise FileNotFoundError(f"Install Android NDK 28.2.13676358: {nm}")
    return nm


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=pathlib.Path, help="Prepared jniLibs directory")
    parser.add_argument("--apk", type=pathlib.Path, help="Use a cached copy of the pinned upstream APK")
    parser.add_argument("--nm", type=pathlib.Path, help="Path to the NDK llvm-nm tool")
    parser.add_argument("--verify-apk", type=pathlib.Path, help="Verify a built APK against the prepared runtime")
    args = parser.parse_args()
    if args.verify_apk is not None:
        verify_apk(args.verify_apk, args.output)
        print(f"Verified English launcher, unchanged native libraries and no bundled game files in {args.verify_apk}")
        return
    nm = args.nm if args.nm is not None else find_nm()
    if args.apk is not None:
        extract_runtime(args.apk, args.output)
    else:
        with tempfile.TemporaryDirectory(prefix="nfsu2-runtime-") as directory:
            apk = pathlib.Path(directory) / "runtime.apk"
            with urllib.request.urlopen(APK_URL, timeout=120) as source, apk.open("wb") as target:
                shutil.copyfileobj(source, target)
            extract_runtime(apk, args.output)
    java = ROOT / "android" / "app" / "src" / "main" / "java" / "com" / "nfsu2" / "androidevolved"
    verify_jni(args.output, java, nm)
    print(f"Verified upstream v0.14.10 native runtime and JNI interface in {args.output}")


if __name__ == "__main__":
    main()
