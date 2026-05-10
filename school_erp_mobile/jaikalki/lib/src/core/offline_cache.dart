import 'dart:convert';

import 'package:hive/hive.dart';

const _box = 'jaikalki.cache';

/// Tiny JSON-blob cache backed by Hive. Used for parent dashboard payloads
/// so the home screen renders something even without network.
class OfflineCache {
  Future<Box> _open() => Hive.openBox(_box);

  Future<void> put(String key, Object value) async {
    final box = await _open();
    await box.put(key, jsonEncode(value));
  }

  Future<dynamic> get(String key) async {
    final box = await _open();
    final raw = box.get(key);
    if (raw is String) return jsonDecode(raw);
    return null;
  }

  Future<void> clear() async {
    final box = await _open();
    await box.clear();
  }
}
