import 'package:flutter/material.dart';
import '../../../core/constants/app_colors.dart';

class SettingsRow extends StatelessWidget {
  final IconData icon;
  final Color iconColor;
  final Color iconBg;
  final String label;
  final String value;
  final bool hasChevron;
  final VoidCallback? onTap;
  final bool isFirst;
  final bool isLast;

  const SettingsRow({
    super.key,
    required this.icon,
    required this.iconColor,
    required this.iconBg,
    required this.label,
    required this.value,
    this.hasChevron = false,
    this.onTap,
    this.isFirst = false,
    this.isLast = false,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: Column(
        children: [
          Padding(
            padding: const EdgeInsets.symmetric(
                horizontal: 16, vertical: 15),
            child: Row(
              children: [
                // Icon circle
                Container(
                  width: 36,
                  height: 36,
                  decoration: BoxDecoration(
                    color: iconBg,
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Icon(icon, color: iconColor, size: 17),
                ),
                const SizedBox(width: 14),

                // Label
                Expanded(
                  child: Text(
                    label,
                    style: const TextStyle(
                      color: AppColors.textPrimary,
                      fontSize: 15,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ),

                // Value (monospace feel)
                Text(
                  value,
                  style: const TextStyle(
                    color: AppColors.textSecondary,
                    fontSize: 12,
                    fontFamily: 'monospace',
                    letterSpacing: 0.3,
                  ),
                ),

                // Chevron
                if (hasChevron) ...[
                  const SizedBox(width: 6),
                  const Icon(Icons.chevron_right_rounded,
                      color: AppColors.textMuted, size: 18),
                ],
              ],
            ),
          ),

          // Divider — skip on last row
          if (!isLast)
            const Divider(
              height: 1,
              thickness: 1,
              color: AppColors.divider,
              indent: 66,
            ),
        ],
      ),
    );
  }
}