import 'package:flutter/material.dart';
import '../../../core/constants/app_colors.dart';
import '../../../data/models/alert_model.dart';

class LatestAlertCard extends StatelessWidget {
  final AlertModel alert;

  const LatestAlertCard({super.key, required this.alert});

  Color get _bgColor {
    switch (alert.severity) {
      case AlertSeverity.critical: return AppColors.statusRedBg;
      case AlertSeverity.warning:  return AppColors.statusAmberBg;
      case AlertSeverity.info:     return AppColors.iconBlueBg;
    }
  }

  Color get _accentColor {
    switch (alert.severity) {
      case AlertSeverity.critical: return AppColors.statusRed;
      case AlertSeverity.warning:  return AppColors.statusAmber;
      case AlertSeverity.info:     return AppColors.accentBlue;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: _bgColor,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: _accentColor.withOpacity(0.3), width: 1),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Icon circle
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: _accentColor.withOpacity(0.2),
              shape: BoxShape.circle,
            ),
            child: Icon(Icons.notifications_active_rounded,
                color: _accentColor, size: 20),
          ),
          const SizedBox(width: 14),

          // Text content
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(alert.title,
                    style: const TextStyle(
                        color: AppColors.textPrimary,
                        fontSize: 15,
                        fontWeight: FontWeight.w700)),
                const SizedBox(height: 4),
                Text(alert.description,
                    style: const TextStyle(
                        color: AppColors.textSecondary, fontSize: 13)),
                const SizedBox(height: 8),
                Text(alert.timeAgo,
                    style: TextStyle(
                        color: _accentColor,
                        fontSize: 12,
                        fontWeight: FontWeight.w600)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}