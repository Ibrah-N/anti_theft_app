import 'package:flutter/material.dart';
import 'presentation/screens/auth/login_screen.dart';

void main() => runApp(const SmartGuardApp());

class SmartGuardApp extends StatelessWidget {
  const SmartGuardApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SmartGuard',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(fontFamily: 'SF Pro Display'),
      home: const LoginScreen(), // ← was HomeScreen()
    );
  }
}