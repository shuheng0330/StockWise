import 'package:flutter/material.dart';

import '../services/api_service.dart';

String userMessageForErrorCode(String? code) {
  switch (code) {
    case 'validation_error':
      return 'Some fields are missing or invalid. Please review your inputs and try again.';
    case 'explanation_validation_error':
      return 'The AI explanation payload was invalid. We’ll show a safe fallback explanation.';
    case 'request_error':
      return 'That request could not be completed. Please try again.';
    default:
      return 'Something went wrong. Please try again.';
  }
}

void showApiError(BuildContext context, Object error) {
  String message = 'Something went wrong.';
  if (error is ApiException) {
    message = error.error?.errorCode != null ? userMessageForErrorCode(error.error!.errorCode) : error.message;
  }

  ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(content: Text(message)),
  );
}

