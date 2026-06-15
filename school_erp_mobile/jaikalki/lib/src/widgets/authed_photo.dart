import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';

import '../api/api_client.dart';
import '../core/service_locator.dart';

/// Authed photo renderer for `/v1/uploads/{path}`.
///
/// A plain Image.network can't hit our uploads endpoint — it lacks the
/// bearer + X-Tenant-Subdomain headers that the Dio interceptor adds
/// automatically. So we go through Dio, get raw bytes, and render via
/// Image.memory.
///
/// Bytes are cached in a single in-memory map keyed by the relative
/// upload path, so the same photo doesn't get re-fetched every time
/// the widget rebuilds (or every time we scroll past it in a list).
/// The cache is process-global on purpose — uploads are tenant-scoped
/// at the server, and a different tenant's user wouldn't have access
/// to anyone else's paths anyway.
class AuthedPhoto extends StatefulWidget {
  const AuthedPhoto({
    super.key,
    required this.path,
    required this.placeholder,
    this.fit = BoxFit.cover,
  });

  /// Relative path returned by POST /v1/uploads (e.g.
  /// "tenant_1/students/photos/abc.jpg"). When null/empty we just
  /// render [placeholder] forever.
  final String? path;
  final Widget placeholder;
  final BoxFit fit;

  static final Map<String, Uint8List> _cache = {};
  static final Map<String, Future<Uint8List?>> _inflight = {};

  static Future<Uint8List?> _fetch(String path) async {
    final cached = _cache[path];
    if (cached != null) return cached;
    final pending = _inflight[path];
    if (pending != null) return pending;
    final api = locator<ApiClient>();
    final f = (() async {
      try {
        final res = await api.dio.get<List<int>>(
          '/v1/uploads/$path',
          options: Options(responseType: ResponseType.bytes),
        );
        final bytes = Uint8List.fromList(res.data ?? const []);
        _cache[path] = bytes;
        return bytes;
      } on DioException {
        return null;
      } finally {
        _inflight.remove(path);
      }
    })();
    _inflight[path] = f;
    return f;
  }

  @override
  State<AuthedPhoto> createState() => _AuthedPhotoState();
}

class _AuthedPhotoState extends State<AuthedPhoto> {
  Uint8List? _bytes;
  String? _loadedFor;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void didUpdateWidget(covariant AuthedPhoto oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.path != widget.path) _load();
  }

  Future<void> _load() async {
    final p = widget.path;
    if (p == null || p.isEmpty) {
      setState(() {
        _bytes = null;
        _loadedFor = null;
      });
      return;
    }
    if (_loadedFor == p) return;
    _loadedFor = p;
    final cached = AuthedPhoto._cache[p];
    if (cached != null) {
      setState(() => _bytes = cached);
      return;
    }
    final bytes = await AuthedPhoto._fetch(p);
    if (!mounted || _loadedFor != p) return;
    setState(() => _bytes = bytes);
  }

  @override
  Widget build(BuildContext context) {
    if (_bytes == null) return widget.placeholder;
    return Image.memory(
      _bytes!,
      fit: widget.fit,
      gaplessPlayback: true,
      errorBuilder: (_, __, ___) => widget.placeholder,
    );
  }
}
