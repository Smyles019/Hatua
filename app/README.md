# Hatua mobile app (Flutter, Android)

One app for all three roles. The screen set depends on who signs in:

- **Caregiver:** home, children, add child, child profile, milestone check, results, history, profile
- **CHW:** home, flagged children, case review with the three outcomes, caregivers, link or enrol a caregiver, outcomes, profile
- **Administrator:** manage users, usage summary, profile

Visual language: the Hatua design system (plum primary, sun secondary, Nunito headings,
Atkinson Hyperlegible body). Orange and coral appear only on risk chips and cards.

## First-time setup

The Dart code is in `lib/`. The Android platform folder is generated once:

```powershell
cd app
flutter create --org ke.hatua --platforms android .
flutter pub get
```

`flutter create .` keeps the existing `lib/`, `test/` and `pubspec.yaml`.

Then open `android/app/src/main/AndroidManifest.xml` and:

1. Add `<uses-permission android:name="android.permission.INTERNET"/>` above `<application>`.
2. Add `android:usesCleartextTraffic="true"` to `<application>` (the local backend is plain HTTP; remove before any real deployment).
3. Set `android:label="Hatua"`.

## Running against the local backend

Start the backend (see `backend/README.md`), then:

```powershell
flutter run                                        # emulator: reaches the host at 10.0.2.2:8000
flutter run --dart-define=API_URL=http://192.168.1.20:8000   # real phone on the same Wi-Fi
```

## Tests

```powershell
flutter test
flutter analyze
```

## Known limits

- The session token is kept in SharedPreferences (not encrypted). Move to `flutter_secure_storage` before any real deployment.
- English only; Swahili is deferred.
- Tolerates slow connections (20 s timeout, retry buttons) but does not work offline.
