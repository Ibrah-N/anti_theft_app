
import 'package:flutter/material.dart';
import '../../../core/constants/app_colors.dart';
import '../../../data/models/camera_model.dart';

class StreamViewer extends StatelessWidget {
  final CameraStatus status;

  const StreamViewer({super.key, required this.status});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      height: 220,
      decoration: BoxDecoration(
        color: AppColors.cardBg,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.borderColor),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(16),
        child: _buildContent(),
      ),
    );
  }

  Widget _buildContent() {
    switch (status) {
      case CameraStatus.offline:
        return _OfflineState();

      case CameraStatus.connecting:
        return _ConnectingState();

      case CameraStatus.streaming:
        // TODO Step 2: Replace with real MJPEG / WebRTC widget
        return _LivePlaceholder();
    }
  }
}

// ── Offline ────────────────────────────────────────────────────────────────
class _OfflineState extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Container(
          width: 72,
          height: 72,
          decoration: BoxDecoration(
            color: AppColors.inputBg,
            borderRadius: BorderRadius.circular(18),
          ),
          child: const Icon(
            Icons.photo_camera_outlined,
            color: AppColors.textSecondary,
            size: 32,
          ),
        ),
        const SizedBox(height: 16),
        const Text(
          'Camera offline',
          style: TextStyle(
            color: AppColors.textPrimary,
            fontSize: 16,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 6),
        const Text(
          'Tap Start Stream to connect',
          style: TextStyle(
            color: AppColors.textSecondary,
            fontSize: 13,
          ),
        ),
      ],
    );
  }
}

// ── Connecting ─────────────────────────────────────────────────────────────
class _ConnectingState extends StatefulWidget {
  @override
  State<_ConnectingState> createState() => _ConnectingStateState();
}

class _ConnectingStateState extends State<_ConnectingState>
    with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl;
  late final Animation<double> _pulse;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
        vsync: this, duration: const Duration(milliseconds: 900))
      ..repeat(reverse: true);
    _pulse = Tween(begin: 0.5, end: 1.0).animate(
        CurvedAnimation(parent: _ctrl, curve: Curves.easeInOut));
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        FadeTransition(
          opacity: _pulse,
          child: Container(
            width: 72,
            height: 72,
            decoration: BoxDecoration(
              color: AppColors.iconBlueBg,
              borderRadius: BorderRadius.circular(18),
            ),
            child: const Icon(
              Icons.photo_camera_outlined,
              color: AppColors.accentBlue,
              size: 32,
            ),
          ),
        ),
        const SizedBox(height: 16),
        const Text(
          'Connecting…',
          style: TextStyle(
            color: AppColors.textPrimary,
            fontSize: 16,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 6),
        const Text(
          'Establishing secure stream',
          style: TextStyle(color: AppColors.textSecondary, fontSize: 13),
        ),
      ],
    );
  }
}

// ── Live placeholder ────────────────────────────────────────────────────────
class _LivePlaceholder extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Stack(
      fit: StackFit.expand,
      children: [
        // Replace this Container with your actual video widget in Step 2
        Container(color: Colors.black),

        // Live badge
        Positioned(
          top: 12,
          left: 12,
          child: Container(
            padding:
                const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: AppColors.statusRed,
              borderRadius: BorderRadius.circular(6),
            ),
            child: const Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.circle, color: Colors.white, size: 8),
                SizedBox(width: 5),
                Text('LIVE',
                    style: TextStyle(
                        color: Colors.white,
                        fontSize: 11,
                        fontWeight: FontWeight.bold,
                        letterSpacing: 1.2)),
              ],
            ),
          ),
        ),
      ],
    );
  }
}