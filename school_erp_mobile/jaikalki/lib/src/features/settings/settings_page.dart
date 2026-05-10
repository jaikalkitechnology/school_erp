import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../core/auth_cubit.dart';
import '../../core/service_locator.dart';
import '../../core/settings_cubit.dart';
import '../../i18n/strings.dart';
import '../../theme/brand.dart';

class SettingsPage extends StatelessWidget {
  const SettingsPage({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<SettingsCubit, SettingsState>(
      builder: (context, state) {
        final s = state.strings;
        final t = Theme.of(context).textTheme;
        return ListView(
          padding: const EdgeInsets.all(20),
          children: [
            _Section(
              title: s.language,
              child: Wrap(
                spacing: 8,
                children: AppLanguage.values.map((lang) {
                  final selected = state.language == lang;
                  return ChoiceChip(
                    label: Text(lang.label),
                    selected: selected,
                    onSelected: (_) => context.read<SettingsCubit>().setLanguage(lang),
                    selectedColor: JaikalkiBrand.saffron,
                    labelStyle: TextStyle(
                      color: selected
                          ? JaikalkiBrand.warmWhite
                          : Theme.of(context).colorScheme.onSurface,
                    ),
                  );
                }).toList(),
              ),
            ),
            const SizedBox(height: 16),
            _Section(
              title: s.appearance,
              child: Wrap(
                spacing: 8,
                children: [
                  _ThemeChoice(label: s.themeSystem, mode: ThemeMode.system),
                  _ThemeChoice(label: s.themeLight, mode: ThemeMode.light),
                  _ThemeChoice(label: s.themeDark, mode: ThemeMode.dark),
                ],
              ),
            ),
            const SizedBox(height: 24),
            FilledButton(
              onPressed: () => locator<AuthCubit>().logout(),
              style: FilledButton.styleFrom(
                backgroundColor: Theme.of(context).colorScheme.error,
              ),
              child: Text(s.signOut),
            ),
            const SizedBox(height: 24),
            Text(s.aboutLine, style: t.bodyMedium),
          ],
        );
      },
    );
  }
}

class _Section extends StatelessWidget {
  const _Section({required this.title, required this.child});
  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Theme.of(context).colorScheme.outline),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title.toUpperCase(),
              style: t.labelSmall?.copyWith(color: JaikalkiBrand.saffronDark)),
          const SizedBox(height: 12),
          child,
        ],
      ),
    );
  }
}

class _ThemeChoice extends StatelessWidget {
  const _ThemeChoice({required this.label, required this.mode});
  final String label;
  final ThemeMode mode;

  @override
  Widget build(BuildContext context) {
    final selected = context.watch<SettingsCubit>().state.themeMode == mode;
    return ChoiceChip(
      label: Text(label),
      selected: selected,
      onSelected: (_) => context.read<SettingsCubit>().setThemeMode(mode),
      selectedColor: JaikalkiBrand.teal,
      labelStyle: TextStyle(
        color: selected
            ? JaikalkiBrand.warmWhite
            : Theme.of(context).colorScheme.onSurface,
      ),
    );
  }
}
