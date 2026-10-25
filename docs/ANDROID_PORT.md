# Android ARM64 / Vulkan 1.1

Current runtime: [0.4.0 input/audio/device status](ANDROID_INPUT_AUDIO_TEST.md).
The original initial splash has rendered through DXVK on the physical phone.
Prepare the pinned graphics dependency as described in
[DXVK build prerequisites](../ports/dxvk_android/README.md) before running Gradle.

Windows gameplay accepted as validated by the owner on 2026-10-07.
Update: [portable guest integration](ANDROID_RUNTIME.md) now compiles the full
generated game code for ARM64, maps the PE, binds imports and attempts its CRT
entry. The initial bootstrap test results below predate this connection.
The independent `android/` build advances the port without changing the
MSVC x86 reference build. CRT bring-up is connected; the APK is not playable.

## Diagnostic renderer and storage foundation

- Android NativeActivity, Android 8+ (API 26), arm64-v8a only.
- Vulkan instance requesting 1.1, graphics/present queue and FIFO swapchain.
- Render-pass clear and presentation using only Vulkan 1.1 core and Android
  surface/swapchain extensions. No descriptor indexing, shaderInt64, buffer
  device address, dynamic rendering or synchronization2 requirements.
- Surface format/usage/extent/composite-alpha checks, pause/resume cleanup,
  window recreation and out-of-date swapchain handling.
- Separate render-finished semaphore per swapchain image. Serialized queue
  completion for initial bring-up; frame fences are a later performance step.
- GuestMemory reserves a 4 GiB virtual address space with inaccessible pages;
  commit uses the device page size. Guest addresses remain uint32 offsets;
  host pointers remain 64-bit. Startup checks image/high addresses and rejects
  ranges that wrap. The class is connected to ADDR, the PE loader and explicit
  guest calls; guest heap services are implemented. Reservation is not 4 GiB of
  physical RAM.
- Fixed game root: `/storage/emulated/0/nfsu2` (Internal storage/nfsu2).
  The application checks readable data folders and executable header/size.
  Android 11+ uses the all-files access settings screen; Android 8–10 requests
  read permission. Files remain external to the APK.
- Launcher icon from `ICONO/ICONO.png`, and a diagnostic status overlay.

## Build and inspect

Install Android SDK platform 35, NDK 28.2.13676358, CMake 3.30.5, and a JDK
compatible with Android Gradle Plugin 8.7.3. Set ANDROID_HOME and JAVA_HOME,
or configure the SDK through Android Studio. From `android/`:

```powershell
./gradlew.bat --no-daemon assembleDebug
adb install -r app/build/outputs/apk/debug/app-debug.apk
adb shell am start -n com.nfsu2.androidevolved/.LauncherActivity
adb logcat -s NFSU2
```

Copy files first with `scripts/copy_android_data.ps1 -GameRoot <installation>`
and allow storage access when prompted. The launcher selects the game language
before starting the guest. The following describes the historical bootstrap:
a dark teal screen and status
text, `Guest memory self-check passed`, `Game data readable`, `Bootstrap ready`
and `Presented frames` in logcat. Runtime 0.2.0 additionally attempts the actual
CRT entry and reports its first unsupported HLE import. No game assets are
packaged; generated code from the owner's copy is included in this local APK.
See [device test report](ANDROID_DEVICE_TEST.md) for version 0.1.0 real-device
verification. Version 0.2.0 includes locally generated code and has now passed
initial ARM64 runtime and Home/return checks; see ANDROID_RUNTIME.md for evidence.

### GitHub Actions release APK

The **Android release APK (debug-signed)** workflow runs on every push to `main`
or `feat/english-launcher-android-release`, and supports manual dispatch for
either branch. It needs **no game files, generated game C,
or private game-source archives**. Signing uses one encrypted repository Actions
secret, `ANDROID_DEBUG_KEYSTORE_BASE64`.

GitHub requires the workflow file on the default branch before exposing the
manual **Run workflow** button. Once registered there, select
`feat/english-launcher-android-release` in the branch dropdown, or run
`gh workflow run android-release.yml --ref feat/english-launcher-android-release`.
Before that registration, pushing this feature branch starts the workflow and
its runs can be started again manually with **Re-run all jobs**. Artifact upload
replaces the previous attempt's artifact so these reruns remain usable.

CI rebuilds the English Java launcher and resources, packaging the six native
ARM64 libraries from the published
[upstream v0.14.10 APK](https://github.com/codepdbh/nfsu2-recompiled/releases/tag/v0.14.10).
That release is built from commit `a8c7a39ce7b75b7a49368445a9a2b7ca5cf6e1f3`,
the native interface used by this launcher. `scripts/prepare_android_runtime.py`
verifies the APK's SHA-256, checks the ARM64 ELF headers and required libraries,
and checks the JNI exports against the current Java declarations. Only native
libraries are copied; no game executable or assets are bundled.

**The device setup is unchanged:** install the APK, then provide your own game
files in Internal storage/nfsu2 and grant file access. Game language selection
remains independent of the English launcher. Spanish status/error text from the
prebuilt runtime is translated at the Java UI boundary.

The workflow builds `assembleRelease`, verifies that the APK is not debuggable
and uses the expected certificate, and uploads `nfsu2-release-arm64-v8a`.
It restores a fixed private debug keystore from
`${{ secrets.ANDROID_DEBUG_KEYSTORE_BASE64 }}` immediately before building and
removes the runner's temporary copy afterward. The key is generated **once**,
not on each runner, so later builds retain the same signing identity. It must
be an Actions **secret**, not an unencrypted repository variable.

The keystore uses alias `androiddebugkey`, store password `android`, and key
password `android`, matching Gradle's debug signing configuration. Its contents
must stay private even though those standard debug passwords are well-known.
Keep a secure backup outside Git. This is a development signing identity, not
a production/Play Store signing setup.

For a repository's first-time setup, only if the signing secret does not already
exist, authenticate GitHub CLI and create or reuse a dedicated keystore outside
the checkout. On another machine, transfer the existing key's secure backup
instead of generating a replacement:

```powershell
$key = Join-Path $env:USERPROFILE ".android\nfsu2-recompiled-signing\ci-debug.keystore"
if (!(Test-Path -LiteralPath $key)) {
    New-Item -ItemType Directory -Force (Split-Path $key) | Out-Null
    keytool -genkeypair -keystore $key -storetype JKS -alias androiddebugkey `
      -storepass android -keypass android -keyalg RSA -keysize 2048 `
      -sigalg SHA256withRSA -validity 10000 -dname "CN=Android Debug,O=Android,C=US"
    if ($LASTEXITCODE -ne 0) { throw "Keystore generation failed" }
}
[Convert]::ToBase64String([IO.File]::ReadAllBytes($key)) |
    gh secret set ANDROID_DEBUG_KEYSTORE_BASE64 --repo axel92b/nfsu2-recompiled
```

Do not regenerate the key or replace the secret for ordinary builds. Its
certificate differs from upstream's and the earlier public-test-key build, so
those APKs cannot be updated in place with this key. Back up app-private
data/settings before switching installations. Subsequent private-key builds
can update one another.

To build the launcher locally without game files, install the SDK/NDK and JDK
listed above, set `ANDROID_HOME` and `JAVA_HOME`, and run from the repository root:

```powershell
python scripts\prepare_android_runtime.py build\android-runtime
Set-Location android
.\gradlew.bat --no-daemon -PnfsNativeLibraries=..\build\android-runtime assembleRelease
```

Set `NFSU2_DEBUG_KEYSTORE` to the dedicated private keystore's absolute path to
reproduce CI's signing identity; otherwise local builds use the normal Android
debug keystore. Never put the keystore or its Base64 contents in source control.

This CI path reuses, rather than recompiles, the native engine. Native gameplay
changes require updating the pinned runtime or using the existing full-source
build. Omitting `-PnfsNativeLibraries` keeps that original CMake build path and
its documented locally generated C/pcrecomp/DXVK prerequisites.

Launcher/runtime checks: `python -m unittest discover -s tests\android_launcher -p "test_*.py" -v`.

## Reference review

- https://github.com/codepdbh/NFS-CARBON-360-ANDROID-RECOMP
  revision 08251847d48222aa6304b9ee521bfe8f430550fa
- https://github.com/codepdbh/nfsmw-android
  revision bc0fe33c4b4d9a5147f790122fb4af39f3734f1c

Both target Xbox 360 PowerPC/Xenos through ReXGlue. Their native renderer uses
Xenos registers and title-specific hooks; it cannot directly replace PC D3D9
or the x86 runtime. Useful reference patterns: optional 64-bit GPU addressing,
Vulkan 1.1 shader compatibility, BC texture CPU fallback, shader caches and
Android lifecycle. NFSU2 should generate SPIR-V for Vulkan 1.1 directly rather
than copy a shader version conversion specialized to a different library.
Their renderer code has not been copied into this MIT project. The standard
Gradle wrapper launchers/JAR were obtained from the MW reference (Gradle's
Apache-licensed tooling); the application and Vulkan bootstrap are new code.

## Original bootstrap roadmap (historical)

1. Portable x86 machine state and explicit guest callback dispatch, with
   complete integer/x87/MMX/SSE/MXCSR/flags state and serialized guest threads.
2. Connect guest memory to generated ADDR accesses and a relocatable PE loader.
   Audit unaligned accesses and host-pointer casts for ARM64 before execution.
3. Bind used Win32 imports to HLE; add guest handles and COM objects/vtables in
   guest memory. Never store native function/object pointers in guest uint32s.
4. D3D9 shim adapter: resources, locks/uploads, state, vertex declarations,
   draw commands and D3D9 bytecode-to-SPIR-V translation. Start with an isolated
   textured draw, then the intro/menu; use race traces to complete coverage.
5. DXT1/DXT5 CPU-to-RGBA fallback if BC formats are unsupported. Check depth,
   render-target and sampler capabilities; expose only supported D3D9 caps.
6. Android files/import, audio, input and game lifecycle, then menu and race.

The game's statically linked D3DX must also run correctly in the portable guest
runtime or be replaced at identified boundaries. Xbox 360 shader containers
and their shader tooling are not PC D3D9 shader inputs.
