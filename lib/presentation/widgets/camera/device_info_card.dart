import 'package:flutter/material.dart';
import '../../../core/constants/app_colors.dart';
import '../../../data/models/camera_model.dart';

class DeviceInfoCard extends StatelessWidget {
  final CameraModel camera;

  const DeviceInfoCard({super.key, required this.camera});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.cardBg,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.borderColor),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Section label
          const Text(
            'DEVICE INFO',
            style: TextStyle(
              color: AppColors.labelColor,
              fontSize: 11,
              fontWeight: FontWeight.w600,
              letterSpacing: 1.5,
            ),
          ),
          const SizedBox(height: 16),

          // 2×2 info grid
          Row(
            children: [
              Expanded(child: _InfoCell(label: 'MODULE',     value: camera.moduleId)),
              Expanded(child: _InfoCell(label: 'RESOLUTION', value: camera.resolution)),
            ],
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(child: _InfoCell(label: 'LATENCY',    value: camera.latency)),
              Expanded(child: _InfoCell(label: 'NIGHT MODE', value: camera.nightMode)),
            ],
          ),
        ],
      ),
    );
  }
}

class _InfoCell extends StatelessWidget {
  final String label;
  final String value;

  const _InfoCell({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: const TextStyle(
            color: AppColors.labelColor,
            fontSize: 10,
            fontWeight: FontWeight.w600,
            letterSpacing: 1.2,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          value,
          style: const TextStyle(
            color: AppColors.textPrimary,
            fontSize: 16,
            fontWeight: FontWeight.w700,
            fontFamily: 'monospace',
          ),
        ),
      ],
    );
  }
}