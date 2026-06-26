import 'package:flutter/material.dart';
import '../../../core/constants/app_colors.dart';
import '../../../data/models/vehicle_model.dart';

class ZoneIndicatorRow extends StatelessWidget {
  final List<ZoneStatus> zones;

  const ZoneIndicatorRow({super.key, required this.zones});

  @override
  Widget build(BuildContext context) {
    final allSecured = zones.every((z) => z.isClosed);

    return Column(
      children: [
        // Dots row
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceEvenly,
          children: zones.map((z) => _ZoneDot(zone: z)).toList(),
        ),

        const SizedBox(height: 16),
        const Divider(color: AppColors.divider, height: 1),
        const SizedBox(height: 14),

        // Status text
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              allSecured ? Icons.check_circle : Icons.warning_rounded,
              color: allSecured ? AppColors.statusGreen : AppColors.statusRed,
              size: 18,
            ),
            const SizedBox(width: 8),
            Text(
              allSecured ? 'All zones secured' : 'Zone breach detected',
              style: TextStyle(
                color: allSecured ? AppColors.statusGreen : AppColors.statusRed,
                fontSize: 14,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ],
    );
  }
}

class _ZoneDot extends StatelessWidget {
  final ZoneStatus zone;
  const _ZoneDot({required this.zone});

  @override
  Widget build(BuildContext context) {
    final color = zone.isClosed ? AppColors.zoneClosed : AppColors.zoneOpen;
    return Column(
      children: [
        // Glowing dot
        Container(
          width: 10,
          height: 10,
          decoration: BoxDecoration(
            color: color,
            shape: BoxShape.circle,
            boxShadow: [
              BoxShadow(color: color.withOpacity(0.6), blurRadius: 6, spreadRadius: 1),
            ],
          ),
        ),
        const SizedBox(height: 6),
        Text(
          zone.label,
          style: const TextStyle(
            color: AppColors.textSecondary,
            fontSize: 11,
            letterSpacing: 0.5,
          ),
        ),
      ],
    );
  }
}