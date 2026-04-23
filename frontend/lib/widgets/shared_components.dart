import 'package:flutter/material.dart';

import '../models/inventory_models.dart';
import '../theme/app_theme.dart';

class PrimaryButton extends StatelessWidget {
  final String label;
  final VoidCallback? onPressed;
  final bool isLoading;
  final IconData? icon;

  const PrimaryButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.isLoading = false,
    this.icon,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return SizedBox(
      height: 46,
      width: double.infinity,
      child: FilledButton(
        style: FilledButton.styleFrom(
          backgroundColor: StockWiseColors.slate900,
          foregroundColor: StockWiseColors.offWhite,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          elevation: 0,
        ),
        onPressed: isLoading ? null : onPressed,
        child: AnimatedSwitcher(
          duration: const Duration(milliseconds: 150),
          child: isLoading
              ? SizedBox(
                  key: const ValueKey('loading'),
                  height: 18,
                  width: 18,
                  child: CircularProgressIndicator(strokeWidth: 2, color: cs.onPrimary),
                )
              : Row(
                  key: const ValueKey('content'),
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    if (icon != null) ...[
                      Icon(icon, size: 18),
                      const SizedBox(width: 8),
                    ],
                    Text(label, style: const TextStyle(fontWeight: FontWeight.w600)),
                  ],
                ),
        ),
      ),
    );
  }
}

class SecondaryButton extends StatelessWidget {
  final String label;
  final VoidCallback? onPressed;
  final IconData? icon;

  const SecondaryButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.icon,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 46,
      width: double.infinity,
      child: OutlinedButton(
        style: OutlinedButton.styleFrom(
          foregroundColor: StockWiseColors.slate900,
          side: const BorderSide(color: StockWiseColors.slate200),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        ),
        onPressed: onPressed,
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            if (icon != null) ...[
              Icon(icon, size: 18),
              const SizedBox(width: 8),
            ],
            Text(label, style: const TextStyle(fontWeight: FontWeight.w600)),
          ],
        ),
      ),
    );
  }
}

class RecommendationBadge extends StatelessWidget {
  final RecommendedAction action;
  final bool compact;

  const RecommendationBadge({super.key, required this.action, this.compact = false});

  @override
  Widget build(BuildContext context) {
    final (bg, fg, label) = switch (action) {
      RecommendedAction.restockNow => (StockWiseColors.rose.withValues(alpha: 0.16), StockWiseColors.rose, 'RESTOCK NOW'),
      RecommendedAction.buyLess => (StockWiseColors.amber.withValues(alpha: 0.16), StockWiseColors.amber, 'BUY LESS'),
      RecommendedAction.delayPurchase =>
        (StockWiseColors.emerald.withValues(alpha: 0.16), StockWiseColors.emerald, 'DELAY PURCHASE'),
      RecommendedAction.monitorClosely =>
        (StockWiseColors.indigo.withValues(alpha: 0.16), StockWiseColors.indigo, 'MONITOR'),
    };

    return Container(
      padding: EdgeInsets.symmetric(horizontal: compact ? 10 : 12, vertical: compact ? 6 : 7),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: fg.withValues(alpha: 0.25)),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: fg,
          fontSize: compact ? 11 : 12,
          fontWeight: FontWeight.w700,
          letterSpacing: 0.3,
        ),
      ),
    );
  }
}

class ScoreBadge extends StatelessWidget {
  final String label;
  final int score;

  const ScoreBadge({super.key, required this.label, required this.score});

  @override
  Widget build(BuildContext context) {
    final color = score >= 80
        ? StockWiseColors.rose
        : score >= 60
            ? StockWiseColors.amber
            : score >= 40
                ? StockWiseColors.indigo
                : StockWiseColors.emerald;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: color.withValues(alpha: 0.25)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(label, style: TextStyle(color: StockWiseColors.slate600, fontSize: 12)),
          const SizedBox(width: 8),
          Text(
            '$score',
            style: TextStyle(color: color, fontWeight: FontWeight.w800, fontSize: 14),
          ),
        ],
      ),
    );
  }
}

class KpiCard extends StatelessWidget {
  final String title;
  final String value;
  final String? subtitle;
  final IconData icon;

  const KpiCard({
    super.key,
    required this.title,
    required this.value,
    required this.icon,
    this.subtitle,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: isDark ? StockWiseColors.slate800 : Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          if (!isDark)
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.06),
              blurRadius: 18,
              offset: const Offset(0, 8),
            ),
        ],
        border: Border.all(color: StockWiseColors.slate200),
      ),
      child: Row(
        children: [
          Container(
            height: 40,
            width: 40,
            decoration: BoxDecoration(
              color: StockWiseColors.slate100,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: StockWiseColors.slate200),
            ),
            child: Icon(icon, color: StockWiseColors.slate900, size: 20),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: TextStyle(color: StockWiseColors.slate600, fontSize: 12, fontWeight: FontWeight.w600)),
                const SizedBox(height: 4),
                Text(value, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
                if (subtitle != null) ...[
                  const SizedBox(height: 2),
                  Text(subtitle!, style: TextStyle(color: StockWiseColors.slate600, fontSize: 12)),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class FormInputField extends StatelessWidget {
  final String label;
  final TextEditingController controller;
  final String? hintText;
  final TextInputType keyboardType;
  final String? Function(String?)? validator;
  final bool dense;

  const FormInputField({
    super.key,
    required this.label,
    required this.controller,
    this.hintText,
    this.keyboardType = TextInputType.text,
    this.validator,
    this.dense = false,
  });

  @override
  Widget build(BuildContext context) {
    return TextFormField(
      controller: controller,
      keyboardType: keyboardType,
      validator: validator,
      decoration: InputDecoration(
        labelText: label,
        hintText: hintText,
        isDense: dense,
      ),
    );
  }
}

class FormDropdown<T> extends StatelessWidget {
  final String label;
  final T? value;
  final List<DropdownMenuItem<T>> items;
  final void Function(T?) onChanged;
  final String? Function(T?)? validator;

  const FormDropdown({
    super.key,
    required this.label,
    required this.value,
    required this.items,
    required this.onChanged,
    this.validator,
  });

  @override
  Widget build(BuildContext context) {
    return DropdownButtonFormField<T>(
      value: value,
      items: items,
      validator: validator,
      onChanged: onChanged,
      decoration: InputDecoration(labelText: label),
      borderRadius: BorderRadius.circular(16),
    );
  }
}

class SoftSectionCard extends StatelessWidget {
  final Widget child;
  const SoftSectionCard({super.key, required this.child});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: isDark ? StockWiseColors.slate800 : Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: StockWiseColors.slate200),
        boxShadow: [
          if (!isDark)
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.05),
              blurRadius: 16,
              offset: const Offset(0, 8),
            ),
        ],
      ),
      child: child,
    );
  }
}

