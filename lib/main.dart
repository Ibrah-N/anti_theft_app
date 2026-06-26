import 'package:flutter/material.dart';
import 'presentation/screens/home/home_screen.dart'; // ← change import

void main() => runApp(const SmartGuardApp());

class SmartGuardApp extends StatelessWidget {
  const SmartGuardApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SmartGuard',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(fontFamily: 'SF Pro Display'),
      home: const HomeScreen(), // ← point to home for now
    );
  }
}