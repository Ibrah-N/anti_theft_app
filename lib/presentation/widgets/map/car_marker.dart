import 'package:flutter/material.dart';
import '../../../core/constants/app_colors.dart';

/// The blue teardrop pin that sits on the real map tile
class CarMarkerWidget extends StatelessWidget {
  final bool isMoving;

  const CarMarkerWidget({super.key, this.isMoving = false});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 48,
      height: 64,
      child: Stack(
        alignment: Alignment.center,
        children: [
          // Glow behind pin
          Container(
            width: 48,
            height: 48,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              boxShadow: [
                BoxShadow(
                  color: AppColors.accentBlue.withOpacity(0.4),
                  blurRadius: 20,
                  spreadRadius: 4,
                ),
              ],
            ),
          ),

          // Custom teardrop shape
          CustomPaint(
            size: const Size(36, 52),
            painter: _TeardropPainter(),
          ),

          // Car icon inside pin
          Positioned(
            top: 6,
            child: Icon(
              isMoving
                  ? Icons.navigation_rounded
                  : Icons.directions_car_rounded,
              color: Colors.white,
              size: 18,
            ),
          ),
        ],
      ),
    );
  }
}

class _TeardropPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = AppColors.primaryBlue
      ..style = PaintingStyle.fill;

    final path = Path();
    final cx = size.width / 2;

    // Rounded top → tapers to point at bottom
    path.moveTo(cx, size.height);           // bottom point
    path.cubicTo(
      cx - size.width * 0.6, size.height * 0.65,
      cx - size.width * 0.6, size.height * 0.1,
      cx, 0,
    );
    path.cubicTo(
      cx + size.width * 0.6, size.height * 0.1,
      cx + size.width * 0.6, size.height * 0.65,
      cx, size.height,
    );

    canvas.drawPath(path, paint);

    // Inner circle
    canvas.drawCircle(
      Offset(cx, size.height * 0.32),
      size.width * 0.22,
      Paint()
        ..color = Colors.white.withOpacity(0.25)
        ..style = PaintingStyle.fill,
    );
  }

  @override
  bool shouldRepaint(_TeardropPainter old) => false;
}