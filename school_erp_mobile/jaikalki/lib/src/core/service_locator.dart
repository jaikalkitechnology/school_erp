import 'package:get_it/get_it.dart';

import '../api/api_client.dart';
import '../api/auth_repository.dart';
import 'auth_cubit.dart';

final GetIt locator = GetIt.instance;

void registerDependencies() {
  if (!locator.isRegistered<ApiClient>()) {
    locator.registerLazySingleton<ApiClient>(() => ApiClient());
  }
  if (!locator.isRegistered<AuthRepository>()) {
    locator.registerLazySingleton<AuthRepository>(() => AuthRepository(locator<ApiClient>()));
  }
  if (!locator.isRegistered<AuthCubit>()) {
    locator.registerLazySingleton<AuthCubit>(() => AuthCubit(locator<AuthRepository>()));
  }
}
