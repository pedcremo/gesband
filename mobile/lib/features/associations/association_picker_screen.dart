import 'dart:typed_data';

import 'package:flutter/material.dart';

import '../../core/app_controller.dart';
import '../../core/localization/app_strings.dart';
import '../../core/localization/language_menu.dart';
import '../../core/models/models.dart';
import '../../core/theme/color_contrast.dart';
import '../../core/theme/gesband_tokens.dart';
import '../../core/theme/theme_controller.dart';
import '../../core/ui/brand_logo.dart';
import '../../core/ui/components.dart';

/// Elección de banda. Cada tarjeta muestra el logotipo o el monograma con el
/// color de esa banda; la app conserva la marca de la última hasta elegir.
class AssociationPickerScreen extends StatelessWidget {
  const AssociationPickerScreen({super.key, required this.controller});
  final AppController controller;
  @override
  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    final theme = ThemeScope.maybeOf(context);
    return Scaffold(
      appBar: ScreenBar(
        title: strings.associations,
        actions: const [LanguageMenu()],
      ),
      body: controller.associations.isEmpty
          ? MessageView(
              icon: Icons.groups_outlined,
              message: strings.noAssociations,
            )
          : ListView(
              padding: const EdgeInsets.fromLTRB(GesbandSpacing.xl,
                  GesbandSpacing.sm, GesbandSpacing.xl, GesbandSpacing.xxl),
              children: [
                for (final association in controller.associations)
                  Padding(
                    padding: const EdgeInsets.only(bottom: GesbandSpacing.md),
                    child: _AssociationCard(
                      association: association,
                      logo: theme?.logoFor(association) ?? Future.value(null),
                      onTap: () => controller.selectAssociation(association),
                    ),
                  ),
              ],
            ),
    );
  }
}

class _AssociationCard extends StatelessWidget {
  const _AssociationCard({
    required this.association,
    required this.logo,
    required this.onTap,
  });

  final Association association;
  final Future<Uint8List?> logo;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final t = GesbandTokens.of(context);
    final text = Theme.of(context).textTheme;
    final color = parseHexColor(association.primaryColor) ?? t.primary;
    return MergeSemantics(
      child: SurfaceCard(
        onTap: onTap,
        child: Row(
          children: [
            FutureBuilder<Uint8List?>(
              future: logo,
              builder: (context, snapshot) => BrandLogo(
                name: association.name,
                logo: snapshot.data,
                color: color,
                size: 52,
              ),
            ),
            const SizedBox(width: GesbandSpacing.lg),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  DisplayText(association.name, size: 22),
                  if (association.motto != null)
                    Text(association.motto!, style: text.bodySmall),
                ],
              ),
            ),
            Icon(Icons.chevron_right_rounded, color: t.muted),
          ],
        ),
      ),
    );
  }
}
