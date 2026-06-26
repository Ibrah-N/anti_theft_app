class DeviceSettings {
  final String deviceId;
  final String network;
  final String heartbeatInterval;
  final String protocol;

  const DeviceSettings({
    required this.deviceId,
    required this.network,
    required this.heartbeatInterval,
    required this.protocol,
  });

  static DeviceSettings mock() => const DeviceSettings(
    deviceId: 'SG-0847A',
    network: 'WiFi + GSM',
    heartbeatInterval: '30s interval',
    protocol: 'MQTT / TLS 1.3',
  );
}

class SecuritySettings {
  final String authMethod;
  final String encryption;
  final String sessionTimeout;

  const SecuritySettings({
    required this.authMethod,
    required this.encryption,
    required this.sessionTimeout,
  });

  static SecuritySettings mock() => const SecuritySettings(
    authMethod: 'Biometric + PIN',
    encryption: 'AES-256',
    sessionTimeout: '15 minutes',
  );
}

class AccessSettings {
  final int sharedUsersCount;
  final String activityLogLabel;

  const AccessSettings({
    required this.sharedUsersCount,
    required this.activityLogLabel,
  });

  static AccessSettings mock() => const AccessSettings(
    sharedUsersCount: 2,
    activityLogLabel: 'View history',
  );
}