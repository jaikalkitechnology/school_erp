import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../theme/brand.dart';

/// Phase 0 stub. Phase 2 wires real auth + tenant resolution + role routing.
class LoginPage extends StatefulWidget {
  const LoginPage({super.key});

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final _formKey = GlobalKey<FormState>();
  final _identifier = TextEditingController();
  final _password = TextEditingController();
  bool _busy = false;

  @override
  void dispose() {
    _identifier.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!(_formKey.currentState?.validate() ?? false)) return;
    setState(() => _busy = true);
    await Future<void>.delayed(const Duration(milliseconds: 250));
    if (!mounted) return;
    context.go('/dashboard');
  }

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
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
              Text('Use your school-issued credentials.', style: t.bodyMedium),
              const SizedBox(height: 20),
              Form(
                key: _formKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
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
                    const SizedBox(height: 22),
                    FilledButton(
                      onPressed: _busy ? null : _submit,
                      child: Text(_busy ? 'Signing in…' : 'Continue'),
                    ),
                    const SizedBox(height: 12),
                    Center(
                      child: Text(
                        'Phase 0 stub · real auth lands in Phase 2',
                        style: t.bodyMedium?.copyWith(color: JaikalkiBrand.textSecondary),
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
  }
}
