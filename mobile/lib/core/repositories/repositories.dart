import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import '../api/api_client.dart';
import '../models/models.dart';
import '../storage/secure_session_store.dart';

abstract interface class AuthRepository {
  Future<void> login({required String email, required String password});
  Future<bool> hasSession();
  Future<void> logout();
}

class ApiAuthRepository implements AuthRepository {
  ApiAuthRepository(this._api, this._store);

  final ApiClient _api;
  final SessionStore _store;

  @override
  Future<bool> hasSession() async => await _store.readTokens() != null;

  @override
  Future<void> login({required String email, required String password}) async {
    final body = await _api.postObject(
      '/auth/login',
      data: {'email': email.trim(), 'password': password},
    );
    await _store.writeTokens(
      SessionTokens(
        accessToken: body['access_token'] as String,
        refreshToken: body['access_token'] as String,
      ),
    );
  }

  @override
  Future<void> logout() => _store.clear();
}

abstract interface class AssociationsRepository {
  Future<List<Association>> listMine();
}

class ApiAssociationsRepository implements AssociationsRepository {
  ApiAssociationsRepository(this._api);

  final ApiClient _api;

  @override
  Future<List<Association>> listMine() async =>
      (await _api.getList('/associations/'))
          .map(Association.fromJson)
          .toList(growable: false);
}

abstract interface class ActivitiesRepository {
  Future<List<ActivitySummary>> listMine(String associationId);
  Future<ActivityDetail> getById(String associationId, String activityId);
  Future<ActivityDetail> respond(
    String associationId,
    String activityId,
    InvitationResponse response, {
    String note = '',
  });
}

class ApiActivitiesRepository implements ActivitiesRepository {
  ApiActivitiesRepository(this._api, this._cache);

  final ApiClient _api;
  final AgendaCache _cache;

  @override
  Future<List<ActivitySummary>> listMine(String associationId) async {
    try {
      final activities =
          (await _api.getList('/activities/?association_id=$associationId'))
              .map(ActivitySummary.fromJson)
              .toList(growable: false);
      await _cache.write(associationId, activities);
      return activities;
    } on ApiException {
      final cached = await _cache.read(associationId);
      if (cached != null) return cached;
      rethrow;
    }
  }

  @override
  Future<ActivityDetail> getById(
    String associationId,
    String activityId,
  ) async =>
      ActivityDetail.fromJson(
        await _api.getObject(
            '/activities/$activityId/?association_id=$associationId'),
      );

  @override
  Future<ActivityDetail> respond(
    String associationId,
    String activityId,
    InvitationResponse response, {
    String note = '',
  }) async {
    final before = await getById(associationId, activityId);
    final invitationId = before.invitationId;
    if (invitationId == null) {
      throw const ApiException(
          'No tienes una convocatoria para esta actividad.');
    }
    await _api.postObject('/activities/$activityId/respond/', data: {
      'invitation_id': invitationId,
      'response': response.name,
      'note': note,
    });
    return getById(associationId, activityId);
  }
}

class AgendaCache {
  AgendaCache(this._preferences);

  final SharedPreferences _preferences;

  String _key(String associationId) => 'agenda:$associationId';

  Future<void> write(
    String associationId,
    List<ActivitySummary> activities,
  ) async {
    final data = {
      'synced_at': DateTime.now().toUtc().toIso8601String(),
      'results': activities.map((item) => item.toJson()).toList(),
    };
    await _preferences.setString(_key(associationId), jsonEncode(data));
  }

  Future<List<ActivitySummary>?> read(String associationId) async {
    final value = _preferences.getString(_key(associationId));
    if (value == null) return null;
    final data = jsonDecode(value) as Map<String, dynamic>;
    final values = data['results'] as List<dynamic>? ?? const [];
    return values
        .map((item) => ActivitySummary.fromJson(item as Map<String, dynamic>))
        .toList(growable: false);
  }

  Future<void> clearAll() async {
    final keys =
        _preferences.getKeys().where((key) => key.startsWith('agenda:'));
    for (final key in keys) {
      await _preferences.remove(key);
    }
  }
}

abstract interface class ProfileRepository {
  Future<MemberProfile> getMine(String associationId);
  Future<MemberProfile> updateContact({String? email, String? phone});
  Future<MemberProfile> updatePhoto(String filePath);
  Future<MemberProfile> deletePhoto();
}

class ApiProfileRepository implements ProfileRepository {
  ApiProfileRepository(this._api);

  final ApiClient _api;

  @override
  Future<MemberProfile> getMine(String associationId) async =>
      MemberProfile.fromJson(
          await _api.getObject('/members/?association_id=$associationId'));

  @override
  Future<MemberProfile> updateContact({String? email, String? phone}) async =>
      MemberProfile.fromJson(
        await _api.patchObject(
          '/members/me/',
          data: {'email': email, 'phone': phone},
        ),
      );

  @override
  Future<MemberProfile> updatePhoto(String filePath) async =>
      MemberProfile.fromJson(
        await _api.uploadFile(
          '/members/me/photo/',
          field: 'photo',
          filePath: filePath,
        ),
      );

  @override
  Future<MemberProfile> deletePhoto() async {
    await _api.delete('/members/me/photo/');
    return getMine('');
  }
}

abstract interface class InboxRepository {
  Future<List<InboxNotification>> list();
  Future<void> markRead(String notificationId);
}

class ApiInboxRepository implements InboxRepository {
  ApiInboxRepository(this._api);

  final ApiClient _api;

  @override
  Future<List<InboxNotification>> list() async =>
      (await _api.getList('/notifications/'))
          .map(InboxNotification.fromJson)
          .toList(growable: false);

  @override
  Future<void> markRead(String notificationId) async {
    await _api.patchObject(
      '/notifications/$notificationId/',
      data: const {'is_read': true},
    );
  }
}

/// Ya habia un voto de esta cuenta: el servidor responde 409.
class AlreadyVotedException implements Exception {
  const AlreadyVotedException();
}

abstract interface class PollsRepository {
  Future<List<Poll>> listMine(String associationId);
  Future<Poll> getById(String associationId, String pollId);
  Future<Poll> vote(String associationId, String pollId, String optionId);
}

class ApiPollsRepository implements PollsRepository {
  ApiPollsRepository(this._api);

  final ApiClient _api;

  @override
  Future<List<Poll>> listMine(String associationId) async =>
      (await _api.getList('/polls/?association_id=$associationId'))
          .map(Poll.fromJson)
          .toList(growable: false);

  @override
  Future<Poll> getById(String associationId, String pollId) async =>
      Poll.fromJson(await _api
          .getObject('/polls/$pollId/?association_id=$associationId'));

  @override
  Future<Poll> vote(
    String associationId,
    String pollId,
    String optionId,
  ) async {
    try {
      return Poll.fromJson(await _api.postObject(
        '/polls/$pollId/vote/?association_id=$associationId',
        data: {'option_id': optionId},
      ));
    } on ApiException catch (error) {
      if (error.statusCode == 409) throw const AlreadyVotedException();
      rethrow;
    }
  }
}
