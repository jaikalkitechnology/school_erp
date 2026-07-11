import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';
import 'package:google_sign_in/google_sign_in.dart';

import '../../api/auth_repository.dart';
import '../../core/auth_cubit.dart';
import '../../core/service_locator.dart';
import '../../theme/brand.dart';
import 'forgot_password_page.dart';

// Web OAuth client ID — passed as serverClientId so the Google ID
// token's audience is the web client, which our backend accepts.
// Override at build time with:
//   flutter run --dart-define=GOOGLE_SERVER_CLIENT_ID=...
const _googleServerClientId = String.fromEnvironment(
  'GOOGLE_SERVER_CLIENT_ID',
  defaultValue:
      '158812707380-i6f00ih0imbt2dh75s9dr849481joqap.apps.googleusercontent.com',
);

/// Modes available on the sign-in screen. Both share the same identifier
/// + subdomain block; only the credential changes.
enum _SignInMode { password, otp }

class LoginPage extends StatefulWidget {
  const LoginPage({super.key});

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final _formKey = GlobalKey<FormState>();
  final _identifier = TextEditingController();
  final _password = TextEditingController();
  final _otp = TextEditingController();
  final _subdomain = TextEditingController(text: 'demo');

  _SignInMode _mode = _SignInMode.password;

  // OTP-mode local state — separate from AuthState because requesting
  // the OTP doesn't touch the AuthCubit (it doesn't authenticate yet).
  bool _otpRequested = false;
  bool _requestingOtp = false;
  String? _otpHint;
  String? _devOtp;
  String? _otpError;

  @override
  void dispose() {
    _identifier.dispose();
    _password.dispose();
    _otp.dispose();
    _subdomain.dispose();
    super.dispose();
  }

  Future<void> _submitPassword() async {
    if (!(_formKey.currentState?.validate() ?? false)) return;
    await locator<AuthCubit>().login(
      identifier: _identifier.text,
      password: _password.text,
      subdomain: _subdomain.text,
    );
  }

  bool _googleBusy = false;

  Future<void> _signInWithGoogle() async {
    final subdomain = _subdomain.text.trim();
    if (subdomain.isEmpty) {
      setState(() => _otpError =
          'Enter your school subdomain first, then continue with Google.');
      return;
    }
    setState(() => _googleBusy = true);
    try {
      final gsi = GoogleSignIn(
        serverClientId: _googleServerClientId,
        scopes: const ['email', 'profile'],
      );
      // Sign out first so the account chooser always shows — avoids a
      // silent re-auth as a stale account.
      await gsi.signOut();
      final account = await gsi.signIn();
      if (account == null) {
        // User cancelled the chooser.
        setState(() => _googleBusy = false);
        return;
      }
      final auth = await account.authentication;
      final idToken = auth.idToken;
      if (idToken == null || idToken.isEmpty) {
        setState(() {
          _googleBusy = false;
          _otpError = 'Google did not return a sign-in token. Try again.';
        });
        return;
      }
      await locator<AuthCubit>().loginWithGoogle(
        idToken: idToken,
        subdomain: subdomain,
      );
    } catch (e) {
      setState(() => _otpError = 'Google sign-in failed. Please try again.');
    } finally {
      if (mounted) setState(() => _googleBusy = false);
    }
  }

  Future<void> _requestOtp() async {
    if (_identifier.text.trim().isEmpty || _subdomain.text.trim().isEmpty) {
      setState(() =>
          _otpError = 'Enter the school subdomain and your email or mobile.');
      return;
    }
    setState(() {
      _requestingOtp = true;
      _otpError = null;
      _devOtp = null;
    });
    try {
      final r = await locator<AuthRepository>().requestLoginOtp(
        identifier: _identifier.text,
        subdomain: _subdomain.text,
      );
      setState(() {
        _otpRequested = true;
        _otpHint = r.channel == 'email'
            ? 'A login code was sent to your email. It expires in ${r.expiresInMinutes} minutes.'
            : 'A login code was sent by SMS. It expires in ${r.expiresInMinutes} minutes.';
        _devOtp = r.devOtp;
      });
    } catch (e) {
      setState(() => _otpError = e is AuthException ? e.message : '$e');
    } finally {
      if (mounted) setState(() => _requestingOtp = false);
    }
  }

  Future<void> _verifyOtp() async {
    if (_otp.text.trim().length < 4) {
      setState(() => _otpError = 'Enter the 6-digit code.');
      return;
    }
    setState(() => _otpError = null);
    await locator<AuthCubit>().loginWithOtp(
      identifier: _identifier.text,
      subdomain: _subdomain.text,
      otp: _otp.text,
    );
  }

  void _switchMode(_SignInMode mode) {
    if (_mode == mode) return;
    setState(() {
      _mode = mode;
      _otpError = null;
      _devOtp = null;
      _otpHint = null;
      _otpRequested = false;
      _otp.clear();
    });
  }

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return BlocProvider.value(
      value: locator<AuthCubit>(),
      child: BlocConsumer<AuthCubit, AuthState>(
        listener: (context, state) {
          if (state is AuthAuthenticated) {
            context.go('/home');
          }
        },
        builder: (context, state) {
          final busy = state is AuthAuthenticating;
          final errorMessage = state is AuthError ? state.message : null;
          return Scaffold(
            body: SafeArea(
              child: SingleChildScrollView(
                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      padding: const EdgeInsets.all(24),
                      decoration: BoxDecoration(
                        gradient: const LinearGradient(
                          colors: [JaikalkiBrand.saffron, JaikalkiBrand.saffronDark],
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                        ),
                        borderRadius: BorderRadius.circular(28),
                      ),
                      width: double.infinity,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('JAIKALKI · MOBILE',
                              style: t.labelSmall?.copyWith(color: JaikalkiBrand.marigoldPale)),
                          const SizedBox(height: 12),
                          Text(
                            'Your school in your pocket.',
                            style: t.displayMedium?.copyWith(color: JaikalkiBrand.warmWhite, height: 1.1),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            'Attendance, fees, homework, transport — one login for parents, teachers, and students.',
                            style: t.bodyMedium?.copyWith(color: JaikalkiBrand.marigoldPale),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 28),
                    Text('Sign in', style: t.headlineMedium),
                    const SizedBox(height: 4),
                    Text(
                      'Demo seed: admin@demo.school / School@123, school = "demo".',
                      style: t.bodyMedium,
                    ),
                    const SizedBox(height: 16),
                    _ModeToggle(
                      mode: _mode,
                      onChanged: busy || _requestingOtp ? null : _switchMode,
                    ),
                    const SizedBox(height: 16),
                    Form(
                      key: _formKey,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          TextFormField(
                            controller: _subdomain,
                            decoration: const InputDecoration(
                              labelText: 'School subdomain',
                              prefixIcon: Icon(Icons.business_outlined),
                            ),
                            validator: (v) => (v == null || v.trim().isEmpty) ? 'Required' : null,
                          ),
                          const SizedBox(height: 14),
                          TextFormField(
                            controller: _identifier,
                            keyboardType: TextInputType.emailAddress,
                            decoration: const InputDecoration(
                              labelText: 'Email or mobile',
                              prefixIcon: Icon(Icons.person_outline),
                            ),
                            validator: (v) => (v == null || v.trim().isEmpty) ? 'Required' : null,
                          ),
                          const SizedBox(height: 14),
                          if (_mode == _SignInMode.password)
                            ..._passwordFields(t, busy, errorMessage)
                          else
                            ..._otpFields(t, busy, errorMessage),
                          const SizedBox(height: 16),
                          Row(
                            children: [
                              const Expanded(child: Divider()),
                              Padding(
                                padding: const EdgeInsets.symmetric(
                                    horizontal: 10),
                                child: Text(
                                  'OR',
                                  style: t.labelSmall?.copyWith(
                                    color: JaikalkiBrand.textSecondary,
                                  ),
                                ),
                              ),
                              const Expanded(child: Divider()),
                            ],
                          ),
                          const SizedBox(height: 12),
                          OutlinedButton.icon(
                            onPressed: (busy || _googleBusy)
                                ? null
                                : _signInWithGoogle,
                            icon: _googleBusy
                                ? const SizedBox(
                                    width: 16,
                                    height: 16,
                                    child: CircularProgressIndicator(
                                        strokeWidth: 2),
                                  )
                                : const Icon(Icons.login),
                            label: Text(_googleBusy
                                ? 'Signing in…'
                                : 'Continue with Google'),
                            style: OutlinedButton.styleFrom(
                              minimumSize: const Size.fromHeight(48),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          );
        },
      ),
    );
  }

  List<Widget> _passwordFields(
    TextTheme t,
    bool busy,
    String? errorMessage,
  ) {
    return [
      TextFormField(
        controller: _password,
        obscureText: true,
        decoration: const InputDecoration(
          labelText: 'Password',
          prefixIcon: Icon(Icons.lock_outline),
        ),
        validator: (v) => (v == null || v.length < 4) ? 'Required' : null,
      ),
      if (errorMessage != null) ...[
        const SizedBox(height: 16),
        Text(errorMessage,
            style: t.bodyMedium?.copyWith(color: const Color(0xFFDC2626))),
      ],
      const SizedBox(height: 6),
      Align(
        alignment: Alignment.centerRight,
        child: TextButton(
          onPressed: busy
              ? null
              : () => Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (_) => ForgotPasswordPage(
                        initialIdentifier: _identifier.text,
                        initialSubdomain: _subdomain.text,
                      ),
                    ),
                  ),
          child: const Text('Forgot password?'),
        ),
      ),
      const SizedBox(height: 6),
      FilledButton(
        onPressed: busy ? null : _submitPassword,
        child: Text(busy ? 'Signing in…' : 'Continue'),
      ),
    ];
  }

  List<Widget> _otpFields(
    TextTheme t,
    bool busy,
    String? errorMessage,
  ) {
    return [
      if (_otpRequested)
        TextFormField(
          controller: _otp,
          keyboardType: TextInputType.number,
          maxLength: 6,
          decoration: const InputDecoration(
            labelText: 'Login code',
            prefixIcon: Icon(Icons.dialpad_outlined),
            counterText: '',
          ),
        )
      else
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
          decoration: BoxDecoration(
            color: JaikalkiBrand.tealPale.withOpacity(0.4),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: JaikalkiBrand.teal.withOpacity(0.3)),
          ),
          child: const Text(
            'We will send a 6-digit code to your email or mobile on file. '
            'No password needed.',
            style: TextStyle(fontSize: 12, color: JaikalkiBrand.tealDark),
          ),
        ),
      if (_otpHint != null) ...[
        const SizedBox(height: 10),
        Text(_otpHint!, style: t.bodyMedium),
      ],
      if (_devOtp != null) ...[
        const SizedBox(height: 10),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
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
                  'Echoed because the server is non-production.',
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
      if (_otpError != null) ...[
        const SizedBox(height: 12),
        Text(_otpError!,
            style: t.bodyMedium?.copyWith(color: const Color(0xFFDC2626))),
      ],
      if (errorMessage != null) ...[
        const SizedBox(height: 12),
        Text(errorMessage,
            style: t.bodyMedium?.copyWith(color: const Color(0xFFDC2626))),
      ],
      const SizedBox(height: 16),
      if (!_otpRequested)
        FilledButton(
          onPressed: _requestingOtp ? null : _requestOtp,
          child: Text(_requestingOtp ? 'Sending…' : 'Send login code'),
        )
      else ...[
        FilledButton(
          onPressed: busy ? null : _verifyOtp,
          child: Text(busy ? 'Signing in…' : 'Sign in with code'),
        ),
        const SizedBox(height: 4),
        TextButton(
          onPressed: busy || _requestingOtp ? null : _requestOtp,
          child: Text(_requestingOtp ? 'Sending…' : 'Resend code'),
        ),
      ],
    ];
  }
}

class _ModeToggle extends StatelessWidget {
  const _ModeToggle({required this.mode, required this.onChanged});

  final _SignInMode mode;
  final void Function(_SignInMode)? onChanged;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(
        color: JaikalkiBrand.warmWhite,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: JaikalkiBrand.saffronPale),
      ),
      child: Row(
        children: [
          _segment(label: 'Password', value: _SignInMode.password),
          _segment(label: 'OTP', value: _SignInMode.otp),
        ],
      ),
    );
  }

  Widget _segment({required String label, required _SignInMode value}) {
    final selected = mode == value;
    return Expanded(
      child: GestureDetector(
        onTap: onChanged == null ? null : () => onChanged!(value),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 10),
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: selected ? JaikalkiBrand.saffron : Colors.transparent,
            borderRadius: BorderRadius.circular(9),
          ),
          child: Text(
            label,
            style: TextStyle(
              fontWeight: FontWeight.w700,
              color: selected ? Colors.white : JaikalkiBrand.indigoDark,
            ),
          ),
        ),
      ),
    );
  }
}
