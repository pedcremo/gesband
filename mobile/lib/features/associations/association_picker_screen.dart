import 'package:flutter/material.dart';
import '../../core/app_controller.dart';
import '../../core/localization/app_strings.dart';
import '../../core/localization/language_menu.dart';

class AssociationPickerScreen extends StatelessWidget {
  const AssociationPickerScreen({super.key, required this.controller});
  final AppController controller;
  @override
  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    return Scaffold(
      appBar: AppBar(
        title: Text(strings.associations),
        actions: const [LanguageMenu()],
      ),
      body: controller.associations.isEmpty
          ? Center(child: Text(strings.noAssociations))
          : ListView(
              padding: const EdgeInsets.all(16),
              children: controller.associations
                  .map((association) => Card(
                      child: ListTile(
                          title: Text(association.name),
                          subtitle: Text(association.motto ?? ''),
                          onTap: () =>
                              controller.selectAssociation(association))))
                  .toList(),
            ),
    );
  }
}
