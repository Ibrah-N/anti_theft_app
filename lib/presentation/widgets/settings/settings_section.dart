import 'package:flutter/material.dart';
import '../../../core/constants/app_colors.dart';
import 'settings_row.dart';

class SettingsSectionData {
  final IconData icon;
  final Color iconColor;
  final Color iconBg;
  final String label;
  final String value;
  final bool hasChevron;
  final VoidCallback? onTap;

  const SettingsSectionData({
    required this.icon,
    required this.iconColor,
    required this.iconBg,
    required this.label,
    required this.value,
    this.hasChevron = false,
    this.onTap,
  });
}

class SettingsSection extends StatelessWidget {
  final String title;
  final List<SettingsSectionData> rows;

  const SettingsSection({
    super.key,
    required this.title,
    required this.rows,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Section label
        Text(
          title,
          style: const TextStyle(
            color: AppColors.labelColor,
            fontSize: 11,
            fontWeight: FontWeight.w600,
            letterSpacing: 1.5,
          ),
        ),
        const SizedBox(height: 10),

        // Section card
        Container(
          decoration: BoxDecoration(
            color: AppColors.cardBg,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: AppColors.borderColor, width: 1),
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(16),
            child: Column(
              children: List.generate(rows.length, (i) {
                final row = rows[i];
                return SettingsRow(
                  icon: row.icon,
                  iconColor: row.iconColor,
                  iconBg: row.iconBg,
                  label: row.label,
                  value: row.value,
                  hasChevron: row.hasChevron,
                  onTap: row.onTap,
                  isFirst: i == 0,
                  isLast: i == rows.length - 1,
                );
              }),
            ),
          ),
        ),
      ],
    );
  }
}