// lib/presentation/screens/home/home_screen.dart

import 'package:flutter/material.dart';
import '../../../core/constants/app_colors.dart';
import '../../../data/models/vehicle_model.dart';
import '../../widgets/home/vehicle_status_card.dart';
import '../../widgets/home/quick_control_card.dart';
import '../../widgets/home/stat_card.dart';
import '../../widgets/common/bottom_nav_bar.dart';
import '../vehicle/vehicle_screen.dart';
import '../map/map_screen.dart';
import '../camera/camera_screen.dart';
import '../alerts/alerts_screen.dart';
import '../settings/settings_screen.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../data/providers/vehicle_provider.dart';
import '../../../data/providers/alerts_provider.dart';

import '../../../main.dart';



class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> with WidgetsBindingObserver {
  int _navIndex = 0;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _checkPendingAlertNavigation();
    });
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState appState) {
    if (appState == AppLifecycleState.resumed) {
      ref.read(vehicleProvider.notifier).retry();
      ref.read(alertsProvider.notifier).load();
      _checkPendingAlertNavigation();
    }
  }

  void _checkPendingAlertNavigation() {
    if (pendingAlertNavigation) {
      pendingAlertNavigation = false;
      setState(() => _navIndex = 4); // Alerts tab
      ref.read(alertsProvider.notifier).load(); // force fresh fetch, no stale cache
    }
  }


  void _toggleEngine() {
    ref.read(vehicleProvider.notifier).toggleEngine(
      !(ref.read(vehicleProvider).valueOrNull?.engineOn ?? false),
    );
  }

  void _toggleFuel() {
    ref.read(vehicleProvider.notifier).toggleFuel(
      !(ref.read(vehicleProvider).valueOrNull?.fuelFlowing ?? true),
    );
  }

  // ── Body switcher ─────────────────────────────────────────────────────────
  Widget _buildBody() {
  switch (_navIndex) {
    case 0:
      final vehicleAsync = ref.watch(vehicleProvider);
      return vehicleAsync.when(
        loading: () => const Center(
          child: CircularProgressIndicator(color: AppColors.primaryBlue),
        ),
        error: (e, _) => Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text('Cannot reach server — check your connection',
                  style: TextStyle(color: AppColors.statusRed)),
              const SizedBox(height: 12),
              TextButton(
                onPressed: () => ref.read(vehicleProvider.notifier).retry(),
                child: const Text('Retry'),
              ),
            ],
          ),
        ),
        data: (vehicle) => _HomeTab(
          vehicle:        vehicle,
          onToggleEngine: _toggleEngine,
          onToggleFuel:   _toggleFuel,
          buildAppBar:    _buildAppBar,
          onRefresh:      () => ref.read(vehicleProvider.notifier).retry(),
        ),
      );
      case 1: return const VehicleScreen();
      case 2: return const MapScreen();
      case 3: return const CameraScreen();
      case 4: return const AlertsScreen();
      case 5: return const SettingsScreen();
      default: return const SizedBox.shrink();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.scaffoldBg,
      body: _buildBody(),
      bottomNavigationBar: SmartGuardBottomNav(
        currentIndex: _navIndex,
        onTap: (i) => setState(() => _navIndex = i),
        unreadCount: ref.watch(alertsProvider).unreadCount,
      ),
    );
  }

  // ── App Bar (only used by HomeTab) ────────────────────────────────────────
  Widget _buildAppBar() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 20),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
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
                Text(ref.watch(vehicleProvider).valueOrNull?.name ?? 'SmartGuard',
                    style: const TextStyle(
                        color: AppColors.textPrimary,
                        fontSize: 24,
                        fontWeight: FontWeight.w800)),
                const SizedBox(height: 4),
                Text('Reg: ${ref.watch(vehicleProvider).valueOrNull?.regNumber ?? '---'}',
                    style: const TextStyle(
                        color: AppColors.textSecondary, fontSize: 13)),
              ],
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              GestureDetector(
                onTap: () => setState(() => _navIndex = 4),
                child: Stack(clipBehavior: Clip.none, children: [
                  Container(
                    width: 40, height: 40,
                    decoration: BoxDecoration(
                        color: AppColors.cardBg,
                        shape: BoxShape.circle,
                        border: Border.all(color: AppColors.borderColor)),
                    child: const Icon(Icons.notifications_outlined,
                        color: AppColors.textSecondary, size: 20),
                  ),
                  if (ref.watch(alertsProvider).unreadCount > 0)
                    Positioned(
                      right: -2, top: -2,
                      child: Container(
                        padding: const EdgeInsets.all(4),
                        decoration: const BoxDecoration(
                            color: AppColors.statusRed, shape: BoxShape.circle),
                        child: Text('${ref.watch(alertsProvider).unreadCount}',
                            style: const TextStyle(
                                color: Colors.white,
                                fontSize: 9,
                                fontWeight: FontWeight.bold)),
                      ),
                    ),
                ]),
              ),
              const SizedBox(height: 10),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
                decoration: BoxDecoration(
                  color: AppColors.statusGreenBg,
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(
                      color: AppColors.statusGreen..withValues(alpha: 0.4), width: 1),
                ),
                child: Row(mainAxisSize: MainAxisSize.min, children: [
                  Container(
                      width: 7, height: 7,
                      decoration: const BoxDecoration(
                          color: AppColors.statusGreen, shape: BoxShape.circle)),
                  const SizedBox(width: 6),
                  const Text('Online',
                      style: TextStyle(
                          color: AppColors.statusGreen,
                          fontSize: 12,
                          fontWeight: FontWeight.w600)),
                ]),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

// ── Home tab ──────────────────────────────────────────────────────────────────
class _HomeTab extends StatelessWidget {
  final VehicleModel   vehicle;
  final VoidCallback   onToggleEngine;
  final VoidCallback   onToggleFuel;
  
  final Widget Function() buildAppBar;
  final Future<void> Function() onRefresh;

  const _HomeTab({
    required this.vehicle,
    required this.onToggleEngine,
    required this.onToggleFuel,
    required this.buildAppBar,
    required this.onRefresh,
  });

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: RefreshIndicator(
        onRefresh: onRefresh,
        child: CustomScrollView(
        slivers: [
          SliverToBoxAdapter(child: buildAppBar()),
          SliverPadding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
            sliver: SliverList(
              delegate: SliverChildListDelegate([
                VehicleStatusCard(vehicle: vehicle),
                const SizedBox(height: 24),
                const Text('QUICK CONTROLS',
                    style: TextStyle(
                        color: AppColors.labelColor,
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                        letterSpacing: 1.5)),
                const SizedBox(height: 12),
                Row(children: [
                  Expanded(
                    child: QuickControlCard(
                      icon: Icons.power_settings_new_rounded,
                      title: 'Engine',
                      subtitle: 'Ignition control',
                      badgeLabel: vehicle.engineOn ? 'ON' : 'OFF',
                      badgeColor: vehicle.engineOn ? AppColors.badgeOn  : AppColors.badgeOff,
                      badgeBg:    vehicle.engineOn ? AppColors.statusGreenBg : AppColors.badgeOffBg,
                      onTap: onToggleEngine,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: QuickControlCard(
                      icon: Icons.water_drop_outlined,
                      title: 'Fuel',
                      subtitle: 'Cutoff system',
                      badgeLabel: vehicle.fuelFlowing ? 'FLOW' : 'CUT',
                      badgeColor: vehicle.fuelFlowing ? AppColors.badgeFlow : AppColors.badgeOff,
                      badgeBg:    vehicle.fuelFlowing ? AppColors.statusGreenBg : AppColors.badgeOffBg,
                      onTap: onToggleFuel,
                    ),
                  ),
                ]),
                const SizedBox(height: 12),
                Row(children: [
                  Expanded(child: StatCard(
                    icon: Icons.show_chart_rounded,
                    iconColor: AppColors.accentBlue,
                    value: vehicle.speedKmh.toInt().toString(),
                    unit: 'km/h', label: 'SPEED',
                  )),
                  const SizedBox(width: 10),
                  Expanded(child: StatCard(
                    icon: Icons.bolt_rounded,
                    iconColor: AppColors.statusAmber,
                    value: vehicle.batteryLevel.toString(),
                    unit: 'volts', label: 'BATTERY',
                  )),
                  const SizedBox(width: 10),
                  Expanded(child: StatCard(
                    icon: Icons.signal_cellular_alt_rounded,
                    iconColor: AppColors.statusGreen,
                    value: '${vehicle.signalBars}/4',
                    unit: 'bars', label: 'SIGNAL',
                  )),
                ]),
                const SizedBox(height: 24),
              ]),
            ),
          ),
          ],
        ),
      ), 
    );
  }
}