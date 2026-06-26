import 'package:flutter/material.dart';
import '../../../core/constants/app_colors.dart';
import '../../../data/models/location_model.dart';

class LocationStatusCard extends StatelessWidget {
  final LocationModel location;

  const LocationStatusCard({super.key, required this.location});

  Color get _statusColor {
    switch (location.status) {
      case VehicleLocationStatus.parked:  return AppColors.statusGreen;
      case VehicleLocationStatus.moving:  return AppColors.accentBlue;
      case VehicleLocationStatus.idle:    return AppColors.statusAmber;
      case VehicleLocationStatus.offline: return AppColors.textMuted;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: AppColors.cardBg.withOpacity(0.92),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppColors.borderColor, width: 1),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          const Text('STATUS',
              style: TextStyle(
                  color: AppColors.labelColor,
                  fontSize: 9,
                  letterSpacing: 1.2,
                  fontWeight: FontWeight.w600)),
          const SizedBox(height: 6),
          Text(location.statusLabel,
              style: TextStyle(
                  color: _statusColor,
                  fontSize: 16,
                  fontWeight: FontWeight.w700)),
          Text(location.timeAgo,
              style: const TextStyle(
                  color: AppColors.textSecondary, fontSize: 11)),
        ],
      ),
    );
  }
}