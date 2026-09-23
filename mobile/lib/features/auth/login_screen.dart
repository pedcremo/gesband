import 'package:flutter/material.dart';

import '../../core/app_controller.dart';
import '../../core/localization/app_strings.dart';
import '../../core/localization/language_menu.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key, required this.controller});
  final AppController controller;
  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final email = TextEditingController();
  final password = TextEditingController();

  @override
  void dispose() {
    email.dispose();
    password.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    return Scaffold(
      appBar: AppBar(actions: const [LanguageMenu()]),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 420),
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              const FlutterLogo(size: 64),
              const SizedBox(height: 16),
              Text(strings.appName,
                  style: TextStyle(fontSize: 32, fontWeight: FontWeight.bold)),
              TextField(
                  controller: email,
                  keyboardType: TextInputType.emailAddress,
                  decoration: InputDecoration(labelText: strings.email)),
              TextField(
                  controller: password,
                  obscureText: true,
                  decoration: InputDecoration(labelText: strings.password)),
              if (widget.controller.error != null)
                Padding(
                    padding: const EdgeInsets.only(top: 12),
                    child: Text(strings.message(widget.controller.error!),
                        style: TextStyle(
                            color: Theme.of(context).colorScheme.error))),
              const SizedBox(height: 20),
              SizedBox(
                  width: double.infinity,
                  child: FilledButton(
                      onPressed: () =>
                          widget.controller.login(email.text, password.text),
                      child: Text(strings.signIn))),
            ]),
          ),
        ),
      ),
    );
  }
}
