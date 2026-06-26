import 'package:flutter/material.dart';
import '../../../core/constants/app_colors.dart';
import '../../../data/models/vehicle_model.dart';
import 'zone_indicator.dart';

class VehicleStatusCard extends StatelessWidget {
  final VehicleModel vehicle;

  const VehicleStatusCard({super.key, required this.vehicle});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.cardBg,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: AppColors.borderColor, width: 1),
      ),
      child: Column(
        children: [
          // ── Top bar: connectivity + voltage ──────────────
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 14, 16, 0),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(children: [
                  const Icon(Icons.signal_cellular_alt,
                      color: AppColors.textSecondary, size: 16),
                  const SizedBox(width: 6),
                  Text(vehicle.connectivity,
                      style: const TextStyle(
                          color: AppColors.textSecondary, fontSize: 13)),
                ]),
                Row(children: [
                  const Icon(Icons.battery_full_outlined,
                      color: AppColors.statusGreen, size: 16),
                  const SizedBox(width: 4),
                  Text('${vehicle.batteryVolts}V',
                      style: const TextStyle(
                          color: AppColors.statusGreen,
                          fontSize: 13,
                          fontWeight: FontWeight.w600)),
                ]),
              ],
            ),
          ),

          // ── Car illustration ─────────────────────────────
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 16),
            child: Container(
              height: 140,
              decoration: BoxDecoration(
                color: AppColors.surfaceBg,
                borderRadius: BorderRadius.circular(14),
              ),
              child: const Center(
                child: Icon(
                  Icons.directions_car_rounded,
                  size: 80,
                  color: Color(0xFF2A3A5C),
                ),
              ),
            ),
          ),

          // ── Zone indicators ──────────────────────────────
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 4, 16, 16),
            child: ZoneIndicatorRow(zones: vehicle.zones),
          ),
        ],
      ),
    );
  }
}