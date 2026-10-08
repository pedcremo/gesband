import 'dart:typed_data';

import 'package:flutter/material.dart';

import '../../core/app_controller.dart';
import '../../core/localization/app_strings.dart';
import '../../core/models/models.dart';
import '../../core/theme/brand.dart';
import '../../core/theme/gesband_tokens.dart';
import '../../core/theme/theme_controller.dart';
import '../../core/theme/visual_style.dart';
import '../../core/ui/brand_header.dart';
import '../../core/ui/components.dart';
import '../notifications/notification_activation_screen.dart';

/// Mi ficha: datos propios con la foto y los ajustes del dispositivo
/// (modo de color, idioma, avisos, banda y sesión).
class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key, required this.controller});

  final AppController controller;

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  late Future<(MemberProfile, Uint8List?)> future;

  @override
  void initState() {
    super.initState();
    future = _load();
  }

  Future<(MemberProfile, Uint8List?)> _load() async {
    final profile = await widget.controller.profileRepository
        .getMine(widget.controller.activeAssociation!.id);
    final url = profile.photoUrl;
    // La foto es privada: se pide al API con la sesión, nunca por URL pública.
    final photo =
        url == null ? null : await widget.controller.api.getBytes(url);
    return (profile, photo);
  }

  void _openNotifications() {
    Navigator.of(context).push(MaterialPageRoute<void>(
      builder: (routeContext) => NotificationActivationScreen(
        notifications: widget.controller.notifications,
        onContinue: () => Navigator.of(routeContext).pop(),
      ),
    ));
  }

  @override
  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    final theme = ThemeScope.maybeOf(context);
    final locale = LocaleScope.of(context);
    final t = GesbandTokens.of(context);
    final text = Theme.of(context).textTheme;
    const gap = SizedBox(height: GesbandSpacing.md);

    return ListView(
      padding: const EdgeInsets.only(bottom: GesbandSpacing.xxxl),
      children: [
        BrandHeader(
          brand: ThemeScope.brandOf(context),
          title: strings.myProfile,
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(
              GesbandSpacing.xl, GesbandSpacing.md, GesbandSpacing.xl, 0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              FutureBuilder<(MemberProfile, Uint8List?)>(
                future: future,
                builder: (context, snapshot) {
                  if (snapshot.hasError) {
                    return InlineNotice(
                      key: const Key('profile-unavailable'),
                      icon: Icons.person_off_outlined,
                      tone: Tone.neutral,
                      message: strings.profileUnavailable,
                      actionLabel: strings.retry,
                      onAction: () => setState(() => future = _load()),
                    );
                  }
                  if (!snapshot.hasData) {
                    return const SizedBox(height: 120, child: LoadingView());
                  }
                  final (profile, photo) = snapshot.data!;
                  return _ProfileCard(profile: profile, photo: photo);
                },
              ),
              const SizedBox(height: GesbandSpacing.xxl),
              SectionTitle(strings.settings),
              gap,
              Text(strings.appearance, style: text.titleSmall),
              const SizedBox(height: GesbandSpacing.sm),
              ChoiceSegments<ColorModeChoice>(
                key: const Key('color-mode-choice'),
                selected: theme?.colorModeChoice ?? ColorModeChoice.band,
                onSelected: (value) => theme?.setColorModeChoice(value),
                options: [
                  (ColorModeChoice.band, strings.colorModeBand),
                  (ColorModeChoice.light, strings.colorModeLight),
                  (ColorModeChoice.dark, strings.colorModeDark),
                ],
              ),
              const SizedBox(height: GesbandSpacing.lg),
              Text(strings.language, style: text.titleSmall),
              const SizedBox(height: GesbandSpacing.sm),
              ChoiceSegments<String>(
                key: const Key('language-choice'),
                selected: locale.locale.languageCode,
                onSelected: (code) => locale.setLocale(Locale(code)),
                options: [
                  for (final item in AppStrings.supportedLocales)
                    (item.languageCode, strings.languageName(item)),
                ],
              ),
              const SizedBox(height: GesbandSpacing.lg),
              ListenableBuilder(
                listenable: widget.controller.notifications,
                builder: (context, _) {
                  final state = widget.controller.notifications.state;
                  return _SettingsRow(
                    key: const Key('notifications-settings'),
                    icon: Icons.notifications_active_outlined,
                    title: strings.notificationsOnThisPhone,
                    subtitle: !state.available
                        ? strings.notificationsUnavailable
                        : state.fullyActive
                            ? strings.notificationsActiveShort
                            : strings.notificationsNeedReview,
                    onTap: _openNotifications,
                  );
                },
              ),
              gap,
              _SettingsRow(
                key: const Key('change-association'),
                icon: Icons.swap_horiz_rounded,
                title: strings.changeAssociation,
                onTap: widget.controller.changeAssociation,
              ),
              gap,
              _SettingsRow(
                icon: Icons.description_outlined,
                title: strings.licenses,
                onTap: () => showLicensePage(
                  context: context,
                  applicationName: strings.appName,
                ),
              ),
              const SizedBox(height: GesbandSpacing.xxl),
              OutlinedButton.icon(
                key: const Key('sign-out'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: t.dangerInk,
                  side: BorderSide(color: t.dangerInk, width: 1.5),
                ),
                onPressed: widget.controller.logout,
                icon: const Icon(Icons.logout_rounded),
                label: Text(strings.signOut),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _ProfileCard extends StatelessWidget {
  const _ProfileCard({required this.profile, required this.photo});

  final MemberProfile profile;
  final Uint8List? photo;

  @override
  Widget build(BuildContext context) {
    final t = GesbandTokens.of(context);
    final strings = AppStrings.of(context);
    final text = Theme.of(context).textTheme;
    final radius = BorderRadius.circular(
        t.style == VisualStyle.partitura ? 999 : t.radiusCard);
    final bytes = photo;
    final avatar = Semantics(
      label: strings.photoOf(profile.fullName),
      image: true,
      child: ClipRRect(
        borderRadius: radius,
        child: SizedBox.square(
          dimension: 88,
          child: bytes != null
              ? Image.memory(bytes, fit: BoxFit.cover, gaplessPlayback: true)
              : ColoredBox(
                  color: t.primaryTint,
                  child: Center(
                    child: Text(
                      monogramOf(profile.fullName),
                      textScaler: TextScaler.noScaling,
                      style: t.display(34, color: t.onPrimaryTint),
                    ),
                  ),
                ),
        ),
      ),
    );
    final details = <(String, String)>[
      if (profile.instrument != null)
        (strings.instrumentLabel, profile.instrument!),
      if (profile.email != null) (strings.email, profile.email!),
      if (profile.phone != null) (strings.phoneLabel, profile.phone!),
    ];
    return SurfaceCard(
      key: const Key('profile-card'),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              avatar,
              const SizedBox(width: GesbandSpacing.lg),
              Expanded(child: DisplayText(profile.fullName, size: 28)),
            ],
          ),
          if (details.isNotEmpty) const SizedBox(height: GesbandSpacing.md),
          for (final (label, value) in details)
            Padding(
              padding: const EdgeInsets.only(top: GesbandSpacing.sm),
              child: MergeSemantics(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(label, style: text.bodySmall),
                    Text(value, style: text.titleMedium),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _SettingsRow extends StatelessWidget {
  const _SettingsRow({
    super.key,
    required this.icon,
    required this.title,
    required this.onTap,
    this.subtitle,
  });

  final IconData icon;
  final String title;
  final String? subtitle;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final t = GesbandTokens.of(context);
    final text = Theme.of(context).textTheme;
    return MergeSemantics(
      child: SurfaceCard(
        onTap: onTap,
        padding: const EdgeInsets.symmetric(
            horizontal: GesbandSpacing.lg, vertical: 14),
        child: Row(
          children: [
            Icon(icon, color: t.primaryText),
            const SizedBox(width: GesbandSpacing.md),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: text.titleMedium),
                  if (subtitle != null) Text(subtitle!, style: text.bodySmall),
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
