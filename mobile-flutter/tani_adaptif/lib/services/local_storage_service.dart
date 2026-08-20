import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import '../models/cuaca_model.dart';
import '../models/recommendation_bundle.dart';

class LocalStorageService {
  static const _weatherKey = 'weather_cache_v1';
  static const _recommendationKey = 'recommendation_cache_v1';
  static const _recommendationSignatureKey =
      'recommendation_cache_signature_v1';
  static const _visualHistoryKey = 'visual_generation_history_v1';

  final SharedPreferences? _providedPreferences;

  const LocalStorageService({SharedPreferences? preferences})
    : _providedPreferences = preferences;

  Future<SharedPreferences> get _preferences async =>
      _providedPreferences ?? SharedPreferences.getInstance();

  Future<void> saveWeather(CuacaModel weather) async {
    final preferences = await _preferences;
    await preferences.setString(_weatherKey, jsonEncode(weather.toJson()));
  }

  Future<CuacaModel?> loadWeather() async {
    final preferences = await _preferences;
    final raw = preferences.getString(_weatherKey);
    if (raw == null) return null;
    try {
      return CuacaModel.fromJson(_asMap(jsonDecode(raw))).asLocalCache();
    } on FormatException {
      return null;
    }
  }

  Future<void> saveRecommendation(
    String signature,
    RecommendationBundle bundle,
  ) async {
    final preferences = await _preferences;
    await preferences.setString(
      _recommendationKey,
      jsonEncode(bundle.toJson()),
    );
    await preferences.setString(_recommendationSignatureKey, signature);
  }

  Future<RecommendationBundle?> loadRecommendation(String signature) async {
    final preferences = await _preferences;
    if (preferences.getString(_recommendationSignatureKey) != signature) {
      return null;
    }
    final raw = preferences.getString(_recommendationKey);
    if (raw == null) return null;
    try {
      return RecommendationBundle.fromJson(
        _asMap(jsonDecode(raw)),
      ).asLocalCache();
    } on FormatException {
      return null;
    }
  }

  Future<void> saveVisualHistory(Map<String, dynamic> entry) async {
    final preferences = await _preferences;
    final existing = preferences.getStringList(_visualHistoryKey) ?? const [];
    final entryId = _historyId(entry);
    final updated = [
      jsonEncode(entry),
      ...existing.where((item) {
        if (entryId.isEmpty) return true;
        try {
          return _historyId(_asMap(jsonDecode(item))) != entryId;
        } on FormatException {
          return true;
        }
      }),
    ].take(20).toList();
    await preferences.setStringList(_visualHistoryKey, updated);
  }

  Future<List<Map<String, dynamic>>> loadVisualHistory() async {
    final preferences = await _preferences;
    final raw = preferences.getStringList(_visualHistoryKey) ?? const [];
    return raw
        .map((item) {
          try {
            return _asMap(jsonDecode(item));
          } on FormatException {
            return <String, dynamic>{};
          }
        })
        .where((item) => item.isNotEmpty)
        .toList();
  }

  Future<void> deleteVisualHistory(String id) async {
    final preferences = await _preferences;
    final existing = preferences.getStringList(_visualHistoryKey) ?? const [];
    final updated = existing.where((item) {
      try {
        return _historyId(_asMap(jsonDecode(item))) != id;
      } on FormatException {
        return true;
      }
    }).toList();
    await preferences.setStringList(_visualHistoryKey, updated);
  }
}

Map<String, dynamic> _asMap(dynamic value) {
  if (value is Map<String, dynamic>) return value;
  if (value is Map) {
    return value.map((key, item) => MapEntry(key.toString(), item));
  }
  return <String, dynamic>{};
}

String _historyId(Map<String, dynamic> entry) {
  return entry['id']?.toString() ?? entry['request_id']?.toString() ?? '';
}
