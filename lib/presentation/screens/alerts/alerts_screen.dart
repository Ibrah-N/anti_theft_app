// lib/presentation/screens/alerts/alerts_screen.dart

import 'package:flutter/material.dart';
import '../../../core/constants/app_colors.dart';
import '../../../data/models/alert_model.dart';
import '../../widgets/alerts/alert_filter_chip.dart';
import '../../widgets/alerts/alert_list_tile.dart';

const List<AlertCategory?> _kFilters = [
  null,
  AlertCategory.engine,
  AlertCategory.gps,
  AlertCategory.door,
  AlertCategory.system,
];

String _filterLabel(AlertCategory? c) => c == null ? 'All' : c.label;

class AlertsScreen extends StatefulWidget {
  final bool standalone;
  const AlertsScreen({super.key, this.standalone = true});

  @override
  State<AlertsScreen> createState() => _AlertsScreenState();
}

class _AlertsScreenState extends State<AlertsScreen> {
  AlertCategory? _activeFilter;
  late List<AlertModel> _alerts;

  @override
  void initState() {
    super.initState();
    _alerts = AlertModel.mockList();
  }

  List<AlertModel> get _filtered => _activeFilter == null
      ? _alerts
      : _alerts.where((a) => a.category == _activeFilter).toList();

  int get _unreadCount => _alerts.where((a) => !a.isRead).length;

  void _markAsRead(String id) {
    setState(() {
      _alerts = _alerts
          .map((a) => a.id == id ? a.copyWith(isRead: true) : a)
          .toList();
    });
  }

  void _markAllRead() {
    setState(() {
      _alerts = _alerts.map((a) => a.copyWith(isRead: true)).toList();
    });
  }

  @override
  Widget build(BuildContext context) {
    final content = SafeArea(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 20, 16, 0),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('Security Alerts',
                          style: TextStyle(
                              color: AppColors.textPrimary,
                              fontSize: 28,
                              fontWeight: FontWeight.w800)),
                      const SizedBox(height: 4),
                      Text(
                        _unreadCount > 0
                            ? '$_unreadCount unread alert${_unreadCount > 1 ? 's' : ''}'
                            : 'All caught up',
                        style: TextStyle(
                          color: _unreadCount > 0
                              ? AppColors.statusRed
                              : AppColors.statusGreen,
                          fontSize: 14,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ],
                  ),
                ),
                if (_unreadCount > 0)
                  GestureDetector(
                    onTap: _markAllRead,
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 12, vertical: 7),
                      decoration: BoxDecoration(
                        color: AppColors.cardBg,
                        borderRadius: BorderRadius.circular(10),
                        border: Border.all(color: AppColors.borderColor),
                      ),
                      child: const Text('Mark all read',
                          style: TextStyle(
                              color: AppColors.textSecondary,
                              fontSize: 12,
                              fontWeight: FontWeight.w500)),
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          SizedBox(
            height: 40,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 16),
              itemCount: _kFilters.length,
              separatorBuilder: (_, __) => const SizedBox(width: 8),
              itemBuilder: (_, i) {
                final filter = _kFilters[i];
                return AlertFilterChip(
                  label: _filterLabel(filter),
                  isActive: _activeFilter == filter,
                  onTap: () => setState(() => _activeFilter = filter),
                );
              },
            ),
          ),
          const SizedBox(height: 16),
          Expanded(
            child: _filtered.isEmpty
                ? _buildEmptyState()
                : ListView.separated(
                    padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
                    itemCount: _filtered.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 10),
                    itemBuilder: (_, i) {
                      final alert = _filtered[i];
                      return AlertListTile(
                        alert: alert,
                        onTap: () => _markAsRead(alert.id),
                      );
                    },
                  ),
          ),
        ],
      ),
    );

    if (widget.standalone) {
      return Scaffold(backgroundColor: AppColors.scaffoldBg, body: content);
    }
    return content;
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 72, height: 72,
            decoration: BoxDecoration(
                color: AppColors.cardBg,
                shape: BoxShape.circle,
                border: Border.all(color: AppColors.borderColor)),
            child: const Icon(Icons.notifications_off_outlined,
                color: AppColors.textMuted, size: 30),
          ),
          const SizedBox(height: 16),
          const Text('No alerts',
              style: TextStyle(
                  color: AppColors.textPrimary,
                  fontSize: 16,
                  fontWeight: FontWeight.w600)),
          const SizedBox(height: 6),
          Text(
            _activeFilter == null
                ? 'Your vehicle is running clean'
                : 'No ${_filterLabel(_activeFilter)} alerts',
            style: const TextStyle(color: AppColors.textSecondary, fontSize: 13),
          ),
        ],
      ),
    );
  }
}