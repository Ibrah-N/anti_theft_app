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
  final bool isArmed;
  final bool doorsLocked;
  final bool mirrorFl;        // true = folded
  final bool mirrorFr;
  final bool mirrorRl;
  final bool mirrorRr;
  final bool engineStarted;   // starter motor relay
  final bool acOn;

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
    required this.isArmed,
    required this.doorsLocked,
    required this.mirrorFl,
    required this.mirrorFr,
    required this.mirrorRl,
    required this.mirrorRr,
    required this.engineStarted,
    required this.acOn,
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
    isArmed: true,
    doorsLocked: true,
    mirrorFl: true,
    mirrorFr: true,
    mirrorRl: true,
    mirrorRr: true,
    engineStarted: false,
    acOn: false,
  );


  // ── fromJson — maps backend response to VehicleModel ──────────────────────
  factory VehicleModel.fromJson(Map<String, dynamic> json) => VehicleModel(
    name:         json['name']          as String,
    regNumber:    json['reg_number']    as String,
    isOnline:     true,
    connectivity: 'GSM+WiFi',
    batteryVolts: (json['battery_level'] as num).toDouble(),
    zones: [
      ZoneStatus(label: 'FL',  isClosed: json['zone_fl']     as bool),
      ZoneStatus(label: 'FR',  isClosed: json['zone_fr']     as bool),
      ZoneStatus(label: 'RL',  isClosed: json['zone_rl']     as bool),
      ZoneStatus(label: 'RR',  isClosed: json['zone_rr']     as bool),
      ZoneStatus(label: 'BNT', isClosed: json['zone_bonnet'] as bool),
      ZoneStatus(label: 'TRK', isClosed: json['zone_trunk']  as bool),
    ],
    engineOn:     json['engine_on']     as bool,
    fuelFlowing:  json['fuel_flowing']  as bool,
    speedKmh:     (json['speed_kmh']    as num).toDouble(),
    batteryLevel: (json['battery_level'] as num).toDouble(),
    signalBars:   json['signal_bars']   as int,
    isArmed:       json['is_armed']       as bool,
    doorsLocked:   json['doors_locked']   as bool,
    mirrorFl:      json['mirror_fl']      as bool,
    mirrorFr:      json['mirror_fr']      as bool,
    mirrorRl:      json['mirror_rl']      as bool,
    mirrorRr:      json['mirror_rr']      as bool,
    engineStarted: json['engine_started'] as bool,
    acOn:          json['ac_on']          as bool,
  );

  // ── copyWithJson — merge partial WebSocket update into existing model ──────
  VehicleModel copyWithJson(Map<String, dynamic> json) => VehicleModel(
    name:         name,
    regNumber:    regNumber,
    isOnline:     isOnline,
    connectivity: connectivity,
    batteryVolts: (json['battery_level'] as num?)?.toDouble() ?? batteryVolts,
    zones: [
      ZoneStatus(label: 'FL',  isClosed: json['zone_fl']     as bool? ?? zones[0].isClosed),
      ZoneStatus(label: 'FR',  isClosed: json['zone_fr']     as bool? ?? zones[1].isClosed),
      ZoneStatus(label: 'RL',  isClosed: json['zone_rl']     as bool? ?? zones[2].isClosed),
      ZoneStatus(label: 'RR',  isClosed: json['zone_rr']     as bool? ?? zones[3].isClosed),
      ZoneStatus(label: 'BNT', isClosed: json['zone_bonnet'] as bool? ?? zones[4].isClosed),
      ZoneStatus(label: 'TRK', isClosed: json['zone_trunk']  as bool? ?? zones[5].isClosed),
    ],
    engineOn:     json['engine_on']     as bool?  ?? engineOn,
    fuelFlowing:  json['fuel_flowing']  as bool?  ?? fuelFlowing,
    speedKmh:     (json['speed_kmh']    as num?)?.toDouble() ?? speedKmh,
    batteryLevel: (json['battery_level'] as num?)?.toDouble() ?? batteryLevel,
    signalBars:   json['signal_bars']   as int?   ?? signalBars,
    isArmed:       json['is_armed']       as bool? ?? isArmed,
    doorsLocked:   json['doors_locked']   as bool? ?? doorsLocked,
    mirrorFl:      json['mirror_fl']      as bool? ?? mirrorFl,
    mirrorFr:      json['mirror_fr']      as bool? ?? mirrorFr,
    mirrorRl:      json['mirror_rl']      as bool? ?? mirrorRl,
    mirrorRr:      json['mirror_rr']      as bool? ?? mirrorRr,
    engineStarted: json['engine_started'] as bool? ?? engineStarted,
    acOn:          json['ac_on']          as bool? ?? acOn,
  );
}