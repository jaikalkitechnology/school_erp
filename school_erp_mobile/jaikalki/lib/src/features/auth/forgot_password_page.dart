import 'package:flutter/material.dart';

import '../../api/auth_repository.dart';
import '../../core/service_locator.dart';
import '../../theme/brand.dart';

/// Two-step "Forgot password" flow:
///   1. Identifier + subdomain → POST /v1/auth/forgot-password.
///      Server queues a 6-digit OTP and (in dev) echoes it back so the
///      mobile flow remains testable without a real SMS gateway.
///   2. OTP + new password   → POST /v1/auth/reset-password.
///      On success: pop back to login with a success snackbar.
class ForgotPasswordPage extends StatefulWidget {
  const ForgotPasswordPage({
    super.key,
    this.initialIdentifier,
    this.initialSubdomain,
  });

  final String? initialIdentifier;
  final String? initialSubdomain;

  @override
  State<ForgotPasswordPage> createState() => _ForgotPasswordPageState();
}

enum _Step { requestOtp, enterOtp }

class _ForgotPasswordPageState extends State<ForgotPasswordPage> {
  late final TextEditingController _identifier;
  late final TextEditingController _subdomain;
  final _otp = TextEditingController();
  final _newPassword = TextEditingController();
  final _confirmPassword = TextEditingController();

  _Step _step = _Step.requestOtp;
  bool _busy = false;
  String? _error;
  String? _hint;
  String? _devOtp;
  String _channel = 'sms';
  int _ttlMin = 10;

  @override
  void initState() {
    super.initState();
    _identifier = TextEditingController(text: widget.initialIdentifier ?? '');
    _subdomain =
        TextEditingController(text: widget.initialSubdomain ?? 'demo');
  }

  @override
  void dispose() {
    _identifier.dispose();
    _subdomain.dispose();
    _otp.dispose();
    _newPassword.dispose();
    _confirmPassword.dispose();
    super.dispose();
  }

  Future<void> _requestOtp() async {
    if (_identifier.text.trim().isEmpty) {
      setState(() => _error = 'Enter your email or mobile number.');
      return;
    }
    if (_subdomain.text.trim().isEmpty) {
      setState(() => _error = 'Enter the school subdomain.');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
      _hint = null;
      _devOtp = null;
    });
    try {
      final r = await locator<AuthRepository>().requestPasswordResetOtp(
        identifier: _identifier.text,
        subdomain: _subdomain.text,
      );
      setState(() {
        _step = _Step.enterOtp;
        _channel = r.channel;
        _ttlMin = r.expiresInMinutes;
        _devOtp = r.devOtp;
        _hint = r.channel == 'email'
            ? 'A 6-digit code was sent to your email. It expires in $_ttlMin minutes.'
            : 'A 6-digit code was sent by SMS. It expires in $_ttlMin minutes.';
      });
    } catch (e) {
      setState(() => _error = e is AuthException ? e.message : '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _submit() async {
    final code = _otp.text.trim();
    if (code.length < 4) {
      setState(() => _error = 'Enter the 6-digit code from the SMS / email.');
      return;
    }
    if (_newPassword.text.length < 6) {
      setState(() => _error = 'New password must be at least 6 characters.');
      return;
    }
    if (_newPassword.text != _confirmPassword.text) {
      setState(() => _error = 'Passwords do not match.');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await locator<AuthRepository>().resetPasswordWithOtp(
        identifier: _identifier.text,
        subdomain: _subdomain.text,
        otp: code,
        newPassword: _newPassword.text,
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Password updated. Sign in with the new password.')),
      );
      Navigator.of(context).pop();
    } catch (e) {
      setState(() => _error = e is AuthException ? e.message : '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return Scaffold(
      appBar: AppBar(title: const Text('Forgot password')),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                _step == _Step.requestOtp
                    ? 'Reset your password'
                    : 'Enter the verification code',
                style: t.headlineMedium,
              ),
              const SizedBox(height: 6),
              Text(
                _step == _Step.requestOtp
                    ? 'We will send a 6-digit code to your registered email or mobile number.'
                    : (_hint ?? 'Enter the code from your SMS / email.'),
                style: t.bodyMedium,
              ),
              const SizedBox(height: 20),
              if (_step == _Step.requestOtp) ..._requestForm() else ..._verifyForm(),
              if (_error != null) ...[
                const SizedBox(height: 14),
                Text(
                  _error!,
                  style: t.bodyMedium?.copyWith(color: const Color(0xFFDC2626)),
                ),
              ],
              if (_devOtp != null) ...[
                const SizedBox(height: 14),
                Container(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 12, vertical: 10),
                  decoration: BoxDecoration(
                    color: JaikalkiBrand.marigoldPale,
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: JaikalkiBrand.marigold),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.bug_report_outlined,
                          color: JaikalkiBrand.indigoDark),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          'Dev OTP: $_devOtp\n'
                          'Echoed because the server is non-production. '
                          'In production this stays out of the response.',
                          style: const TextStyle(
                            fontSize: 12,
                            color: JaikalkiBrand.indigoDark,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
              const SizedBox(height: 24),
              FilledButton(
                onPressed: _busy
                    ? null
                    : (_step == _Step.requestOtp ? _requestOtp : _submit),
                child: Text(
                  _busy
                      ? 'Working…'
                      : (_step == _Step.requestOtp ? 'Send code' : 'Reset password'),
                ),
              ),
              if (_step == _Step.enterOtp) ...[
                const SizedBox(height: 8),
                TextButton(
                  onPressed: _busy ? null : _requestOtp,
                  child: const Text('Resend code'),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  List<Widget> _requestForm() => [
        TextField(
          controller: _subdomain,
          decoration: const InputDecoration(
            labelText: 'School subdomain',
            prefixIcon: Icon(Icons.business_outlined),
          ),
        ),
        const SizedBox(height: 14),
        TextField(
          controller: _identifier,
          keyboardType: TextInputType.emailAddress,
          decoration: const InputDecoration(
            labelText: 'Email or mobile',
            prefixIcon: Icon(Icons.person_outline),
          ),
        ),
      ];

  List<Widget> _verifyForm() => [
        TextField(
          controller: _otp,
          keyboardType: TextInputType.number,
          maxLength: 6,
          decoration: const InputDecoration(
            labelText: 'Verification code',
            prefixIcon: Icon(Icons.dialpad_outlined),
            counterText: '',
          ),
        ),
        const SizedBox(height: 14),
        TextField(
          controller: _newPassword,
          obscureText: true,
          decoration: const InputDecoration(
            labelText: 'New password',
            prefixIcon: Icon(Icons.lock_outline),
          ),
        ),
        const SizedBox(height: 14),
        TextField(
          controller: _confirmPassword,
          obscureText: true,
          decoration: const InputDecoration(
            labelText: 'Confirm new password',
            prefixIcon: Icon(Icons.lock_reset_outlined),
          ),
        ),
      ];
}
