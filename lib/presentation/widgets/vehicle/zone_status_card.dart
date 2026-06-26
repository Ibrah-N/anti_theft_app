import 'package:flutter/material.dart';
import '../../../core/constants/app_colors.dart';

class ZoneStatusCard extends StatelessWidget {
  final String zoneName;
  final bool isClosed;

  const ZoneStatusCard({
    super.key,
    required this.zoneName,
    required this.isClosed,
  });

  @override
  Widget build(BuildContext context) {
    final color = isClosed ? AppColors.zoneClosed : AppColors.zoneOpen;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
      decoration: BoxDecoration(
        color: AppColors.cardBg,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppColors.borderColor, width: 1),
      ),
      child: Row(
        children: [
          // Status dot
          Container(
            width: 10, height: 10,
            decoration: BoxDecoration(
              color: color,
              shape: BoxShape.circle,
              boxShadow: [BoxShadow(color: color.withOpacity(0.6), blurRadius: 6)],
            ),
          ),
          const SizedBox(width: 12),

          // Name + status
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(zoneName,
                    style: const TextStyle(
                        color: AppColors.textPrimary,
                        fontSize: 15,
                        fontWeight: FontWeight.w700)),
                const SizedBox(height: 2),
                Text(isClosed ? 'Secured' : 'Open',
                    style: TextStyle(
                        color: color,
                        fontSize: 12,
                        fontWeight: FontWeight.w500)),
              ],
            ),
          ),

          // Lock icon
          Icon(
            isClosed ? Icons.lock_outline_rounded : Icons.lock_open_outlined,
            color: isClosed ? AppColors.textMuted : AppColors.statusRed,
            size: 18,
          ),
        ],
      ),
    );
  }
}