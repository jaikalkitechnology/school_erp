import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:hive/hive.dart';

import '../i18n/strings.dart';

const _kSettingsBox = 'jaikalki.settings';
const _kLangKey = 'lang';
const _kThemeKey = 'theme_mode';
const _kOnboardedKey = 'onboarded';

class SettingsState {
  const SettingsState({
    required this.language,
    required this.themeMode,
    required this.onboarded,
  });

  final AppLanguage language;
  final ThemeMode themeMode;
  final bool onboarded;

  AppStrings get strings => AppStrings.of(language);

  SettingsState copyWith({
    AppLanguage? language,
    ThemeMode? themeMode,
    bool? onboarded,
  }) =>
      SettingsState(
        language: language ?? this.language,
        themeMode: themeMode ?? this.themeMode,
        onboarded: onboarded ?? this.onboarded,
      );

  static const initial = SettingsState(
    language: AppLanguage.english,
    themeMode: ThemeMode.system,
    onboarded: false,
  );
}

class SettingsCubit extends Cubit<SettingsState> {
  SettingsCubit() : super(SettingsState.initial);

  Future<void> bootstrap() async {
    final box = await Hive.openBox(_kSettingsBox);
    final lang = AppLanguageX.fromCode((box.get(_kLangKey) as String?) ?? 'en');
    final mode = _modeFromString(box.get(_kThemeKey) as String?);
    final onboarded = (box.get(_kOnboardedKey) as bool?) ?? false;
    emit(state.copyWith(language: lang, themeMode: mode, onboarded: onboarded));
  }

  Future<void> setLanguage(AppLanguage lang) async {
    final box = await Hive.openBox(_kSettingsBox);
    await box.put(_kLangKey, lang.code);
    emit(state.copyWith(language: lang));
  }

  Future<void> setThemeMode(ThemeMode mode) async {
    final box = await Hive.openBox(_kSettingsBox);
    await box.put(_kThemeKey, _modeToString(mode));
    emit(state.copyWith(themeMode: mode));
  }

  Future<void> markOnboarded() async {
    final box = await Hive.openBox(_kSettingsBox);
    await box.put(_kOnboardedKey, true);
    emit(state.copyWith(onboarded: true));
  }

  static ThemeMode _modeFromString(String? raw) => switch (raw) {
        'light' => ThemeMode.light,
        'dark' => ThemeMode.dark,
        _ => ThemeMode.system,
      };

  static String _modeToString(ThemeMode mode) => switch (mode) {
        ThemeMode.light => 'light',
        ThemeMode.dark => 'dark',
        _ => 'system',
      };
}
