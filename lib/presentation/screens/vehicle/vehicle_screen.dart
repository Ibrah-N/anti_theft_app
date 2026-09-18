// lib/presentation/screens/vehicle/vehicle_screen.dart
// CHANGED: removed Scaffold + bottomNavigationBar + _navIndex — nav lives in HomeScreen now

import 'package:flutter/material.dart';
import '../../../core/constants/app_colors.dart';
import '../../../data/models/vehicle_model.dart';
import '../../widgets/vehicle/car_blueprint_painter.dart';
import '../../widgets/vehicle/zone_status_card.dart';
import '../../widgets/vehicle/control_button.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../data/providers/vehicle_provider.dart';



class VehicleScreen extends ConsumerStatefulWidget {
  const VehicleScreen({super.key});

  @override
  ConsumerState<VehicleScreen> createState() => _VehicleScreenState();
}

class _VehicleScreenState extends ConsumerState<VehicleScreen> {
  // Zone state — true = closed/green, false = open/red
  // In Step 2 this comes from the repository / WebSocket stream
  static const Map<CarZone, String> _zoneNames = {
    CarZone.bonnet:     'Bonnet',
    CarZone.frontLeft:  'Front Left',
    CarZone.frontRight: 'Front Right',
    CarZone.rearLeft:   'Rear Left',
    CarZone.rearRight:  'Rear Right',
    CarZone.trunk:      'Trunk',
  };

  void _onBlueprintTap(Offset localPos, Size painterSize) {
  // TODO hardware phase — tap will send command to device
    // For now just visual feedback
  }

  // ── Build zone map from provider data ────────────────────────────────────────
  Map<CarZone, bool> _zonesFromVehicle(VehicleModel vehicle) => {
    CarZone.bonnet:     vehicle.zones[4].isClosed,
    CarZone.frontLeft:  vehicle.zones[0].isClosed,
    CarZone.frontRight: vehicle.zones[1].isClosed,
    CarZone.rearLeft:   vehicle.zones[2].isClosed,
    CarZone.rearRight:  vehicle.zones[3].isClosed,
    CarZone.trunk:      vehicle.zones[5].isClosed,
  };

  @override
  Widget build(BuildContext context) {
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
      data: (vehicle) => _buildContent(
        vehicle,
        _zonesFromVehicle(vehicle),
        ref.watch(pendingCommandsProvider),
      ),
    );
  }

  void _toggleLock(bool locked) =>
      ref.read(vehicleProvider.notifier).toggleLock(locked);

  void _toggleMirror(String position, bool folded) =>
      ref.read(vehicleProvider.notifier).toggleMirror(position, folded);

  void _toggleStart(bool started) =>
      ref.read(vehicleProvider.notifier).toggleStart(started);

  void _toggleAc(bool on) =>
      ref.read(vehicleProvider.notifier).toggleAc(on);

  Widget _buildContent(
    VehicleModel vehicle,
    Map<CarZone, bool> zoneStates,
    Set<String> pending,
  ) {
    return SafeArea(
      child: RefreshIndicator(
        onRefresh: () => ref.read(vehicleProvider.notifier).retry(),
        child: CustomScrollView(
        slivers: [
          // ── Header ──────────────────────────────────────────────────────
          const SliverToBoxAdapter(
            child: Padding(
              padding: EdgeInsets.fromLTRB(16, 16, 16, 20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Vehicle Status',
                      style: TextStyle(
                          color: AppColors.textPrimary,
                          fontSize: 26,
                          fontWeight: FontWeight.w800)),
                  SizedBox(height: 4),
                  Text('Tap any zone to simulate open/close',
                      style: TextStyle(
                          color: AppColors.accentBlue, fontSize: 13)),
                ],
              ),
            ),
          ),

          // ── Car Blueprint ────────────────────────────────────────────────
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Container(
                height: 400,
                decoration: BoxDecoration(
                  color: AppColors.cardBg,
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: AppColors.borderColor),
                ),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(20),
                  child: LayoutBuilder(
                    builder: (ctx, constraints) {
                      final painterSize =
                          Size(constraints.maxWidth, constraints.maxHeight);
                      return GestureDetector(
                        onTapDown: (d) =>
                            _onBlueprintTap(d.localPosition, painterSize),
                        child: CustomPaint(
                          size: painterSize,
                          painter: CarBlueprintPainter(zoneStates: zoneStates),
                        ),
                      );
                    },
                  ),
                ),
              ),
            ),
          ),

          const SliverToBoxAdapter(child: SizedBox(height: 24)),

          // ── Zone Status label ────────────────────────────────────────────
          const SliverToBoxAdapter(
            child: Padding(
              padding: EdgeInsets.symmetric(horizontal: 16),
              child: Text('ZONE STATUS',
                  style: TextStyle(
                      color: AppColors.labelColor,
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                      letterSpacing: 1.5)),
            ),
          ),
          const SliverToBoxAdapter(child: SizedBox(height: 12)),

          // ── Zone grid ────────────────────────────────────────────────────
          SliverPadding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            sliver: SliverGrid(
              gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: 2,
                crossAxisSpacing: 10,
                mainAxisSpacing: 10,
                childAspectRatio: 2.4,
              ),
              delegate: SliverChildListDelegate(
                zoneStates.entries.map((e) {
                  return ZoneStatusCard(
                    zoneName: _zoneNames[e.key]!,
                    isClosed: e.value,
                  );
                }).toList(),
              ),
            ),
          ),

          const SliverToBoxAdapter(child: SizedBox(height: 24)),

          // ── Door controls ────────────────────────────────────────────────
          const SliverToBoxAdapter(
            child: Padding(
              padding: EdgeInsets.symmetric(horizontal: 16),
              child: Text('DOOR CONTROLS',
                  style: TextStyle(
                      color: AppColors.labelColor,
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                      letterSpacing: 1.5)),
            ),
          ),
          const SliverToBoxAdapter(child: SizedBox(height: 12)),
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Row(children: [
                Expanded(
                  child: ControlButton(
                    icon: Icons.lock_outline_rounded,
                    label: 'Lock All',
                    active: vehicle.doorsLocked,
                    pending: pending.contains('lock'),
                    onTap: () => _toggleLock(true),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: ControlButton(
                    icon: Icons.lock_open_outlined,
                    label: 'Unlock All',
                    active: !vehicle.doorsLocked,
                    pending: pending.contains('lock'),
                    onTap: () => _toggleLock(false),
                  ),
                ),
              ]),
            ),
          ),

          const SliverToBoxAdapter(child: SizedBox(height: 24)),

          // ── Mirror controls ──────────────────────────────────────────────
          const SliverToBoxAdapter(
            child: Padding(
              padding: EdgeInsets.symmetric(horizontal: 16),
              child: Text('MIRROR CONTROLS',
                  style: TextStyle(
                      color: AppColors.labelColor,
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                      letterSpacing: 1.5)),
            ),
          ),
          const SliverToBoxAdapter(child: SizedBox(height: 12)),
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Column(children: [
                Row(children: [
                  Expanded(
                    child: ControlButton(
                      icon: Icons.arrow_upward_rounded,
                      label: vehicle.mirrorFl ? 'FL · Unfold' : 'FL · Fold',
                      active: vehicle.mirrorFl,
                      pending: pending.contains('mirror_fl'),
                      onTap: () => _toggleMirror('fl', !vehicle.mirrorFl),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: ControlButton(
                      icon: Icons.arrow_upward_rounded,
                      label: vehicle.mirrorFr ? 'FR · Unfold' : 'FR · Fold',
                      active: vehicle.mirrorFr,
                      pending: pending.contains('mirror_fr'),
                      onTap: () => _toggleMirror('fr', !vehicle.mirrorFr),
                    ),
                  ),
                ]),
                const SizedBox(height: 10),
                Row(children: [
                  Expanded(
                    child: ControlButton(
                      icon: Icons.arrow_upward_rounded,
                      label: vehicle.mirrorRl ? 'RL · Unfold' : 'RL · Fold',
                      active: vehicle.mirrorRl,
                      pending: pending.contains('mirror_rl'),
                      onTap: () => _toggleMirror('rl', !vehicle.mirrorRl),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: ControlButton(
                      icon: Icons.arrow_upward_rounded,
                      label: vehicle.mirrorRr ? 'RR · Unfold' : 'RR · Fold',
                      active: vehicle.mirrorRr,
                      pending: pending.contains('mirror_rr'),
                      onTap: () => _toggleMirror('rr', !vehicle.mirrorRr),
                    ),
                  ),
                ]),
              ]),
            ),
          ),

          const SliverToBoxAdapter(child: SizedBox(height: 24)),

          // ── Engine & comfort ─────────────────────────────────────────────
          const SliverToBoxAdapter(
            child: Padding(
              padding: EdgeInsets.symmetric(horizontal: 16),
              child: Text('ENGINE & COMFORT',
                  style: TextStyle(
                      color: AppColors.labelColor,
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                      letterSpacing: 1.5)),
            ),
          ),
          const SliverToBoxAdapter(child: SizedBox(height: 12)),
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Row(children: [
                Expanded(
                  child: ControlButton(
                    icon: Icons.bolt_rounded,
                    label: vehicle.engineStarted ? 'Stop Engine' : 'Start Engine',
                    active: vehicle.engineStarted,
                    pending: pending.contains('start'),
                    onTap: () => _toggleStart(!vehicle.engineStarted),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: ControlButton(
                    icon: Icons.ac_unit_rounded,
                    label: vehicle.acOn ? 'AC · ON' : 'AC · OFF',
                    active: vehicle.acOn,
                    pending: pending.contains('ac'),
                    onTap: () => _toggleAc(!vehicle.acOn),
                  ),
                ),
              ]),
            ),
          ),

          const SliverToBoxAdapter(child: SizedBox(height: 24)),
        ],
      ),
      ),
    );
  }
}