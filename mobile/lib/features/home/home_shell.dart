import 'package:flutter/material.dart';

import '../../core/app_controller.dart';
import '../../core/localization/app_strings.dart';
import '../../core/ui/section_nav.dart';
import '../activities/agenda_screen.dart';
import '../inbox/inbox_screen.dart';
import '../polls/polls_screen.dart';
import '../profile/profile_screen.dart';

/// Secciones principales con la navegación inferior del estilo activo.
///
/// Cada sección se construye la primera vez que se visita y conserva su
/// estado al cambiar de pestaña.
class HomeShell extends StatefulWidget {
  const HomeShell({super.key, required this.controller});

  final AppController controller;

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int index = 0;
  final visited = <int>{0};

  @override
  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    final controller = widget.controller;
    final association = controller.activeAssociation!;
    final pages = <Widget Function()>[
      () => AgendaScreen(controller: controller),
      () => PollsScreen(
            association: association,
            repository: controller.pollsRepository,
          ),
      () => InboxScreen(controller: controller),
      () => ProfileScreen(controller: controller),
    ];
    return Scaffold(
      body: IndexedStack(
        index: index,
        children: [
          for (var i = 0; i < pages.length; i++)
            visited.contains(i) ? pages[i]() : const SizedBox.shrink(),
        ],
      ),
      bottomNavigationBar: SectionNav(
        selected: index,
        onSelected: (value) => setState(() {
          index = value;
          visited.add(value);
        }),
        items: [
          SectionNavItem(
            key: const Key('nav-agenda'),
            icon: Icons.calendar_month_outlined,
            label: strings.agenda,
          ),
          SectionNavItem(
            key: const Key('nav-polls'),
            icon: Icons.bar_chart_rounded,
            label: strings.polls,
          ),
          SectionNavItem(
            key: const Key('nav-inbox'),
            icon: Icons.notifications_none_rounded,
            label: strings.inbox,
          ),
          SectionNavItem(
            key: const Key('nav-profile'),
            icon: Icons.person_outline_rounded,
            label: strings.myProfile,
          ),
        ],
      ),
    );
  }
}
