import 'package:flutter/material.dart';
import '../../../core/constants/app_colors.dart';
import '../../../data/models/alert_model.dart';

class AlertListTile extends StatelessWidget {
  final AlertModel alert;
  final VoidCallback? onTap;

  const AlertListTile({super.key, required this.alert, this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AppColors.cardBg,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: alert.isRead
                ? AppColors.borderColor
                : alert.borderColor,
            width: alert.isRead ? 1 : 1.2,
          ),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [

            // ── Icon circle ───────────────────────────────────────────────
            Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                color: alert.iconBg,
                shape: BoxShape.circle,
              ),
              child: Icon(alert.icon, color: alert.iconColor, size: 20),
            ),
            const SizedBox(width: 14),

            // ── Content ───────────────────────────────────────────────────
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Title row + unread dot
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.center,
                    children: [
                      Expanded(
                        child: Text(
                          alert.title,
                          style: TextStyle(
                            color: AppColors.textPrimary,
                            fontSize: 15,
                            fontWeight: alert.isRead
                                ? FontWeight.w500
                                : FontWeight.w700,
                          ),
                        ),
                      ),
                      if (!alert.isRead) ...[
                        const SizedBox(width: 8),
                        Container(
                          width: 8,
                          height: 8,
                          decoration: const BoxDecoration(
                            color: AppColors.statusRed,
                            shape: BoxShape.circle,
                          ),
                        ),
                      ],
                    ],
                  ),
                  const SizedBox(height: 5),

                  // Subtitle
                  Text(
                    alert.subtitle,
                    style: const TextStyle(
                      color: AppColors.textSecondary,
                      fontSize: 13,
                    ),
                  ),
                  const SizedBox(height: 8),

                  // Time row
                  Row(
                    children: [
                      const Icon(Icons.access_time_rounded,
                          color: AppColors.textMuted, size: 13),
                      const SizedBox(width: 4),
                      Text(
                        alert.timeAgo,
                        style: const TextStyle(
                          color: AppColors.textMuted,
                          fontSize: 12,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}