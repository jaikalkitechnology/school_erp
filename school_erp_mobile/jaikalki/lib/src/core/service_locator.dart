import 'package:get_it/get_it.dart';

import '../api/api_client.dart';
import '../api/auth_repository.dart';
import '../api/messages_repository.dart';
import '../api/parent_repository.dart';
import '../api/teacher_repository.dart';
import 'attendance_cubit.dart';
import 'auth_cubit.dart';
import 'children_cubit.dart';
import 'fees_cubit.dart';
import 'homework_cubit.dart';
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
  if (!locator.isRegistered<TeacherRepository>()) {
    locator.registerLazySingleton<TeacherRepository>(() => TeacherRepository(locator<ApiClient>()));
  }
  if (!locator.isRegistered<MessagesRepository>()) {
    locator.registerLazySingleton<MessagesRepository>(() => MessagesRepository(locator<ApiClient>()));
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
  // ----- P0 parent screens (Phases 9 / 11 / 14) ---------------------------
  if (!locator.isRegistered<AttendanceCubit>()) {
    locator.registerLazySingleton<AttendanceCubit>(
      () => AttendanceCubit(locator<ParentRepository>()),
    );
  }
  if (!locator.isRegistered<FeesCubit>()) {
    locator.registerLazySingleton<FeesCubit>(
      () => FeesCubit(locator<ParentRepository>()),
    );
  }
  if (!locator.isRegistered<HomeworkCubit>()) {
    locator.registerLazySingleton<HomeworkCubit>(
      () => HomeworkCubit(locator<ParentRepository>()),
    );
  }
}
