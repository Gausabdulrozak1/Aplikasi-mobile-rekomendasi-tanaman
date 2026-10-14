# APK Build Report

Latest build verification: 2026-08-05 (Asia/Makassar)

## Result

| Item | Actual value |
| --- | --- |
| Artifact | `artifacts/apk/taniadaptif-debug.apk` |
| Variant | debug |
| Size | 152,840,310 bytes |
| SHA-256 | `ffb15a9f38c4242d2482976d71e101f1564eab2cbbd48eda78b59b37409d2996` |
| Package | `com.hamzanwadi.tani_adaptif` |
| Version | `1.0.0` (`versionCode` 1) |
| minSdk | 24 |
| targetSdk / compileSdk | 36 / 36 |
| Native ABIs | arm64-v8a, armeabi-v7a, x86_64 |
| INTERNET permission | present |
| Application label | TaniAdaptif |

## Commands and Validation

1. `flutter build apk --debug` completed successfully.
2. The initial build completed but Kotlin reported a cross-drive incremental-cache
   exception and used compiler fallback. `kotlin.incremental=false` was added.
3. The latest `flutter build apk --debug` completed cleanly in 40.9 seconds;
   its size and SHA-256 are identical to the prior verified build.
4. Android `apksigner` verification passed using APK Signature Scheme v2.
5. Android `aapt2 dump badging` confirmed package, SDK levels, label, ABIs, and
   INTERNET permission shown above.
6. `Get-FileHash -Algorithm SHA256` produced the recorded checksum.
7. The first standalone `apksigner` invocation lacked process-local
   `JAVA_HOME`; it was rerun with Android Studio JDK 21 and passed. No system
   environment, registry, or signing configuration was changed.

## Signing Scope

This is intentionally a debug-signed APK. The project no longer assigns the
debug signing configuration to the release build. No release keystore,
password, or fabricated signing identity was created. A release APK is pending
an authorized release-signing configuration.

## Device Status

No Android device was connected during this run. Installation, network routing
on a physical phone, and physical-device UI/UAT remain pending-device-test.
