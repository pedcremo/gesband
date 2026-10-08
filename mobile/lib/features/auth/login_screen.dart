import 'package:flutter/material.dart';

import '../../core/app_controller.dart';
import '../../core/localization/app_strings.dart';
import '../../core/localization/language_menu.dart';
import '../../core/theme/gesband_tokens.dart';
import '../../core/theme/theme_controller.dart';
import '../../core/theme/visual_style.dart';
import '../../core/ui/brand_logo.dart';
import '../../core/ui/components.dart';

/// Acceso con la marca de la última banda usada en el dispositivo o, si no
/// hay ninguna, la de Gesband.
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

  void _submit() => widget.controller.login(email.text, password.text);

  @override
  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    final t = GesbandTokens.of(context);
    final text = Theme.of(context).textTheme;
    final brand = ThemeScope.brandOf(context);
    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            const Align(
              alignment: AlignmentDirectional.centerEnd,
              child: Padding(
                padding: EdgeInsets.all(GesbandSpacing.xs),
                child: LanguageMenu(),
              ),
            ),
            Expanded(
              child: Center(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.fromLTRB(GesbandSpacing.xxl, 0,
                      GesbandSpacing.xxl, GesbandSpacing.xxl),
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 420),
                    child: AutofillGroup(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          BrandLogo.of(brand, size: 88),
                          const SizedBox(height: GesbandSpacing.xl),
                          Semantics(
                            header: true,
                            child: DisplayText(brand.name, size: 44),
                          ),
                          if (brand.motto != null) ...[
                            const SizedBox(height: GesbandSpacing.sm),
                            Text(
                              brand.motto!,
                              style: text.bodyLarge!.copyWith(
                                color: t.muted,
                                fontFamily: t.style == VisualStyle.partitura
                                    ? t.displayFamily
                                    : null,
                                fontStyle: t.style == VisualStyle.partitura
                                    ? FontStyle.italic
                                    : null,
                              ),
                            ),
                          ],
                          if (t.style == VisualStyle.partitura) ...[
                            const SizedBox(height: GesbandSpacing.lg),
                            const StaffDivider(),
                          ],
                          const SizedBox(height: GesbandSpacing.xxl),
                          TextField(
                            controller: email,
                            keyboardType: TextInputType.emailAddress,
                            autofillHints: const [AutofillHints.email],
                            textInputAction: TextInputAction.next,
                            decoration:
                                InputDecoration(labelText: strings.email),
                          ),
                          const SizedBox(height: GesbandSpacing.md),
                          TextField(
                            controller: password,
                            obscureText: true,
                            autofillHints: const [AutofillHints.password],
                            textInputAction: TextInputAction.done,
                            onSubmitted: (_) => _submit(),
                            decoration:
                                InputDecoration(labelText: strings.password),
                          ),
                          if (widget.controller.error != null) ...[
                            const SizedBox(height: GesbandSpacing.md),
                            InlineNotice(
                              icon: Icons.error_outline_rounded,
                              tone: Tone.danger,
                              message:
                                  strings.message(widget.controller.error!),
                            ),
                          ],
                          const SizedBox(height: GesbandSpacing.xl),
                          SizedBox(
                            width: double.infinity,
                            child: FilledButton(
                              onPressed: _submit,
                              child: Text(strings.signIn),
                            ),
                          ),
                          if (!brand.isGesband) ...[
                            const SizedBox(height: GesbandSpacing.xl),
                            Center(
                              child: Text(strings.appName,
                                  style: text.labelMedium!
                                      .copyWith(color: t.muted)),
                            ),
                          ],
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Pantalla de espera entre pasos, con la marca activa.
class BrandLoadingScreen extends StatelessWidget {
  const BrandLoadingScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final brand = ThemeScope.brandOf(context);
    return Scaffold(
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            BrandLogo.of(brand, size: 72),
            const SizedBox(height: GesbandSpacing.xl),
            const LoadingView(),
          ],
        ),
      ),
    );
  }
}
