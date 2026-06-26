import 'package:flutter/material.dart';
import '../../../core/constants/app_colors.dart';
import '../../../data/models/camera_model.dart';

class CameraControlRow extends StatelessWidget {
  final CameraStatus status;
  final bool isRecording;
  final VoidCallback onSnapshot;
  final VoidCallback onRecord;

  const CameraControlRow({
    super.key,
    required this.status,
    required this.isRecording,
    required this.onSnapshot,
    required this.onRecord,
  });

  bool get _enabled => status == CameraStatus.streaming;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: _ControlButton(
            icon: Icons.motion_photos_on_outlined,
            label: 'Snapshot',
            enabled: _enabled,
            onTap: onSnapshot,
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: _ControlButton(
            icon: Icons.show_chart_rounded,
            label: isRecording ? 'Stop' : 'Record',
            enabled: _enabled,
            active: isRecording,
            onTap: onRecord,
          ),
        ),
      ],
    );
  }
}

class _ControlButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final bool enabled;
  final bool active;
  final VoidCallback onTap;

  const _ControlButton({
    required this.icon,
    required this.label,
    required this.enabled,
    required this.onTap,
    this.active = false,
  });

  @override
  Widget build(BuildContext context) {
    final Color fg = enabled
        ? (active ? AppColors.statusRed : AppColors.textPrimary)
        : AppColors.textMuted;

    final Color border = enabled
        ? (active ? AppColors.statusRed : AppColors.borderColor)
        : AppColors.borderColor;

    return GestureDetector(
      onTap: enabled ? onTap : null,
      child: Container(
        height: 52,
        decoration: BoxDecoration(
          color: AppColors.cardBg,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: border),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, color: fg, size: 18),
            const SizedBox(width: 8),
            Text(
              label,
              style: TextStyle(
                color: fg,
                fontSize: 14,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
      ),
    );
  }
}