import 'package:get_it/get_it.dart';

import '../api/api_client.dart';

final GetIt locator = GetIt.instance;

void registerDependencies() {
  if (!locator.isRegistered<ApiClient>()) {
    locator.registerLazySingleton<ApiClient>(() => ApiClient());
  }
}
