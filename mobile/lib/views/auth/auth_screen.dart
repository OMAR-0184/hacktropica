/// Authentication screen — Login / Sign Up tabbed interface.
library;

import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../config/theme.dart';
import '../../viewmodels/auth_viewmodel.dart';
import '../../widgets/error_banner.dart';
import '../../widgets/staggered_list.dart';

class AuthScreen extends ConsumerStatefulWidget {
  const AuthScreen({super.key});

  @override
  ConsumerState<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends ConsumerState<AuthScreen>
    with SingleTickerProviderStateMixin {
  late final TabController _tabCtrl;
  final _loginEmail = TextEditingController();
  final _loginPassword = TextEditingController();
  final _signupEmail = TextEditingController();
  final _signupPassword = TextEditingController();
  final _signupUsername = TextEditingController();
  bool _obscureLogin = true;
  bool _obscureSignup = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _tabCtrl = TabController(length: 2, vsync: this);
  }

  @override
  void dispose() {
    _tabCtrl.dispose();
    _loginEmail.dispose();
    _loginPassword.dispose();
    _signupEmail.dispose();
    _signupPassword.dispose();
    _signupUsername.dispose();
    super.dispose();
  }

  Future<void> _handleLogin() async {
    setState(() => _error = null);
    await ref.read(authViewModelProvider.notifier).login(
          _loginEmail.text.trim(),
          _loginPassword.text,
        );
    if (!mounted) return;
    final state = ref.read(authViewModelProvider);
    if (state.hasError) {
      setState(() => _error = AuthViewModel.errorMessage(state.error!));
    } else if (state.value == true) {
      context.go('/dashboard');
    }
  }

  Future<void> _handleSignup() async {
    setState(() => _error = null);
    await ref.read(authViewModelProvider.notifier).register(
          _signupEmail.text.trim(),
          _signupPassword.text,
          username: _signupUsername.text.trim().isEmpty
              ? null
              : _signupUsername.text.trim(),
        );
    if (!mounted) return;
    final state = ref.read(authViewModelProvider);
    if (state.hasError) {
      setState(() => _error = AuthViewModel.errorMessage(state.error!));
    } else if (state.value == true) {
      context.go('/dashboard');
    }
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authViewModelProvider);
    final isLoading = authState.isLoading;

    return Scaffold(
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 420),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                // ── Brand ────────────────────────────
                StaggeredFadeSlide(
                  index: 0,
                  slideOffset: 16,
                  child: const _BrandHeader(),
                ),
                const SizedBox(height: 32),

                // ── Card ─────────────────────────────
                StaggeredFadeSlide(
                  index: 1,
                  slideOffset: 20,
                  child: Container(
                    decoration: BoxDecoration(
                      color: AppColors.surface.withAlpha(235),
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(color: AppColors.border),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withAlpha(100),
                          blurRadius: 40,
                          offset: const Offset(0, 16),
                        ),
                      ],
                    ),
                    child: Padding(
                      padding: const EdgeInsets.all(24),
                      child: Column(
                        children: [
                          // Tab bar
                          Container(
                            decoration: BoxDecoration(
                              color: AppColors.surface2,
                              borderRadius: BorderRadius.circular(12),
                              border: Border.all(color: AppColors.border),
                            ),
                            padding: const EdgeInsets.all(4),
                            child: TabBar(
                              controller: _tabCtrl,
                              indicator: BoxDecoration(
                                color: AppColors.primary500.withAlpha(30),
                                borderRadius: BorderRadius.circular(10),
                                border: Border.all(
                                    color: AppColors.primary500.withAlpha(60)),
                              ),
                              indicatorSize: TabBarIndicatorSize.tab,
                              dividerHeight: 0,
                              labelColor: Colors.white,
                              unselectedLabelColor: AppColors.textMuted,
                              labelStyle: const TextStyle(
                                  fontSize: 14, fontWeight: FontWeight.w600),
                              tabs: const [
                                Tab(text: 'Sign In'),
                                Tab(text: 'Sign Up'),
                              ],
                            ),
                          ),
                          const SizedBox(height: 20),

                          // Error
                          if (_error != null) ...[
                            ErrorBanner(message: _error!),
                            const SizedBox(height: 16),
                          ],

                          // Tab views
                          SizedBox(
                            height: _tabCtrl.index == 1 ? 340 : 260,
                            child: TabBarView(
                              controller: _tabCtrl,
                              children: [
                                _buildLoginForm(isLoading),
                                _buildSignupForm(isLoading),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildLoginForm(bool isLoading) {
    return Column(
      children: [
        TextField(
          controller: _loginEmail,
          decoration: const InputDecoration(
            labelText: 'EMAIL',
            hintText: 'you@example.com',
            prefixIcon: Icon(Icons.email_outlined, size: 18),
          ),
          keyboardType: TextInputType.emailAddress,
          enabled: !isLoading,
        ),
        const SizedBox(height: 14),
        TextField(
          controller: _loginPassword,
          decoration: InputDecoration(
            labelText: 'PASSWORD',
            hintText: '••••••••••••',
            prefixIcon: const Icon(Icons.lock_outline, size: 18),
            suffixIcon: IconButton(
              icon: Icon(
                _obscureLogin ? Icons.visibility_off : Icons.visibility,
                size: 18,
                color: AppColors.textMuted,
              ),
              onPressed: () =>
                  setState(() => _obscureLogin = !_obscureLogin),
            ),
          ),
          obscureText: _obscureLogin,
          enabled: !isLoading,
        ),
        const SizedBox(height: 24),
        SizedBox(
          width: double.infinity,
          child: ElevatedButton(
            onPressed: isLoading ? null : _handleLogin,
            child: isLoading
                ? const SizedBox(
                    height: 18,
                    width: 18,
                    child: CircularProgressIndicator(
                        strokeWidth: 2, color: Colors.white),
                  )
                : const Text('Sign In'),
          ),
        ),
      ],
    );
  }

  Widget _buildSignupForm(bool isLoading) {
    return SingleChildScrollView(
      child: Column(
        children: [
          TextField(
            controller: _signupEmail,
            decoration: const InputDecoration(
              labelText: 'EMAIL',
              hintText: 'you@example.com',
              prefixIcon: Icon(Icons.email_outlined, size: 18),
            ),
            keyboardType: TextInputType.emailAddress,
            enabled: !isLoading,
          ),
          const SizedBox(height: 14),
          TextField(
            controller: _signupUsername,
            decoration: const InputDecoration(
              labelText: 'USERNAME (OPTIONAL)',
              hintText: 'anon_node_∞',
              prefixIcon: Icon(Icons.person_outline, size: 18),
            ),
            enabled: !isLoading,
          ),
          const SizedBox(height: 14),
          TextField(
            controller: _signupPassword,
            decoration: InputDecoration(
              labelText: 'PASSWORD',
              hintText: 'Use a strong passphrase',
              prefixIcon: const Icon(Icons.lock_outline, size: 18),
              suffixIcon: IconButton(
                icon: Icon(
                  _obscureSignup ? Icons.visibility_off : Icons.visibility,
                  size: 18,
                  color: AppColors.textMuted,
                ),
                onPressed: () =>
                    setState(() => _obscureSignup = !_obscureSignup),
              ),
            ),
            obscureText: _obscureSignup,
            enabled: !isLoading,
          ),
          const SizedBox(height: 24),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: isLoading ? null : _handleSignup,
              child: isLoading
                  ? const SizedBox(
                      height: 18,
                      width: 18,
                      child: CircularProgressIndicator(
                          strokeWidth: 2, color: Colors.white),
                    )
                  : const Text('Create Account'),
            ),
          ),
        ],
      ),
    );
  }
}

/// Brand header with animated gradient ring around the icon.
class _BrandHeader extends StatefulWidget {
  const _BrandHeader();

  @override
  State<_BrandHeader> createState() => _BrandHeaderState();
}

class _BrandHeaderState extends State<_BrandHeader>
    with SingleTickerProviderStateMixin {
  late final AnimationController _rotationCtrl;

  @override
  void initState() {
    super.initState();
    _rotationCtrl = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 6),
    )..repeat();
  }

  @override
  void dispose() {
    _rotationCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final reduceMotion = MediaQuery.of(context).disableAnimations;

    return Column(
      children: [
        SizedBox(
          width: 68,
          height: 68,
          child: Stack(
            alignment: Alignment.center,
            children: [
              // Animated gradient ring
              if (!reduceMotion)
                AnimatedBuilder(
                  animation: _rotationCtrl,
                  builder: (context, child) => Transform.rotate(
                    angle: _rotationCtrl.value * 2 * math.pi,
                    child: child,
                  ),
                  child: Container(
                    width: 68,
                    height: 68,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: SweepGradient(
                        colors: [
                          AppColors.primary500.withAlpha(80),
                          AppColors.accent500.withAlpha(80),
                          AppColors.primary500.withAlpha(10),
                          AppColors.primary500.withAlpha(80),
                        ],
                      ),
                    ),
                  ),
                )
              else
                Container(
                  width: 68,
                  height: 68,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    border: Border.all(
                        color: AppColors.primary500.withAlpha(60)),
                  ),
                ),

              // Icon container
              Container(
                width: 52,
                height: 52,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(16),
                  color: AppColors.background,
                  boxShadow: [
                    BoxShadow(
                      color: AppColors.primary500.withAlpha(30),
                      blurRadius: 20,
                    ),
                  ],
                ),
                child: const Icon(
                  Icons.hub_outlined,
                  color: AppColors.primary500,
                  size: 28,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        const Text(
          'Cognimap',
          style: TextStyle(
            fontSize: 22,
            fontWeight: FontWeight.w700,
            color: AppColors.textPrimary,
          ),
        ),
        const SizedBox(height: 4),
        const Text(
          'Map your learning. Master your path.',
          style: TextStyle(
            fontSize: 13,
            color: AppColors.textMuted,
          ),
        ),
      ],
    );
  }
}
