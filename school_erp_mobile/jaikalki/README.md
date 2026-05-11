# Jaikalki School ERP — Mobile App

Flutter app used by everyone except the Super Admin: principals, teachers,
parents, students, accountants, librarians, transport managers, hostel wardens,
office staff, plus a quick-approvals UI for the school admin.

## Run

```bash
flutter pub get
flutter run            # Android emulator / iOS sim
flutter run -d chrome  # Web preview
```

The backend (`../school_erp_backend`) needs to be on `http://localhost:8000`.
The default `ApiClient` uses `10.0.2.2:8000` so the Android emulator can reach
the host machine — adjust `lib/src/api/api_client.dart` if you're on iOS or
the web target.

## App icon

The launcher icon is generated from `assets/icons/` (kept in version
control). After editing any of the source PNGs — or pulling a new
saffron-themed mark — regenerate every Android density, the iOS
AppIcon.appiconset, the web favicon, and the Windows .ico in one shot:

```bash
dart run flutter_launcher_icons
```

Sources (all 432×432 for adaptive, 1024×1024 for the iOS master):

- `assets/icons/ic_launcher_foreground.png` — logo mark on transparent
- `assets/icons/ic_launcher_background.png` — saffron gradient layer
- `assets/icons/ic_launcher_monochrome.png` — Android 13+ themed icon
- `assets/icons/app_icon.png` — full-bleed 1024 master (iOS / web / Windows)

Config lives under `flutter_launcher_icons:` in `pubspec.yaml`.

## Structure

```
lib/
├── main.dart
├── src/
│   ├── app.dart                    # Root MaterialApp.router
│   ├── theme/brand.dart            # Jaikalki design tokens (saffron / teal …)
│   ├── routing/router.dart         # go_router configuration
│   ├── core/service_locator.dart   # get_it container
│   ├── api/api_client.dart         # Dio wrapper
│   ├── models/user_role.dart       # 13-role enum
│   └── features/
│       ├── auth/login_page.dart
│       └── dashboard/dashboard_page.dart
```

## Phase 0 acceptance

- [x] Boots on Android, iOS, Web
- [x] Jaikalki theme applied (Fraunces + DM Sans, saffron/marigold/teal/indigo)
- [x] Login → Dashboard route flow with go_router
- [x] Dashboard renders the API health probe via Dio
- [x] Widget test boots the app and finds the login form
