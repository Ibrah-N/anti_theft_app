import 'package:flutter/material.dart';
import '../../../core/constants/app_colors.dart';

/// Animated pulsing geofence ring — overlaid on the map
/// In Step 2: radius comes from geofence config stored in your DB
class GeofenceRing extends StatefulWidget {
  final double radiusMeters;   // real-world radius in metres

  const GeofenceRing({super.key, this.radiusMeters = 100});

  @override
  State<GeofenceRing> createState() => _GeofenceRingState();
}

class _GeofenceRingState extends State<GeofenceRing>
    with SingleTickerProviderStateMixin {
  late AnimationController _ctrl;
  late Animation<double> _pulse;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat();
    _pulse = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _ctrl, curve: Curves.easeOut),
    );
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _pulse,
      builder: (_, __) => CustomPaint(
        painter: _GeofencePainter(pulse: _pulse.value),
      ),
    );
  }
}

class _GeofencePainter extends CustomPainter {
  final double pulse;
  _GeofencePainter({required this.pulse});

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final baseR  = size.shortestSide * 0.38;

    // Filled pulse wave
    canvas.drawCircle(
      center,
      baseR + pulse * 16,
      Paint()
        ..color = AppColors.accentBlue.withOpacity((1 - pulse) * 0.12)
        ..style = PaintingStyle.fill,
    );

    // Dashed border
    _drawDashed(canvas, center, baseR);
  }

  void _drawDashed(Canvas canvas, Offset center, double r) {
    const segments = 40;
    const gap = 0.35;
    const step = (2 * 3.14159) / segments;
    final paint = Paint()
      ..color = AppColors.accentBlue.withOpacity(0.6)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.5;
    for (int i = 0; i < segments; i++) {
      final start = i * step;
      canvas.drawArc(
        Rect.fromCircle(center: center, radius: r),
        start,
        step * (1 - gap),
        false,
        paint,
      );
    }
  }

  @override
  bool shouldRepaint(_GeofencePainter old) => old.pulse != pulse;
}