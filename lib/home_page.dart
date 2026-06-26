import 'package:anti_theft/routes.dart';
import 'package:flutter/material.dart';


class HomePage extends StatelessWidget {
  const HomePage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
        appBar: AppBar(
          title: const Text('Flutter Demo Home Page'),
        ),

        body: Center(
          child: Column(children: [
            const Text(
              "Home Page",
              textDirection: TextDirection.ltr,
              style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
              textAlign: TextAlign.right,
            ),


            ElevatedButton(
              onPressed: () {
                Navigator.pushNamed(
                  context,
                  MyRoutes.login
                );
              },

              style: ElevatedButton.styleFrom(
                minimumSize: const Size(double.infinity, 50.0),
                backgroundColor: Colors.blue,
              ),
              
              child: const Text("Login Page"),
            ),
          ])
        )
      );
  }
}