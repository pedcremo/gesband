import 'package:flutter/material.dart';

import 'app_strings.dart';

class LanguageMenu extends StatelessWidget {
  const LanguageMenu({super.key});

  @override
  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    final localeController = LocaleScope.of(context);
    return PopupMenuButton<Locale>(
      tooltip: strings.language,
      icon: const Icon(Icons.language),
      initialValue: localeController.locale,
      onSelected: localeController.setLocale,
      itemBuilder: (context) => AppStrings.supportedLocales
          .map(
            (locale) => PopupMenuItem<Locale>(
              value: locale,
              child: Row(
                children: [
                  if (localeController.locale.languageCode ==
                      locale.languageCode)
                    const Padding(
                      padding: EdgeInsets.only(right: 8),
                      child: Icon(Icons.check, size: 18),
                    ),
                  Text(strings.languageName(locale)),
                ],
              ),
            ),
          )
          .toList(growable: false),
    );
  }
}
