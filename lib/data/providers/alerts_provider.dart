// lib/data/providers/alerts_provider.dart

import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../data/models/alert_model.dart';
import '../services/api_service.dart';

// ── Alerts state ──────────────────────────────────────────────────────────────
class AlertsState {
final List<AlertModel> alerts;
final int              total;
final int              unreadCount;
final bool             isLoading;
final String?          error;

const AlertsState({
this.alerts      = const [],
this.total       = 0,
this.unreadCount = 0,
this.isLoading   = false,
this.error,
  });

AlertsState copyWith({
List<AlertModel>? alerts,
int?              total,
int?              unreadCount,
bool?             isLoading,
String?           error,
  }) =>
AlertsState(
alerts:      alerts      ?? this.alerts,
total:       total       ?? this.total,
unreadCount: unreadCount ?? this.unreadCount,
isLoading:   isLoading   ?? this.isLoading,
error:       error       ?? this.error,
      );
}

// ── Notifier ──────────────────────────────────────────────────────────────────
class AlertsNotifier extends StateNotifier<AlertsState> {
AlertsNotifier() : super(const AlertsState(isLoading: true)) {
load();
  }

Future<void> load({String? category}) async {
state = state.copyWith(isLoading: true, error: null);
try {
final data    = await ApiService.instance.getAlerts(category: category);
final alerts  = (data['alerts'] as List)
          .map((a) => AlertModel.fromJson(a))
          .toList();
state = AlertsState(
alerts:      alerts,
total:       data['total']        as int,
unreadCount: data['unread_count'] as int,
isLoading:   false,
      );
    } catch (e) {
state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

Future<void> markRead(int alertId) async {
await ApiService.instance.markAlertRead(alertId);
state = state.copyWith(
alerts: state.alerts
          .map((a) => a.id == alertId.toString()
? a.copyWith(isRead: true)
: a)
          .toList(),
unreadCount: (state.unreadCount - 1).clamp(0, 999),
    );
  }

Future<void> markAllRead() async {
await ApiService.instance.markAllAlertsRead();
state = state.copyWith(
alerts:      state.alerts.map((a) => a.copyWith(isRead: true)).toList(),
unreadCount: 0,
    );
  }

void prependAlert(AlertModel alert) {
state = state.copyWith(
alerts:      [alert, ...state.alerts],
total:       state.total + 1,
unreadCount: state.unreadCount + 1,
    );
  }
}

final alertsProvider =
StateNotifierProvider<AlertsNotifier, AlertsState>(
  (ref) => AlertsNotifier(),
);