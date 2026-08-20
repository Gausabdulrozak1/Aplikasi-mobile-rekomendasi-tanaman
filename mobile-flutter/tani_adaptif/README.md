# TaniAdaptif Flutter

Flutter renders BMKG context, deterministic crop recommendations, a four-week
calendar, local last-known cache, bounded visual history, and optional visual
simulation. Stable Diffusion never selects a crop.

## Configuration

Android emulator development:

```powershell
flutter run --dart-define-from-file=config/development.example.json
```

CPU-safe fixture mode:

```powershell
flutter run --dart-define-from-file=config/mock.example.json
```

Mock data is visibly labelled and is not research data. Replace the invalid
example HTTPS hosts in `config/production.example.json` before a production
build. Do not put tokens or passwords in a dart-define file or APK.

## Verification and Build

```powershell
flutter pub get
dart format --output=none --set-exit-if-changed lib test
flutter analyze
flutter test
flutter build apk --debug
```

Android defaults use `10.0.2.2`; Flutter web defaults use `localhost`. Main
Android manifest includes INTERNET permission, while local cleartext traffic is
allowed only in the debug manifest. Visual failure leaves the rule-based result
visible and supplies a user retry action.
