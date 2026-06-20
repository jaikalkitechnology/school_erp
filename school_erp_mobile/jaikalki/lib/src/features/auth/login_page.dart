import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth_cubit.dart';
import '../../core/service_locator.dart';
import '../../theme/brand.dart';
import 'forgot_password_page.dart';

class LoginPage extends StatefulWidget {
  const LoginPage({super.key});

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final _formKey = GlobalKey<FormState>();
  final _identifier = TextEditingController();
  final _password = TextEditingController();
  final _subdomain = TextEditingController(text: 'demo');

  @override
  void dispose() {
    _identifier.dispose();
    _password.dispose();
    _subdomain.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!(_formKey.currentState?.validate() ?? false)) return;
    final cubit = locator<AuthCubit>();
    await cubit.login(
      identifier: _identifier.text,
      password: _password.text,
      subdomain: _subdomain.text,
    );
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
                    const SizedBox(height: 20),
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
                            onPressed: busy ? null : _submit,
                            child: Text(busy ? 'Signing in…' : 'Continue'),
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
}
