import 'package:flutter/material.dart';

import '../../core/localization/app_strings.dart';

/// Pide el motivo obligatorio de una ausencia. Devuelve el texto o `null` si
/// se cancela.
Future<String?> askAbsenceReason(BuildContext context) => showDialog<String>(
      context: context,
      builder: (_) => const AbsenceReasonDialog(),
    );

/// Pide el motivo de una ausencia. Es dueño de su campo de texto, que sigue en
/// pantalla durante la animación de cierre y no puede liberarse antes.
class AbsenceReasonDialog extends StatefulWidget {
  const AbsenceReasonDialog({super.key});

  @override
  State<AbsenceReasonDialog> createState() => _AbsenceReasonDialogState();
}

class _AbsenceReasonDialogState extends State<AbsenceReasonDialog> {
  final controller = TextEditingController();

  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    return AlertDialog(
      title: Text(strings.absenceReason),
      scrollable: true,
      content: TextField(
        controller: controller,
        autofocus: true,
        maxLength: 500,
        maxLines: 3,
        decoration: InputDecoration(
          labelText: strings.absenceReason,
          helperText: strings.reasonRequired,
          helperMaxLines: 3,
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: Text(strings.cancel),
        ),
        FilledButton(
          onPressed: () {
            final value = controller.text.trim();
            if (value.isNotEmpty) Navigator.pop(context, value);
          },
          child: Text(strings.submitAbsence),
        ),
      ],
    );
  }
}
