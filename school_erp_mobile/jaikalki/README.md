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
