import 'package:flutter/material.dart';
import '../../../core/constants/app_colors.dart';
import '../../../data/models/vehicle_model.dart';

// Keys to identify tappable zones
enum CarZone { bonnet, frontLeft, frontRight, rearLeft, rearRight, trunk }

class CarBlueprintPainter extends CustomPainter {
  final Map<CarZone, bool> zoneStates; // true = closed/green, false = open/red

  CarBlueprintPainter({required this.zoneStates});

  Color _zoneColor(CarZone zone) =>
      (zoneStates[zone] ?? true) ? AppColors.zoneClosed : AppColors.zoneOpen;

  Paint _borderPaint(CarZone zone) => Paint()
    ..color = _zoneColor(zone)
    ..style = PaintingStyle.stroke
    ..strokeWidth = 2.0
    ..maskFilter = MaskFilter.blur(BlurStyle.normal, 4);

  Paint _fillPaint(CarZone zone) => Paint()
    ..color = _zoneColor(zone).withOpacity(0.08)
    ..style = PaintingStyle.fill;

  Paint get _bodyPaint => Paint()
    ..color = const Color(0xFF0F1A2E)
    ..style = PaintingStyle.fill;

  Paint get _darkFill => Paint()
    ..color = const Color(0xFF0A1020)
    ..style = PaintingStyle.fill;

  @override
  void paint(Canvas canvas, Size size) {
    final w = size.width;
    final h = size.height;

    // Layout proportions
    final cx = w / 2;
    final bonnetH = h * 0.22;
    final trunkH = h * 0.22;
    final bodyTop = h * 0.25;
    final bodyBottom = h * 0.75;
    final bodyLeft = w * 0.22;
    final bodyRight = w * 0.78;
    final doorW = w * 0.10;
    final midY = (bodyTop + bodyBottom) / 2;

    // ── Car body background ───────────────────────────────
    final bodyRect = RRect.fromRectAndRadius(
      Rect.fromLTRB(bodyLeft, bodyTop, bodyRight, bodyBottom),
      const Radius.circular(8),
    );
    canvas.drawRRect(bodyRect, _bodyPaint);

    // ── BONNET ────────────────────────────────────────────
    final bonnetRect = RRect.fromRectAndRadius(
      Rect.fromLTRB(bodyLeft + 10, h * 0.01, bodyRight - 10, bonnetH + h * 0.01),
      const Radius.circular(14),
    );
    canvas.drawRRect(bonnetRect, _fillPaint(CarZone.bonnet));
    canvas.drawRRect(bonnetRect, _borderPaint(CarZone.bonnet));

    // BONNET label
    _drawZoneLabel(canvas, 'BONNET', 'CLOSED',
        Offset(cx, h * 0.01 + bonnetH / 2), _zoneColor(CarZone.bonnet));

    // ── TRUNK ─────────────────────────────────────────────
    final trunkRect = RRect.fromRectAndRadius(
      Rect.fromLTRB(bodyLeft + 10, h - trunkH - h * 0.01,
          bodyRight - 10, h - h * 0.01),
      const Radius.circular(14),
    );
    canvas.drawRRect(trunkRect, _fillPaint(CarZone.trunk));
    canvas.drawRRect(trunkRect, _borderPaint(CarZone.trunk));

    _drawZoneLabel(canvas, 'TRUNK', 'CLOSED',
        Offset(cx, h - trunkH / 2 - h * 0.01), _zoneColor(CarZone.trunk));

    // ── FRONT LEFT DOOR ───────────────────────────────────
    final flRect = RRect.fromRectAndRadius(
      Rect.fromLTRB(bodyLeft - doorW - 2, bodyTop + 8,
          bodyLeft - 2, midY - 4),
      const Radius.circular(8),
    );
    canvas.drawRRect(flRect, _fillPaint(CarZone.frontLeft));
    canvas.drawRRect(flRect, _borderPaint(CarZone.frontLeft));
    _drawRotatedLabel(canvas, 'F-LEFT', _zoneColor(CarZone.frontLeft),
        Offset(bodyLeft - doorW / 2 - 2, (bodyTop + 8 + midY - 4) / 2));

    // ── FRONT RIGHT DOOR ──────────────────────────────────
    final frRect = RRect.fromRectAndRadius(
      Rect.fromLTRB(bodyRight + 2, bodyTop + 8,
          bodyRight + doorW + 2, midY - 4),
      const Radius.circular(8),
    );
    canvas.drawRRect(frRect, _fillPaint(CarZone.frontRight));
    canvas.drawRRect(frRect, _borderPaint(CarZone.frontRight));
    _drawRotatedLabel(canvas, 'F-RIGHT', _zoneColor(CarZone.frontRight),
        Offset(bodyRight + doorW / 2 + 2, (bodyTop + 8 + midY - 4) / 2));

    // ── REAR LEFT DOOR ────────────────────────────────────
    final rlRect = RRect.fromRectAndRadius(
      Rect.fromLTRB(bodyLeft - doorW - 2, midY + 4,
          bodyLeft - 2, bodyBottom - 8),
      const Radius.circular(8),
    );
    canvas.drawRRect(rlRect, _fillPaint(CarZone.rearLeft));
    canvas.drawRRect(rlRect, _borderPaint(CarZone.rearLeft));
    _drawRotatedLabel(canvas, 'R-LEFT', _zoneColor(CarZone.rearLeft),
        Offset(bodyLeft - doorW / 2 - 2, (midY + 4 + bodyBottom - 8) / 2));

    // ── REAR RIGHT DOOR ───────────────────────────────────
    final rrRect = RRect.fromRectAndRadius(
      Rect.fromLTRB(bodyRight + 2, midY + 4,
          bodyRight + doorW + 2, bodyBottom - 8),
      const Radius.circular(8),
    );
    canvas.drawRRect(rrRect, _fillPaint(CarZone.rearRight));
    canvas.drawRRect(rrRect, _borderPaint(CarZone.rearRight));
    _drawRotatedLabel(canvas, 'R-RIGHT', _zoneColor(CarZone.rearRight),
        Offset(bodyRight + doorW / 2 + 2, (midY + 4 + bodyBottom - 8) / 2));

    // ── Interior cabin ────────────────────────────────────
    final cabinRect = Rect.fromLTRB(
        bodyLeft + 8, bodyTop + 12, bodyRight - 8, bodyBottom - 12);
    canvas.drawRRect(
      RRect.fromRectAndRadius(cabinRect, const Radius.circular(6)),
      _darkFill,
    );

    // Steering wheel
    final steeringCenter = Offset(cx - 18, bodyTop + (bodyBottom - bodyTop) * 0.32);
    canvas.drawCircle(steeringCenter, 16,
        Paint()..color = const Color(0xFF1E3A5F)..style = PaintingStyle.fill);
    canvas.drawCircle(steeringCenter, 16,
        Paint()..color = const Color(0xFF2563EB)..style = PaintingStyle.stroke..strokeWidth = 1.5);
    canvas.drawCircle(steeringCenter, 5,
        Paint()..color = const Color(0xFF2563EB)..style = PaintingStyle.fill);

    // Front seats
    _drawSeat(canvas, Offset(cx - 30, bodyTop + (bodyBottom - bodyTop) * 0.45));
    _drawSeat(canvas, Offset(cx + 20, bodyTop + (bodyBottom - bodyTop) * 0.45));

    // Rear seats (smaller)
    _drawSeat(canvas, Offset(cx - 30, bodyTop + (bodyBottom - bodyTop) * 0.70), small: true);
    _drawSeat(canvas, Offset(cx + 20, bodyTop + (bodyBottom - bodyTop) * 0.70), small: true);

    // ── Wheels (black rounded corners) ───────────────────
    _drawWheel(canvas, Offset(bodyLeft - 2, bodyTop + 2));
    _drawWheel(canvas, Offset(bodyRight + 2, bodyTop + 2), flipX: true);
    _drawWheel(canvas, Offset(bodyLeft - 2, bodyBottom - 2), bottom: true);
    _drawWheel(canvas, Offset(bodyRight + 2, bodyBottom - 2), flipX: true, bottom: true);
  }

  void _drawSeat(Canvas canvas, Offset center, {bool small = false}) {
    final r = small ? 12.0 : 14.0;
    canvas.drawRRect(
      RRect.fromRectAndRadius(
        Rect.fromCenter(center: center, width: r * 1.6, height: r * 2),
        const Radius.circular(6),
      ),
      Paint()..color = const Color(0xFF1A2A45)..style = PaintingStyle.fill,
    );
  }

  void _drawWheel(Canvas canvas, Offset corner,
      {bool flipX = false, bool bottom = false}) {
    final ww = 18.0;
    final wh = 22.0;
    final left = flipX ? corner.dx - ww : corner.dx - ww;
    final top = bottom ? corner.dy - wh : corner.dy;
    canvas.drawRRect(
      RRect.fromRectAndRadius(
        Rect.fromLTWH(left, top, ww, wh),
        const Radius.circular(5),
      ),
      Paint()..color = const Color(0xFF080D18)..style = PaintingStyle.fill,
    );
  }

  void _drawZoneLabel(Canvas canvas, String title, String sub,
      Offset center, Color color) {
    final tp = TextPainter(
      text: TextSpan(
        children: [
          TextSpan(
            text: '$title\n',
            style: TextStyle(
              color: color,
              fontSize: 11,
              fontWeight: FontWeight.w700,
              letterSpacing: 1.5,
            ),
          ),
          TextSpan(
            text: sub,
            style: TextStyle(
              color: color.withOpacity(0.7),
              fontSize: 9,
              letterSpacing: 1,
            ),
          ),
        ],
      ),
      textAlign: TextAlign.center,
      textDirection: TextDirection.ltr,
    )..layout();
    tp.paint(canvas, center - Offset(tp.width / 2, tp.height / 2));
  }

  void _drawRotatedLabel(Canvas canvas, String text, Color color, Offset center) {
    canvas.save();
    canvas.translate(center.dx, center.dy);
    canvas.rotate(-1.5708); // -90 degrees
    final tp = TextPainter(
      text: TextSpan(
        text: text,
        style: TextStyle(
          color: color,
          fontSize: 9,
          fontWeight: FontWeight.w600,
          letterSpacing: 1,
        ),
      ),
      textDirection: TextDirection.ltr,
    )..layout();
    tp.paint(canvas, Offset(-tp.width / 2, -tp.height / 2));
    canvas.restore();
  }

  @override
  bool shouldRepaint(CarBlueprintPainter oldDelegate) =>
      oldDelegate.zoneStates != zoneStates;
}

// ── Hit-test helper ────────────────────────────────────────────────────────
class CarZoneHitTester {
  final Size size;
  CarZoneHitTester(this.size);

  final double _bodyLeftFrac  = 0.22;
  final double _bodyRightFrac = 0.78;
  final double _bodyTopFrac   = 0.25;
  final double _bodyBotFrac   = 0.75;
  final double _doorWFrac     = 0.10;

  CarZone? hitTest(Offset local) {
    final w = size.width;
    final h = size.height;
    final bodyLeft  = w * _bodyLeftFrac;
    final bodyRight = w * _bodyRightFrac;
    final bodyTop   = h * _bodyTopFrac;
    final bodyBot   = h * _bodyBotFrac;
    final doorW     = w * _doorWFrac;
    final midY      = (bodyTop + bodyBot) / 2;

    if (_inRect(local, Rect.fromLTRB(bodyLeft + 10, h * 0.01, bodyRight - 10, h * 0.23)))
      return CarZone.bonnet;
    if (_inRect(local, Rect.fromLTRB(bodyLeft + 10, h * 0.77, bodyRight - 10, h * 0.99)))
      return CarZone.trunk;
    if (_inRect(local, Rect.fromLTRB(bodyLeft - doorW - 2, bodyTop + 8, bodyLeft - 2, midY - 4)))
      return CarZone.frontLeft;
    if (_inRect(local, Rect.fromLTRB(bodyRight + 2, bodyTop + 8, bodyRight + doorW + 2, midY - 4)))
      return CarZone.frontRight;
    if (_inRect(local, Rect.fromLTRB(bodyLeft - doorW - 2, midY + 4, bodyLeft - 2, bodyBot - 8)))
      return CarZone.rearLeft;
    if (_inRect(local, Rect.fromLTRB(bodyRight + 2, midY + 4, bodyRight + doorW + 2, bodyBot - 8)))
      return CarZone.rearRight;
    return null;
  }

  bool _inRect(Offset p, Rect r) => r.contains(p);
}