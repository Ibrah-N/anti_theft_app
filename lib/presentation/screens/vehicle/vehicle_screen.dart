import 'package:flutter/material.dart';
import '../../../core/constants/app_colors.dart';
import '../../../data/models/vehicle_model.dart';
import '../../widgets/vehicle/car_blueprint_painter.dart';
import '../../widgets/vehicle/zone_status_card.dart';
import '../../widgets/common/bottom_nav_bar.dart';

class VehicleScreen extends StatefulWidget {
  const VehicleScreen({super.key});

  @override
  State<VehicleScreen> createState() => _VehicleScreenState();
}

class _VehicleScreenState extends State<VehicleScreen> {
  int _navIndex = 1;

  // Zone state — true = closed/green, false = open/red
  // In Step 2 this comes from the repository / WebSocket stream
  Map<CarZone, bool> _zoneStates = {
    CarZone.bonnet:     true,
    CarZone.frontLeft:  true,
    CarZone.frontRight: true,
    CarZone.rearLeft:   true,
    CarZone.rearRight:  true,
    CarZone.trunk:      true,
  };

  // Map CarZone enum → display name
  static const Map<CarZone, String> _zoneNames = {
    CarZone.bonnet:     'Bonnet',
    CarZone.frontLeft:  'Front Left',
    CarZone.frontRight: 'Front Right',
    CarZone.rearLeft:   'Rear Left',
    CarZone.rearRight:  'Rear Right',
    CarZone.trunk:      'Trunk',
  };

  // Tap on car blueprint toggles zone (simulation mode)
  void _onBlueprintTap(Offset localPos, Size painterSize) {
    final zone = CarZoneHitTester(painterSize).hitTest(localPos);
    if (zone != null) {
      setState(() => _zoneStates[zone] = !(_zoneStates[zone] ?? true));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.scaffoldBg,
      body: SafeArea(
        child: Column(
          children: [
            Expanded(
              child: CustomScrollView(
                slivers: [
                  // ── Header ──────────────────────────────────
                  SliverToBoxAdapter(
                    child: Padding(
                      padding: const EdgeInsets.fromLTRB(16, 16, 16, 20),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: const [
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

                  // ── Car Blueprint ────────────────────────────
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
                              final painterSize = Size(
                                  constraints.maxWidth, constraints.maxHeight);
                              return GestureDetector(
                                onTapDown: (d) => _onBlueprintTap(
                                    d.localPosition, painterSize),
                                child: CustomPaint(
                                  size: painterSize,
                                  painter: CarBlueprintPainter(
                                      zoneStates: _zoneStates),
                                ),
                              );
                            },
                          ),
                        ),
                      ),
                    ),
                  ),

                  const SliverToBoxAdapter(child: SizedBox(height: 24)),

                  // ── Zone Status label ────────────────────────
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

                  // ── Zone grid ────────────────────────────────
                  SliverPadding(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    sliver: SliverGrid(
                      gridDelegate:
                          const SliverGridDelegateWithFixedCrossAxisCount(
                        crossAxisCount: 2,
                        crossAxisSpacing: 10,
                        mainAxisSpacing: 10,
                        childAspectRatio: 2.4,
                      ),
                      delegate: SliverChildListDelegate(
                        _zoneStates.entries.map((e) {
                          return ZoneStatusCard(
                            zoneName: _zoneNames[e.key]!,
                            isClosed: e.value,
                          );
                        }).toList(),
                      ),
                    ),
                  ),

                  const SliverToBoxAdapter(child: SizedBox(height: 24)),
                ],
              ),
            ),
          ],
        ),
      ),

      // ── Bottom Nav ───────────────────────────────────────
      bottomNavigationBar: SmartGuardBottomNav(
        currentIndex: _navIndex,
        onTap: (i) => setState(() => _navIndex = i),
      ),
    );
  }
}