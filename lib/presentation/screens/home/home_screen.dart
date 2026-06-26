import 'package:flutter/material.dart';
import '../../../core/constants/app_colors.dart';
import '../../../data/models/vehicle_model.dart';
import '../../../data/models/alert_model.dart';
import '../../widgets/home/vehicle_status_card.dart';
import '../../widgets/home/quick_control_card.dart';
import '../../widgets/home/stat_card.dart';
import '../../widgets/home/latest_alert_card.dart';
import '../../widgets/common/bottom_nav_bar.dart';
import '../vehicle/vehicle_screen.dart';
import '../map/map_screen.dart';
import '../settings/settings_screen.dart';
import '../camera/camera_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _navIndex = 0;
  // Mock data — will be replaced by provider/repository in Step 2
  final VehicleModel _vehicle = VehicleModel.mock();
  final AlertModel _latestAlert = AlertModel.mock();

  void _toggleEngine() {
    // TODO Step 2: call repository
  }

  void _toggleFuel() {
    // TODO Step 2: call repository
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.scaffoldBg,
      body: SafeArea(
        child: CustomScrollView(
          slivers: [
            // ── App Bar ───────────────────────────────────────
            SliverToBoxAdapter(child: _buildAppBar()),

            SliverPadding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
              sliver: SliverList(
                delegate: SliverChildListDelegate([

                  // ── Vehicle Status Card ──────────────────────
                  VehicleStatusCard(vehicle: _vehicle),
                  const SizedBox(height: 24),

                  // ── Quick Controls label ─────────────────────
                  const Text('QUICK CONTROLS',
                      style: TextStyle(
                          color: AppColors.labelColor,
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                          letterSpacing: 1.5)),
                  const SizedBox(height: 12),

                  // ── Engine + Fuel row ────────────────────────
                  Row(children: [
                    Expanded(
                      child: QuickControlCard(
                        icon: Icons.power_settings_new_rounded,
                        title: 'Engine',
                        subtitle: 'Ignition control',
                        badgeLabel: _vehicle.engineOn ? 'ON' : 'OFF',
                        badgeColor: _vehicle.engineOn
                            ? AppColors.badgeOn
                            : AppColors.badgeOff,
                        badgeBg: _vehicle.engineOn
                            ? AppColors.statusGreenBg
                            : AppColors.badgeOffBg,
                        onTap: _toggleEngine,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: QuickControlCard(
                        icon: Icons.water_drop_outlined,
                        title: 'Fuel',
                        subtitle: 'Cutoff system',
                        badgeLabel: _vehicle.fuelFlowing ? 'FLOW' : 'CUT',
                        badgeColor: _vehicle.fuelFlowing
                            ? AppColors.badgeFlow
                            : AppColors.badgeOff,
                        badgeBg: _vehicle.fuelFlowing
                            ? AppColors.statusGreenBg
                            : AppColors.badgeOffBg,
                        onTap: _toggleFuel,
                      ),
                    ),
                  ]),
                  const SizedBox(height: 12),

                  // ── Stat cards row ───────────────────────────
                  Row(children: [
                    Expanded(
                      child: StatCard(
                        icon: Icons.show_chart_rounded,
                        iconColor: AppColors.accentBlue,
                        value: _vehicle.speedKmh.toInt().toString(),
                        unit: 'km/h',
                        label: 'SPEED',
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: StatCard(
                        icon: Icons.bolt_rounded,
                        iconColor: AppColors.statusAmber,
                        value: _vehicle.batteryLevel.toString(),
                        unit: 'volts',
                        label: 'BATTERY',
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: StatCard(
                        icon: Icons.signal_cellular_alt_rounded,
                        iconColor: AppColors.statusGreen,
                        value: '${_vehicle.signalBars}/4',
                        unit: 'bars',
                        label: 'SIGNAL',
                      ),
                    ),
                  ]),
                  const SizedBox(height: 24),

                  // ── Latest Alert label ───────────────────────
                  const Text('LATEST ALERT',
                      style: TextStyle(
                          color: AppColors.labelColor,
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                          letterSpacing: 1.5)),
                  const SizedBox(height: 12),

                  // ── Alert card ───────────────────────────────
                  LatestAlertCard(alert: _latestAlert),

                  const SizedBox(height: 24),
                ]),
              ),
            ),
          ],
        ),
      ),

      // ── Bottom Nav ─────────────────────────────────────────
      bottomNavigationBar: SmartGuardBottomNav(
        currentIndex: _navIndex,

      onTap: (i) {
          if (i == 1) {
            Navigator.push(context,
                MaterialPageRoute(builder: (_) => const VehicleScreen()));
          } else if (i == 2) {
            Navigator.push(context,
                MaterialPageRoute(builder: (_) => const MapScreen()));
          } else if (i == 3) {
            Navigator.push(context,
                MaterialPageRoute(builder: (_) => const CameraScreen()));
          } else if (i == 5) {
            Navigator.push(context,
                MaterialPageRoute(builder: (_) => const SettingsScreen()));
          } else {
            setState(() => _navIndex = i);
          }
        },

      ),
    );
  }

  Widget _buildAppBar() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 20),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Left: label + name + reg
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('SMARTGUARD',
                    style: TextStyle(
                        color: AppColors.labelColor,
                        fontSize: 11,
                        letterSpacing: 1.5,
                        fontWeight: FontWeight.w600)),
                const SizedBox(height: 4),
                Text(_vehicle.name,
                    style: const TextStyle(
                        color: AppColors.textPrimary,
                        fontSize: 24,
                        fontWeight: FontWeight.w800)),
                const SizedBox(height: 4),
                Text('Reg: ${_vehicle.regNumber}',
                    style: const TextStyle(
                        color: AppColors.textSecondary, fontSize: 13)),
              ],
            ),
          ),

          // Right: notification bell + online pill (stacked)
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              // Bell with badge
              Stack(clipBehavior: Clip.none, children: [
                Container(
                  width: 40, height: 40,
                  decoration: BoxDecoration(
                      color: AppColors.cardBg,
                      shape: BoxShape.circle,
                      border: Border.all(color: AppColors.borderColor)),
                  child: const Icon(Icons.notifications_outlined,
                      color: AppColors.textSecondary, size: 20),
                ),
                Positioned(
                  right: -2, top: -2,
                  child: Container(
                    padding: const EdgeInsets.all(4),
                    decoration: const BoxDecoration(
                        color: AppColors.statusRed, shape: BoxShape.circle),
                    child: const Text('3',
                        style: TextStyle(
                            color: Colors.white,
                            fontSize: 9,
                            fontWeight: FontWeight.bold)),
                  ),
                ),
              ]),
              const SizedBox(height: 10),

              // Online pill
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
                decoration: BoxDecoration(
                  color: AppColors.statusGreenBg,
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(
                      color: AppColors.statusGreen.withOpacity(0.4), width: 1),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                        width: 7, height: 7,
                        decoration: const BoxDecoration(
                            color: AppColors.statusGreen,
                            shape: BoxShape.circle)),
                    const SizedBox(width: 6),
                    const Text('Online',
                        style: TextStyle(
                            color: AppColors.statusGreen,
                            fontSize: 12,
                            fontWeight: FontWeight.w600)),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}