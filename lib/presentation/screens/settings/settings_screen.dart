// lib/presentation/screens/settings/settings_screen.dart
// CHANGED: removed bottomNavigationBar + _navIndex — nav lives in HomeScreen now

import 'package:flutter/material.dart';
import '../../../core/constants/app_colors.dart';
import '../../../data/models/user_model.dart';
import '../../../data/models/settings_model.dart';
import '../../widgets/settings/profile_card.dart';
import '../../widgets/settings/settings_section.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  // Step 2: replace with provider / auth repository
  final UserModel        _user   = UserModel.mock();
  final DeviceSettings   _device = DeviceSettings.mock();
  final SecuritySettings _sec    = SecuritySettings.mock();
  final AccessSettings   _access = AccessSettings.mock();

  void _onSignOut() {
    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        backgroundColor: AppColors.cardBg,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: const Text('Sign Out',
            style: TextStyle(color: AppColors.textPrimary)),
        content: const Text(
            'Are you sure you want to sign out of SmartGuard?',
            style: TextStyle(color: AppColors.textSecondary)),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel',
                style: TextStyle(color: AppColors.textSecondary)),
          ),
          TextButton(
            onPressed: () {
              Navigator.pop(context);
              // TODO Step 2: clear tokens + navigate to LoginScreen
            },
            child: const Text('Sign Out',
                style: TextStyle(color: AppColors.statusRed)),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: CustomScrollView(
        slivers: [
          const SliverToBoxAdapter(
            child: Padding(
              padding: EdgeInsets.fromLTRB(16, 16, 16, 20),
              child: Text('Settings',
                  style: TextStyle(
                      color: AppColors.textPrimary,
                      fontSize: 26,
                      fontWeight: FontWeight.w800)),
            ),
          ),
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: ProfileCard(user: _user),
            ),
          ),
          const SliverToBoxAdapter(child: SizedBox(height: 28)),

          // ── DEVICE ──────────────────────────────────────────────────────
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: SettingsSection(
                title: 'DEVICE',
                rows: [
                  SettingsSectionData(
                    icon: Icons.storage_rounded,
                    iconColor: AppColors.accentBlue,
                    iconBg: AppColors.iconBlueBg,
                    label: 'Device ID',
                    value: _device.deviceId,
                    hasChevron: true, onTap: () {},
                  ),
                  SettingsSectionData(
                    icon: Icons.wifi_rounded,
                    iconColor: const Color(0xFF22C55E),
                    iconBg: const Color(0xFF052E16),
                    label: 'Network',
                    value: _device.network,
                    hasChevron: true, onTap: () {},
                  ),
                  SettingsSectionData(
                    icon: Icons.podcasts_rounded,
                    iconColor: const Color(0xFFF59E0B),
                    iconBg: const Color(0xFF2D1A00),
                    label: 'Heartbeat',
                    value: _device.heartbeatInterval,
                    hasChevron: false,
                  ),
                  SettingsSectionData(
                    icon: Icons.signal_cellular_alt_rounded,
                    iconColor: AppColors.accentBlue,
                    iconBg: AppColors.iconBlueBg,
                    label: 'Protocol',
                    value: _device.protocol,
                    hasChevron: false,
                  ),
                ],
              ),
            ),
          ),
          const SliverToBoxAdapter(child: SizedBox(height: 24)),

          // ── SECURITY ────────────────────────────────────────────────────
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: SettingsSection(
                title: 'SECURITY',
                rows: [
                  SettingsSectionData(
                    icon: Icons.key_rounded,
                    iconColor: const Color(0xFFEF4444),
                    iconBg: const Color(0xFF2D0A0A),
                    label: 'Auth Method',
                    value: _sec.authMethod,
                    hasChevron: true, onTap: () {},
                  ),
                  SettingsSectionData(
                    icon: Icons.shield_outlined,
                    iconColor: AppColors.accentBlue,
                    iconBg: AppColors.iconBlueBg,
                    label: 'Encryption',
                    value: _sec.encryption,
                    hasChevron: false,
                  ),
                  SettingsSectionData(
                    icon: Icons.timer_outlined,
                    iconColor: const Color(0xFFF59E0B),
                    iconBg: const Color(0xFF2D1A00),
                    label: 'Session Timeout',
                    value: _sec.sessionTimeout,
                    hasChevron: true, onTap: () {},
                  ),
                ],
              ),
            ),
          ),
          const SliverToBoxAdapter(child: SizedBox(height: 24)),

          // ── ACCESS ──────────────────────────────────────────────────────
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: SettingsSection(
                title: 'ACCESS',
                rows: [
                  SettingsSectionData(
                    icon: Icons.group_outlined,
                    iconColor: const Color(0xFF22C55E),
                    iconBg: const Color(0xFF052E16),
                    label: 'Shared Users',
                    value: '${_access.sharedUsersCount} active',
                    hasChevron: true, onTap: () {},
                  ),
                  SettingsSectionData(
                    icon: Icons.show_chart_rounded,
                    iconColor: AppColors.accentBlue,
                    iconBg: AppColors.iconBlueBg,
                    label: 'Activity Log',
                    value: _access.activityLogLabel,
                    hasChevron: true, onTap: () {},
                  ),
                ],
              ),
            ),
          ),
          const SliverToBoxAdapter(child: SizedBox(height: 28)),

          // ── Sign Out ────────────────────────────────────────────────────
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: GestureDetector(
                onTap: _onSignOut,
                child: Container(
                  height: 54,
                  decoration: BoxDecoration(
                    color: AppColors.statusRedBg,
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(
                        color: AppColors.statusRed.withOpacity(0.3), width: 1),
                  ),
                  alignment: Alignment.center,
                  child: const Text('SIGN OUT',
                      style: TextStyle(
                          color: AppColors.statusRed,
                          fontSize: 13,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 1.5)),
                ),
              ),
            ),
          ),
          const SliverToBoxAdapter(child: SizedBox(height: 28)),
        ],
      ),
    );
  }
}