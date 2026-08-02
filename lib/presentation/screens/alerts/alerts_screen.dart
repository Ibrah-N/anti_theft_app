// lib/presentation/screens/alerts/alerts_screen.dart

import 'package:flutter/material.dart';
import '../../../core/constants/app_colors.dart';
import '../../../data/models/alert_model.dart';
import '../../widgets/alerts/alert_filter_chip.dart';
import '../../widgets/alerts/alert_list_tile.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../data/providers/alerts_provider.dart';

const List<AlertCategory?> _kFilters = [
  null,
  AlertCategory.engine,
  AlertCategory.gps,
  AlertCategory.door,
  AlertCategory.system,
];

String _filterLabel(AlertCategory? c) => c == null ? 'All' : c.label;

class AlertsScreen extends ConsumerStatefulWidget {
  const AlertsScreen({super.key});

  @override
  ConsumerState<AlertsScreen> createState() => _AlertsScreenState();
}

class _AlertsScreenState extends ConsumerState<AlertsScreen> {
  AlertCategory? _activeFilter;

  List<AlertModel> _filtered(List<AlertModel> alerts) => _activeFilter == null
      ? alerts
      : alerts.where((a) => a.category == _activeFilter).toList();

  void _markAsRead(String id) {
    ref.read(alertsProvider.notifier).markRead(int.parse(id));
  }

  void _markAllRead() {
    ref.read(alertsProvider.notifier).markAllRead();
  }

  @override
  Widget build(BuildContext context) {
    final alertsState = ref.watch(alertsProvider);

    final content = SafeArea(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // ── Header ──────────────────────────────────────────────────────
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
                        alertsState.unreadCount > 0
                            ? '${alertsState.unreadCount} unread alert${alertsState.unreadCount > 1 ? 's' : ''}'
                            : 'All caught up',
                        style: TextStyle(
                          color: alertsState.unreadCount > 0
                              ? AppColors.statusRed
                              : AppColors.statusGreen,
                          fontSize: 14,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ],
                  ),
                ),
                if (alertsState.unreadCount > 0)
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

          // ── Filter chips ──────────────────────────────────────────────
          SizedBox(
            height: 40,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 16),
              itemCount: _kFilters.length,
              separatorBuilder: (_, _) => const SizedBox(width: 8),
              itemBuilder: (_, i) {
                final filter = _kFilters[i];
                return AlertFilterChip(
                  label: _filterLabel(filter),
                  isActive: _activeFilter == filter,
                  onTap: () {
                    setState(() => _activeFilter = filter);
                    ref.read(alertsProvider.notifier).load(
                      category: filter?.label.toLowerCase(),
                    );
                  },
                );
              },
            ),
          ),
          const SizedBox(height: 16),

          // ── Alert list ────────────────────────────────────────────────
          Expanded(
            child: RefreshIndicator(
                onRefresh: () => ref.read(alertsProvider.notifier).load(),
                child: alertsState.isLoading
                ? const Center(
                    child: CircularProgressIndicator(
                        color: AppColors.primaryBlue))
                    : alertsState.error != null
                      ? Center(
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              const Text('Cannot reach server — check your connection',
                                  style: TextStyle(color: AppColors.statusRed)),
                              const SizedBox(height: 12),
                              TextButton(
                                onPressed: () => ref.read(alertsProvider.notifier).load(),
                                child: const Text('Retry'),
                              ),
                            ],
                          ),
                        )
                    : _filtered(alertsState.alerts).isEmpty
                        ? _buildEmptyState()
                        : ListView.separated(
                            physics: const AlwaysScrollableScrollPhysics(),
                            padding:
                                const EdgeInsets.fromLTRB(16, 0, 16, 24),
                            itemCount:
                                _filtered(alertsState.alerts).length,
                            separatorBuilder: (_, _) =>
                                const SizedBox(height: 10),
                            itemBuilder: (_, i) {
                              final alert =
                                  _filtered(alertsState.alerts)[i];
                              return AlertListTile(
                                alert: alert,
                                onTap: () => _markAsRead(alert.id),
                              );
                            },
                          ),
          ),
          ),
        ],
      ),
    );

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