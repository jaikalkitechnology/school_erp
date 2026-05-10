# Jaikalki School ERP — Android Adaptive Icon

## Files

- `ic_launcher_foreground.png` (432×432) — logo mark, transparent edges
- `ic_launcher_background.png` (432×432) — saffron gradient background
- `ic_launcher_monochrome.png` (432×432) — white silhouette for Android 13+ themed icons
- `ic_launcher.xml` — adaptive icon drawable resource
- `preview-circle-mask.png` — preview with circle mask (Pixel)
- `preview-squircle-mask.png` — preview with squircle mask (Samsung)

## Flutter Integration

1. Copy `ic_launcher_foreground.png`, `ic_launcher_background.png`, `ic_launcher_monochrome.png` into:
   `android/app/src/main/res/mipmap-xxxhdpi/`

2. Resize for other densities (use `flutter_launcher_icons` or manually):
   - `mipmap-mdpi/`: 108×108
   - `mipmap-hdpi/`: 162×162
   - `mipmap-xhdpi/`: 216×216
   - `mipmap-xxhdpi/`: 324×324
   - `mipmap-xxxhdpi/`: 432×432

3. Place `ic_launcher.xml` in `android/app/src/main/res/mipmap-anydpi-v26/`

4. Or use `flutter_launcher_icons` with this config in `pubspec.yaml`:
```yaml
flutter_launcher_icons:
  android: "ic_launcher"
  image_path_android: "assets/icons/ic_launcher_foreground.png"
  adaptive_icon_background: "assets/icons/ic_launcher_background.png"
  adaptive_icon_foreground: "assets/icons/ic_launcher_foreground.png"
  adaptive_icon_monochrome: "assets/icons/ic_launcher_monochrome.png"
```

## Safe Zone

The foreground has a 264×264 safe zone in the center.
Anything outside may be cropped by the launcher's mask (circle, squircle, square, etc.).
