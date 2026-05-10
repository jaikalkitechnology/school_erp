import 'package:get_it/get_it.dart';

import '../api/api_client.dart';
import '../api/auth_repository.dart';
import '../api/parent_repository.dart';
import 'auth_cubit.dart';
import 'children_cubit.dart';
import 'offline_cache.dart';
import 'settings_cubit.dart';

final GetIt locator = GetIt.instance;

void registerDependencies() {
  if (!locator.isRegistered<ApiClient>()) {
    locator.registerLazySingleton<ApiClient>(() => ApiClient());
  }
  if (!locator.isRegistered<OfflineCache>()) {
    locator.registerLazySingleton<OfflineCache>(() => OfflineCache());
  }
  if (!locator.isRegistered<AuthRepository>()) {
    locator.registerLazySingleton<AuthRepository>(() => AuthRepository(locator<ApiClient>()));
  }
  if (!locator.isRegistered<ParentRepository>()) {
    locator.registerLazySingleton<ParentRepository>(() => ParentRepository(locator<ApiClient>()));
  }
  if (!locator.isRegistered<AuthCubit>()) {
    locator.registerLazySingleton<AuthCubit>(() => AuthCubit(locator<AuthRepository>()));
  }
  if (!locator.isRegistered<ChildrenCubit>()) {
    locator.registerLazySingleton<ChildrenCubit>(
      () => ChildrenCubit(locator<ParentRepository>(), cache: locator<OfflineCache>()),
    );
  }
  if (!locator.isRegistered<SettingsCubit>()) {
    locator.registerLazySingleton<SettingsCubit>(() => SettingsCubit());
  }
}
