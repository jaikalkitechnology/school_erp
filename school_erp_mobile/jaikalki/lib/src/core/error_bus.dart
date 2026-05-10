import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';

/// Pipes Dio errors to a global Stream so any widget can show them as
/// snackbars without each call site re-implementing error handling.
class ErrorBus {
  ErrorBus._();
  static final ErrorBus instance = ErrorBus._();

  final _controller = StreamController<String>.broadcast();
  Stream<String> get stream => _controller.stream;

  void emit(String message) {
    if (!_controller.isClosed) _controller.add(message);
  }
}

class ErrorInterceptor extends Interceptor {
  ErrorInterceptor({required this.fallback});
  final String fallback;

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    final message = _readableMessage(err) ?? fallback;
    if (err.response?.statusCode == 401) {
      // Auth handler shows its own state; don't double-snackbar.
    } else {
      ErrorBus.instance.emit(message);
    }
    handler.next(err);
  }

  String? _readableMessage(DioException err) {
    final data = err.response?.data;
    if (data is Map && data['detail'] is String) return data['detail'] as String;
    if (err.type == DioExceptionType.connectionTimeout ||
        err.type == DioExceptionType.connectionError) {
      return null; // caller's fallback already covers this
    }
    return err.message;
  }
}

/// Drop-in widget to surface ErrorBus messages as snackbars in any subtree.
class GlobalErrorListener extends StatefulWidget {
  const GlobalErrorListener({super.key, required this.child});
  final Widget child;

  @override
  State<GlobalErrorListener> createState() => _GlobalErrorListenerState();
}

class _GlobalErrorListenerState extends State<GlobalErrorListener> {
  late final StreamSubscription<String> _sub;

  @override
  void initState() {
    super.initState();
    _sub = ErrorBus.instance.stream.listen((message) {
      final messenger = ScaffoldMessenger.maybeOf(context);
      messenger?.showSnackBar(
        SnackBar(content: Text(message), behavior: SnackBarBehavior.floating),
      );
    });
  }

  @override
  void dispose() {
    _sub.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => widget.child;
}
