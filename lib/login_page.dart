import 'package:flutter/material.dart';

import 'routes.dart';



class LoginPage extends StatefulWidget {
  const LoginPage({super.key});

  @override
  State<LoginPage> createState() => _LoginPageState();
}


class _LoginPageState extends State<LoginPage> {

  // variables 
  double boarderRadius = 5.0;
  double boxWidth = 100;
  double boxHeight = 50;
  bool isLoginPressed = false;

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


        // #### Container Button to navigate to Home Page ####
        InkWell(
            onTap: () async {
            
            setState(() {
              boarderRadius = 50.0;
              boxWidth = 70;
              boxHeight = 50;
              isLoginPressed = true;
            });

            await Future.delayed(const Duration(seconds: 1));


            Navigator.pushNamed(
              context,
              MyRoutes.home
            );            
          },

          child: AnimatedContainer(
            duration: const Duration(seconds: 1),
            width: boxWidth,
            height: boxHeight,
            alignment: Alignment.center,
            decoration: BoxDecoration(
            color: isLoginPressed ? Colors.green : Colors.blue,
            borderRadius: BorderRadius.circular(boarderRadius),
          ),
          
          child: Text(
            "Login",

            style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Colors.white),
          )))


        // #### Elevated Button to navigate to Home Page ####
        //   ElevatedButton(
        //   onPressed: () {
        //     Navigator.pushNamed(
        //       context, 
        //       MyRoutes.home
        //     );
        //   },
        //   style: ElevatedButton.styleFrom(
        //     minimumSize: const Size(double.infinity, 50.0),
        //     backgroundColor: Colors.blue,
        //   ),
        //   child: const Text(
        //     "Login",
        //     style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Colors.white),
        //   ),
        // )



        ])
    ); // materila 
  }
}