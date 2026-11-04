// lib/presentation/widgets/camera/event_status_banner.dart
//
// Shown on the camera screen while the camera is recording or uploading an
// EVENT clip (started by a suspicious event, not by the user). Hidden when idle.

import 'package:flutter/material.dart';
import '../../../core/constants/app_colors.dart';
import '../../../data/providers/camera_event_provider.dart';

class EventStatusBanner extends StatelessWidget {
  final CameraEventState event;
  const EventStatusBanner({super.key, required this.event});

  String _elapsed(double? s) {
    if (s == null) return '';
    final t = s.round();
    final m = (t ~/ 60).toString().padLeft(2, '0');
    final sec = (t % 60).toString().padLeft(2, '0');
    return '$m:$sec';
  }

  @override
  Widget build(BuildContext context) {
    if (!event.isRecording && !event.isUploading) return const SizedBox.shrink();

    final recording = event.isRecording;
    final color = recording ? AppColors.statusRed : AppColors.statusAmber;
    final bg    = recording ? AppColors.statusRedBg : AppColors.statusAmberBg;

    final title = recording ? 'Event recording in progress' : 'Uploading event video';
    final parts = <String>[
      if (event.reasonLabel != null) event.reasonLabel!,
      if (recording && event.elapsedSeconds != null) _elapsed(event.elapsedSeconds),
      if (!recording && event.segmentsTotal != null)
        'part ${event.segmentsUploaded ?? 0} of ${event.segmentsTotal}',
    ];
    final hint = recording
        ? 'Opening the live stream will stop and save this video first.'
        : 'It will appear in your saved media when finished.';

    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(top: 14),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withValues(alpha: 0.4)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.only(top: 2),
            child: Icon(
              recording ? Icons.fiber_manual_record_rounded : Icons.cloud_upload_rounded,
              color: color,
              size: 16,
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  parts.isEmpty ? title : '$title · ${parts.join(' · ')}',
                  style: TextStyle(color: color, fontSize: 13, fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 3),
                Text(hint,
                    style: const TextStyle(color: AppColors.textSecondary, fontSize: 11.5)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}