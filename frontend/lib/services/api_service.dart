import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;

import '../models/inventory_models.dart';

class ApiException implements Exception {
  final int statusCode;
  final ErrorEnvelope? error;
  final String message;

  const ApiException({required this.statusCode, required this.message, this.error});

  @override
  String toString() => 'ApiException($statusCode): $message';
}

class ApiService {
  final String baseUrl;
  final http.Client _client;

  ApiService({
    required this.baseUrl,
    http.Client? client,
  }) : _client = client ?? http.Client();

  Uri _uri(String path) => Uri.parse(baseUrl).replace(path: path);

  Future<T> _decodeJson<T>(
    http.Response resp,
    T Function(Map<String, dynamic>) fromJson,
  ) async {
    final body = resp.body;
    Map<String, dynamic>? jsonMap;
    try {
      final decoded = jsonDecode(body);
      if (decoded is Map<String, dynamic>) {
        jsonMap = decoded;
      }
    } catch (_) {
      // ignore
    }

    if (resp.statusCode >= 200 && resp.statusCode < 300) {
      if (jsonMap == null) {
        throw const ApiException(statusCode: 500, message: 'Invalid JSON response.');
      }
      return fromJson(jsonMap);
    }

    ErrorEnvelope? envelope;
    if (jsonMap != null && jsonMap.containsKey('error_code') && jsonMap.containsKey('message')) {
      try {
        envelope = ErrorEnvelope.fromJson(jsonMap);
      } catch (_) {
        // ignore
      }
    }
    throw ApiException(
      statusCode: resp.statusCode,
      message: envelope?.message ?? 'Request failed.',
      error: envelope,
    );
  }

  Future<AnalysisResponse> createAnalysisFromCsv({
    required Uint8List bytes,
    required String filename,
  }) async {
    final req = http.MultipartRequest('POST', _uri('/api/v1/analyses'));
    req.files.add(http.MultipartFile.fromBytes('file', bytes, filename: filename));
    final streamed = await _client.send(req);
    final resp = await http.Response.fromStream(streamed);
    return _decodeJson(resp, AnalysisResponse.fromJson);
  }

  Future<AnalysisResponse> createManualAnalysis(ManualAnalysisRequest request) async {
    final resp = await _client.post(
      _uri('/api/v1/manual-analyses'),
      headers: {'content-type': 'application/json'},
      body: jsonEncode(request.toJson()),
    );
    return _decodeJson(resp, AnalysisResponse.fromJson);
  }

  Future<List<InventoryRecord>> getRecords({required String analysisId}) async {
    final resp = await _client.get(_uri('/api/v1/analyses/$analysisId/records'));
    if (resp.statusCode >= 200 && resp.statusCode < 300) {
      final decoded = jsonDecode(resp.body);
      if (decoded is List) {
        return decoded.map((e) => InventoryRecord.fromJson((e as Map).cast<String, dynamic>())).toList();
      }
      throw const ApiException(statusCode: 500, message: 'Invalid records response.');
    }
    // try to throw envelope
    return _decodeJson(resp, (_) => throw StateError('unreachable'));
  }

  Future<InventoryRecord> patchRecord({
    required String analysisId,
    required int itemId,
    required InventoryRecordUpdate update,
  }) async {
    final resp = await _client.patch(
      _uri('/api/v1/analyses/$analysisId/items/$itemId'),
      headers: {'content-type': 'application/json'},
      body: jsonEncode(update.toJson()),
    );
    return _decodeJson(resp, InventoryRecord.fromJson);
  }

  Future<void> deleteRecord({required String analysisId, required int itemId}) async {
    final resp = await _client.delete(_uri('/api/v1/analyses/$analysisId/items/$itemId'));
    if (resp.statusCode >= 200 && resp.statusCode < 300) return;
    await _decodeJson(resp, (_) => throw StateError('unreachable'));
  }

  Future<SimulationResponse> simulate({
    required String analysisId,
    required int itemId,
    required SimulationRequest request,
  }) async {
    final resp = await _client.post(
      _uri('/api/v1/analyses/$analysisId/items/$itemId/simulate'),
      headers: {'content-type': 'application/json'},
      body: jsonEncode(request.toJson()),
    );
    return _decodeJson(resp, SimulationResponse.fromJson);
  }

  Future<ExplanationResponse> explanation({
    required String analysisId,
    required int itemId,
    required ExplanationRequest request,
  }) async {
    final resp = await _client.post(
      _uri('/api/v1/analyses/$analysisId/items/$itemId/explanation'),
      headers: {'content-type': 'application/json'},
      body: jsonEncode(request.toJson()),
    );
    return _decodeJson(resp, ExplanationResponse.fromJson);
  }
}

