enum UserPlan { free, pro, enterprise }

class UserModel {
  final String name;
  final String email;
  final String role;
  final String pairedVehicle;
  final UserPlan plan;

  const UserModel({
    required this.name,
    required this.email,
    required this.role,
    required this.pairedVehicle,
    required this.plan,
  });

  String get planLabel {
    switch (plan) {
      case UserPlan.free:       return 'FREE';
      case UserPlan.pro:        return 'PRO';
      case UserPlan.enterprise: return 'ENT';
    }
  }

  // Step 2: replace with auth repository response
  static UserModel mock() => const UserModel(
    name: 'Alex Johnson',
    email: 'alex@email.com',
    role: 'Owner',
    pairedVehicle: 'Toyota Camry 2023',
    plan: UserPlan.pro,
  );
}