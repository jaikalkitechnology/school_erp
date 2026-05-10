# Jaikalki School ERP — iOS App Icon Set

## Files

`AppIcon.appiconset/` contains 18 icon size variants for iPhone, iPad, and App Store marketing.

## Flutter Integration

### Option A: Drop-in replacement
1. Copy the entire `AppIcon.appiconset/` folder to:
   `ios/Runner/Assets.xcassets/AppIcon.appiconset/`
2. (Replaces existing)

### Option B: Use flutter_launcher_icons
Add to `pubspec.yaml`:
```yaml
flutter_launcher_icons:
  ios: true
  image_path_ios: "assets/icons/jaikalki-school-app-icon-saffron-1024.png"
  remove_alpha_ios: true
```
Then run: `flutter pub run flutter_launcher_icons`

## Important Notes
- iOS adds rounded corners automatically — DO NOT pre-round.
- Icons are flat squares (no transparency, no shadows).
- Marketing icon (1024×1024) MUST have NO alpha channel.
