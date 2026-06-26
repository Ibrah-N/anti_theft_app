enum AlertSeverity { critical, warning, info }

class AlertModel {
  final String id;
  final String title;
  final String description;
  final DateTime timestamp;
  final AlertSeverity severity;

  const AlertModel({
    required this.id,
    required this.title,
    required this.description,
    required this.timestamp,
    required this.severity,
  });

  String get timeAgo {
    final diff = DateTime.now().difference(timestamp);
    if (diff.inMinutes < 60) return '${diff.inMinutes} min ago';
    if (diff.inHours < 24)   return '${diff.inHours} hr ago';
    return '${diff.inDays} days ago';
  }

  static AlertModel mock() => AlertModel(
    id: '1',
    title: 'Unauthorized Ignition Attempt',
    description: 'Ignition attempt blocked by SmartGuard',
    timestamp: DateTime.now().subtract(const Duration(minutes: 2)),
    severity: AlertSeverity.critical,
  );
}