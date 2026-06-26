import 'package:flutter/material.dart';
import '../../core/constants/app_colors.dart';

// ── Enums ─────────────────────────────────────────────────────────────────────

enum AlertSeverity { critical, warning, info }

enum AlertCategory { engine, gps, door, system }

extension AlertCategoryX on AlertCategory {
  String get label {
    switch (this) {
      case AlertCategory.engine: return 'Engine';
      case AlertCategory.gps:    return 'GPS';
      case AlertCategory.door:   return 'Door';
      case AlertCategory.system: return 'System';
    }
  }
}

// ── Model ─────────────────────────────────────────────────────────────────────

class AlertModel {
  final String id;
  final String title;
  final String description;   // ← kept original field name — nothing breaks
  final DateTime timestamp;
  final AlertSeverity severity;
  final AlertCategory category;
  final bool isRead;

  const AlertModel({
    required this.id,
    required this.title,
    required this.description,
    required this.timestamp,
    required this.severity,
    this.category = AlertCategory.system,
    this.isRead   = false,
  });

  // subtitle is a transparent alias — alerts_screen uses this, old widgets use description
  String get subtitle => description;

  AlertModel copyWith({bool? isRead}) => AlertModel(
        id:          id,
        title:       title,
        description: description,
        timestamp:   timestamp,
        severity:    severity,
        category:    category,
        isRead:      isRead ?? this.isRead,
      );

  // ── Derived display props ─────────────────────────────────────────────────

  IconData get icon {
    switch (category) {
      case AlertCategory.engine: return Icons.power_settings_new_rounded;
      case AlertCategory.gps:    return Icons.location_on_outlined;
      case AlertCategory.door:   return Icons.lock_outline_rounded;
      case AlertCategory.system: return Icons.warning_amber_rounded;
    }
  }

  Color get iconColor {
    switch (category) {
      case AlertCategory.engine: return AppColors.accentBlue;
      case AlertCategory.gps:    return AppColors.statusGreen;
      case AlertCategory.door:   return AppColors.statusAmber;
      case AlertCategory.system: return AppColors.statusRed;
    }
  }

  Color get iconBg {
    switch (category) {
      case AlertCategory.engine: return AppColors.iconBlueBg;
      case AlertCategory.gps:    return AppColors.statusGreenBg;
      case AlertCategory.door:   return AppColors.statusAmberBg;
      case AlertCategory.system: return AppColors.statusRedBg;
    }
  }

  Color get borderColor {
    switch (category) {
      case AlertCategory.engine: return AppColors.accentBlue.withOpacity(0.25);
      case AlertCategory.gps:    return AppColors.statusGreen.withOpacity(0.25);
      case AlertCategory.door:   return AppColors.statusAmber.withOpacity(0.25);
      case AlertCategory.system: return AppColors.statusRed.withOpacity(0.25);
    }
  }

  // identical to original
  String get timeAgo {
    final diff = DateTime.now().difference(timestamp);
    if (diff.inMinutes < 60) return '${diff.inMinutes} min ago';
    if (diff.inHours < 24)   return '${diff.inHours} hr ago';
    return '${diff.inDays} days ago';
  }

  // identical signature to original mock()
  static AlertModel mock() => AlertModel(
        id:          '1',
        title:       'Unauthorized Ignition Attempt',
        description: 'Ignition attempt blocked by SmartGuard',
        timestamp:   DateTime.now().subtract(const Duration(minutes: 2)),
        severity:    AlertSeverity.critical,
        category:    AlertCategory.engine,
        isRead:      false,
      );

  // new — only used by AlertsScreen
  static List<AlertModel> mockList() {
    final now = DateTime.now();
    return [
      AlertModel(
        id: 'a1', title: 'Unauthorized Ignition Attempt',
        description: 'Ignition attempt blocked by SmartGuard',
        category: AlertCategory.engine, severity: AlertSeverity.critical,
        timestamp: now.subtract(const Duration(minutes: 2)), isRead: false,
      ),
      AlertModel(
        id: 'a2', title: 'Driver Door Opened',
        description: 'Front-left door opened while parked',
        category: AlertCategory.door, severity: AlertSeverity.warning,
        timestamp: now.subtract(const Duration(minutes: 18)), isRead: false,
      ),
      AlertModel(
        id: 'a3', title: 'Geofence Breached',
        description: 'Vehicle left safe zone boundary (Home)',
        category: AlertCategory.gps, severity: AlertSeverity.warning,
        timestamp: now.subtract(const Duration(hours: 1)), isRead: false,
      ),
      AlertModel(
        id: 'a4', title: 'Battery Voltage Low',
        description: 'Battery at 11.8V — check vehicle',
        category: AlertCategory.system, severity: AlertSeverity.warning,
        timestamp: now.subtract(const Duration(hours: 3)), isRead: true,
      ),
      AlertModel(
        id: 'a5', title: 'Trunk Opened',
        description: 'Trunk opened unexpectedly at 02:14',
        category: AlertCategory.door, severity: AlertSeverity.warning,
        timestamp: now.subtract(const Duration(hours: 5)), isRead: true,
      ),
      AlertModel(
        id: 'a6', title: 'GPS Signal Lost',
        description: 'Tracker lost satellite connection',
        category: AlertCategory.gps, severity: AlertSeverity.info,
        timestamp: now.subtract(const Duration(hours: 8)), isRead: true,
      ),
    ];
  }
}