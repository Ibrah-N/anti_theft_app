import 'package:flutter/material.dart';

import 'routes.dart';



class LoginPage extends StatelessWidget {
  const LoginPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Material(
      
      child: Column(
        
        children: [

          const SizedBox(height: 70.0),
          const Text(
            "Login Page",
            textDirection: TextDirection.ltr,
            style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold),
            textAlign: TextAlign.right,
          ),


          const SizedBox(height: 20.0),

          Image.asset(
            "assets/images/images.jpeg",
            width: 400.0,
            height: 400.0,
          ), 
          

          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 10.0),
            child: Column(
              children: [

              TextFormField(
                decoration: const InputDecoration(
                  hintText: "Enter Username",
                  labelText: "Username",
                ),
              ),


              TextFormField(
                obscureText: true,
                decoration: const InputDecoration(
                  hintText: "Enter Password",
                  labelText: "Password",
                ),
              ),
            ],)
          ),

          ElevatedButton(
          onPressed: () {
            Navigator.pushNamed(
              context, 
              MyRoutes.home
            );
          },
          style: ElevatedButton.styleFrom(
            minimumSize: const Size(double.infinity, 50.0),
            backgroundColor: Colors.blue,
          ),
          child: const Text(
            "Login",
            style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Colors.white),
          ),
        )



        ])
    ); // materila 
  }
}