# APK Debug Proxy Build Report

Verification date: 2026-08-21 (Asia/Makassar)

| Item | Actual value |
| --- | --- |
| Artifact | `artifacts/apk/taniadaptif-debug-proxy-20260821.apk` |
| Variant | debug, default development configuration |
| Size | 152,840,310 bytes |
| SHA-256 | `417604f6a2180401aef576c8f01bf5bc1997dadae27311c1841f1a58d48cedb5` |
| Package | `com.hamzanwadi.tani_adaptif` |
| Version | `1.0.0` (`versionCode` 1) |
| minSdk / targetSdk / compileSdk | 24 / 36 / 36 |
| Native ABIs | arm64-v8a, armeabi-v7a, x86_64 |
| INTERNET permission | present |
| Signature | Android debug certificate, APK Signature Scheme v2 verified |

`flutter build apk --debug` completed successfully after the visual path was
changed to Flutter -> Express -> private FastAPI. Flutter analyze and all 13
Flutter tests passed.

This artifact contains no production RunPod URL or client token. It proves the
Android code compiles; it is not a release APK and is not real-inference or
physical-device evidence. Build/run the controlled test with ignored
`config/production.local.json` only after the remote GPU endpoint exists.
