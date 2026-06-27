// lib/presentation/screens/auth/login_screen.dart
// CHANGED: _onSignIn navigates to HomeScreen and clears the stack

import 'package:flutter/material.dart';
import '../../../../core/constants/app_colors.dart';
import '../../../../core/constants/app_dimensions.dart';
import '../../widgets/common/custom_text_field.dart';
import '../../widgets/common/custom_button.dart';
import '../home/home_screen.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey              = GlobalKey<FormState>();
  final _identifierController = TextEditingController();
  final _passwordController   = TextEditingController();
  bool _isLoading = false;

  @override
  void dispose() {
    _identifierController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  void _onSignIn() {
    if (!(_formKey.currentState?.validate() ?? false)) return;

    setState(() => _isLoading = true);

    // TODO Step 2: replace Future.delayed with real auth repository call
    Future.delayed(const Duration(seconds: 2), () {
      if (!mounted) return;
      // ── Navigate to Home and remove ALL previous routes ──────────────────
      // pushAndRemoveUntil ensures the user cannot press Back to get to Login
      Navigator.pushAndRemoveUntil(
        context,
        MaterialPageRoute(builder: (_) => const HomeScreen()),
        (route) => false, // remove everything below
      );
    });
  }

  void _onBiometric() {
    // TODO Step 3: hook up biometric auth service
  }

  void _onQrPair() {
    // TODO Step 2: navigate to QR pairing screen
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.scaffoldBg,
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(
            horizontal: AppDimensions.paddingLG,
          ),
          child: Form(
            key: _formKey,
            child: Column(
              children: [
                const SizedBox(height: AppDimensions.paddingXXL),

                // ── Logo ──────────────────────────────────────────
                _ShieldLogo(),

                const SizedBox(height: AppDimensions.paddingXL),

                // ── App Name ──────────────────────────────────────
                const Text(
                  'SMARTGUARD',
                  style: TextStyle(
                    color: AppColors.textPrimary,
                    fontSize: 28,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 3,
                  ),
                ),
                const SizedBox(height: AppDimensions.paddingSM),
                const Text(
                  'VEHICLE SECURITY SYSTEM',
                  style: TextStyle(
                    color: AppColors.textSecondary,
                    fontSize: 12,
                    fontWeight: FontWeight.w400,
                    letterSpacing: 2.5,
                  ),
                ),

                const SizedBox(height: AppDimensions.paddingXXL),

                // ── Phone / Email Field ───────────────────────────
                CustomTextField(
                  label: 'PHONE OR EMAIL',
                  hint: '+1 (555) 000-0000',
                  controller: _identifierController,
                  keyboardType: TextInputType.emailAddress,
                  validator: (v) =>
                      (v == null || v.isEmpty) ? 'Required' : null,
                ),

                const SizedBox(height: AppDimensions.paddingLG),

                // ── Password Field ────────────────────────────────
                CustomTextField(
                  label: 'PASSWORD',
                  hint: '••••••••••',
                  isPassword: true,
                  controller: _passwordController,
                  validator: (v) =>
                      (v == null || v.length < 6) ? 'Min 6 chars' : null,
                ),

                const SizedBox(height: AppDimensions.paddingXL),

                // ── Sign In Button ────────────────────────────────
                CustomButton(
                  label: 'SIGN IN',
                  onPressed: _onSignIn,
                  isLoading: _isLoading,
                ),

                const SizedBox(height: AppDimensions.paddingLG),

                // ── Divider ───────────────────────────────────────
                _OrDivider(),

                const SizedBox(height: AppDimensions.paddingLG),

                // ── Biometric Button ──────────────────────────────
                CustomButton(
                  label: 'BIOMETRIC LOGIN',
                  onPressed: _onBiometric,
                  variant: ButtonVariant.outline,
                  prefixIcon: Icons.fingerprint,
                ),

                const SizedBox(height: AppDimensions.paddingXL),

                // ── QR Pair Link ──────────────────────────────────
                GestureDetector(
                  onTap: _onQrPair,
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: const [
                      Icon(Icons.wifi_tethering,
                          color: AppColors.textSecondary, size: 16),
                      SizedBox(width: AppDimensions.paddingSM),
                      Text(
                        'Pair a new device via QR code',
                        style: TextStyle(
                            color: AppColors.textSecondary, fontSize: 13),
                      ),
                    ],
                  ),
                ),

                const SizedBox(height: AppDimensions.paddingXL),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

// ── Private sub-widgets ───────────────────────────────────────────────────────

class _ShieldLogo extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      width: AppDimensions.logoSize,
      height: AppDimensions.logoSize,
      decoration: BoxDecoration(
        color: AppColors.cardBg,
        borderRadius: BorderRadius.circular(AppDimensions.radiusXXL),
      ),
      child: const Icon(
        Icons.shield_outlined,
        color: AppColors.shieldBlue,
        size: AppDimensions.iconSize,
      ),
    );
  }
}

class _OrDivider extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Row(
      children: const [
        Expanded(child: Divider(color: AppColors.divider)),
        Padding(
          padding: EdgeInsets.symmetric(horizontal: AppDimensions.paddingMD),
          child: Text('or',
              style:
                  TextStyle(color: AppColors.textSecondary, fontSize: 13)),
        ),
        Expanded(child: Divider(color: AppColors.divider)),
      ],
    );
  }
}