class ZoneStatus {
  final String label;   // FL, FR, RL, RR, BNT, TRK
  final bool isClosed;  // true = green, false = red

  const ZoneStatus({required this.label, required this.isClosed});
}

class VehicleModel {
  final String name;          // Toyota Camry 2023
  final String regNumber;     // TYC-2023-0847A
  final bool isOnline;
  final String connectivity;  // GSM+WiFi
  final double batteryVolts;
  final List<ZoneStatus> zones;
  final bool engineOn;
  final bool fuelFlowing;     // true = FLOW, false = CUT
  final double speedKmh;
  final double batteryLevel;
  final int signalBars;       // out of 4

  const VehicleModel({
    required this.name,
    required this.regNumber,
    required this.isOnline,
    required this.connectivity,
    required this.batteryVolts,
    required this.zones,
    required this.engineOn,
    required this.fuelFlowing,
    required this.speedKmh,
    required this.batteryLevel,
    required this.signalBars,
  });

  // Mock data — replaces with real API in Step 2
  static VehicleModel mock() => VehicleModel(
    name: 'Toyota Camry 2023',
    regNumber: 'TYC-2023-0847A',
    isOnline: true,
    connectivity: 'GSM+WiFi',
    batteryVolts: 12.6,
    zones: const [
      ZoneStatus(label: 'FL',  isClosed: true),
      ZoneStatus(label: 'FR',  isClosed: true),
      ZoneStatus(label: 'RL',  isClosed: true),
      ZoneStatus(label: 'RR',  isClosed: true),
      ZoneStatus(label: 'BNT', isClosed: true),
      ZoneStatus(label: 'TRK', isClosed: true),
    ],
    engineOn: false,
    fuelFlowing: true,
    speedKmh: 0,
    batteryLevel: 12.6,
    signalBars: 3,
  );
}