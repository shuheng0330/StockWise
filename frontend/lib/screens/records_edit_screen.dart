import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/inventory_models.dart';
import '../state/providers.dart';
import '../utils/error_handler.dart';
import '../widgets/shared_components.dart';

class RecordsEditScreen extends ConsumerStatefulWidget {
  final String analysisId;
  const RecordsEditScreen({super.key, required this.analysisId});

  @override
  ConsumerState<RecordsEditScreen> createState() => _RecordsEditScreenState();
}

class _RecordsEditScreenState extends ConsumerState<RecordsEditScreen> {
  bool _loading = true;
  List<InventoryRecord> _records = const [];
  Object? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final api = ref.read(apiServiceProvider);
      final records = await api.getRecords(analysisId: widget.analysisId);
      if (!mounted) return;
      setState(() => _records = records);
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = e);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _edit(InventoryRecord record) async {
    final result = await showModalBottomSheet<InventoryRecordUpdate?>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      backgroundColor: Theme.of(context).cardColor,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (context) => _EditRecordSheet(record: record),
    );
    if (result == null) return;

    try {
      final api = ref.read(apiServiceProvider);
      final updated = await api.patchRecord(
        analysisId: widget.analysisId,
        itemId: record.itemId,
        update: result,
      );
      if (!mounted) return;
      setState(() {
        _records = _records.map((r) => r.itemId == updated.itemId ? updated : r).toList();
      });
    } catch (e) {
      if (!mounted) return;
      showApiError(context, e);
    }
  }

  Future<void> _delete(InventoryRecord record) async {
    if (_records.length <= 1) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('You can’t delete the final remaining item.')));
      return;
    }

    final ok = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete item?'),
        content: Text('Delete "${record.itemName}" from this analysis?'),
        actions: [
          TextButton(onPressed: () => Navigator.of(context).pop(false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.of(context).pop(true), child: const Text('Delete')),
        ],
      ),
    );
    if (ok != true) return;

    try {
      final api = ref.read(apiServiceProvider);
      await api.deleteRecord(analysisId: widget.analysisId, itemId: record.itemId);
      if (!mounted) return;
      setState(() => _records = _records.where((r) => r.itemId != record.itemId).toList());
    } catch (e) {
      if (!mounted) return;
      showApiError(context, e);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Records Review / Edit')),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 520),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: _loading
                ? const Center(child: CircularProgressIndicator())
                : _error != null
                    ? SoftSectionCard(
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const Text('Could not load records.', style: TextStyle(fontWeight: FontWeight.w900)),
                            const SizedBox(height: 8),
                            TextButton.icon(
                              onPressed: () => showApiError(context, _error!),
                              icon: const Icon(Icons.error_outline),
                              label: const Text('Tap for details'),
                            ),
                            const SizedBox(height: 8),
                            PrimaryButton(label: 'Retry', onPressed: _load, icon: Icons.refresh),
                          ],
                        ),
                      )
                    : ListView(
                        children: [
                          Text(
                            'Items (${_records.length})',
                            style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w900),
                          ),
                          const SizedBox(height: 10),
                          ..._records.map((r) => Padding(
                                padding: const EdgeInsets.only(bottom: 12),
                                child: SoftSectionCard(
                                  child: Row(
                                    children: [
                                      Expanded(
                                        child: Column(
                                          crossAxisAlignment: CrossAxisAlignment.start,
                                          children: [
                                            Text(r.itemName, style: const TextStyle(fontWeight: FontWeight.w900)),
                                            const SizedBox(height: 4),
                                            Text(
                                              'Stock: ${r.currentStock.toStringAsFixed(1)} ${r.unit} • Usage: ${r.usageValue.toStringAsFixed(1)} (${usagePeriodToJson(r.usagePeriod)})',
                                              style: TextStyle(color: Theme.of(context).hintColor, fontSize: 12),
                                            ),
                                            if (r.recommendedAction != null) ...[
                                              const SizedBox(height: 8),
                                              RecommendationBadge(action: r.recommendedAction!, compact: true),
                                            ],
                                          ],
                                        ),
                                      ),
                                      IconButton(onPressed: () => _edit(r), icon: const Icon(Icons.edit_outlined)),
                                      IconButton(onPressed: () => _delete(r), icon: const Icon(Icons.delete_outline)),
                                    ],
                                  ),
                                ),
                              )),
                        ],
                      ),
          ),
        ),
      ),
    );
  }
}

class _EditRecordSheet extends StatefulWidget {
  final InventoryRecord record;
  const _EditRecordSheet({required this.record});

  @override
  State<_EditRecordSheet> createState() => _EditRecordSheetState();
}

class _EditRecordSheetState extends State<_EditRecordSheet> {
  final _formKey = GlobalKey<FormState>();

  late final TextEditingController itemName;
  late final TextEditingController currentStock;
  late final TextEditingController unit;
  late final TextEditingController usageValue;
  UsagePeriod? usagePeriod;
  late final TextEditingController leadTimeDays;
  late final TextEditingController pricePerUnit;
  double? seasonalFactor;

  PerishabilityLevel? perishabilityLevel;
  late final TextEditingController recentWastePercentage;

  late final TextEditingController category;
  late final TextEditingController subcategory;
  late final TextEditingController supplierName;
  late final TextEditingController manualReorderLevel;

  @override
  void initState() {
    super.initState();
    final r = widget.record;
    itemName = TextEditingController(text: r.itemName);
    currentStock = TextEditingController(text: r.currentStock.toString());
    unit = TextEditingController(text: r.unit);
    usageValue = TextEditingController(text: r.usageValue.toString());
    usagePeriod = r.usagePeriod;
    leadTimeDays = TextEditingController(text: r.leadTimeDays.toString());
    pricePerUnit = TextEditingController(text: r.pricePerUnit.toString());
    seasonalFactor = r.seasonalFactor;
    perishabilityLevel = r.perishabilityLevel;
    recentWastePercentage = TextEditingController(text: r.recentWastePercentage?.toString() ?? '');
    category = TextEditingController(text: r.category ?? '');
    subcategory = TextEditingController(text: r.subcategory ?? '');
    supplierName = TextEditingController(text: r.supplierName ?? '');
    manualReorderLevel = TextEditingController(text: r.manualReorderLevel?.toString() ?? '');
  }

  @override
  void didUpdateWidget(covariant _EditRecordSheet oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.record == widget.record) return;
    final r = widget.record;
    itemName.text = r.itemName;
    currentStock.text = r.currentStock.toString();
    unit.text = r.unit;
    usageValue.text = r.usageValue.toString();
    usagePeriod = r.usagePeriod;
    leadTimeDays.text = r.leadTimeDays.toString();
    pricePerUnit.text = r.pricePerUnit.toString();
    seasonalFactor = r.seasonalFactor;
    perishabilityLevel = r.perishabilityLevel;
    recentWastePercentage.text = r.recentWastePercentage?.toString() ?? '';
    category.text = r.category ?? '';
    subcategory.text = r.subcategory ?? '';
    supplierName.text = r.supplierName ?? '';
    manualReorderLevel.text = r.manualReorderLevel?.toString() ?? '';
  }

  @override
  void dispose() {
    itemName.dispose();
    currentStock.dispose();
    unit.dispose();
    usageValue.dispose();
    leadTimeDays.dispose();
    pricePerUnit.dispose();
    recentWastePercentage.dispose();
    category.dispose();
    subcategory.dispose();
    supplierName.dispose();
    manualReorderLevel.dispose();
    super.dispose();
  }

  void _save() {
    final form = _formKey.currentState;
    if (form == null) return;
    if (!form.validate()) return;

    final update = InventoryRecordUpdate(
      itemName: itemName.text.trim(),
      currentStock: double.parse(currentStock.text.trim()),
      unit: unit.text.trim(),
      usageValue: double.parse(usageValue.text.trim()),
      usagePeriod: usagePeriod,
      leadTimeDays: int.parse(leadTimeDays.text.trim()),
      pricePerUnit: double.parse(pricePerUnit.text.trim()),
      seasonalFactor: seasonalFactor,
      category: category.text.trim().isEmpty ? null : category.text.trim(),
      subcategory: subcategory.text.trim().isEmpty ? null : subcategory.text.trim(),
      supplierName: supplierName.text.trim().isEmpty ? null : supplierName.text.trim(),
      perishabilityLevel: perishabilityLevel,
      manualReorderLevel: manualReorderLevel.text.trim().isEmpty ? null : double.parse(manualReorderLevel.text.trim()),
      recentWastePercentage:
          recentWastePercentage.text.trim().isEmpty ? null : double.parse(recentWastePercentage.text.trim()),
    );

    final hasWasteSignal = update.perishabilityLevel != null || update.recentWastePercentage != null;
    if (!hasWasteSignal) {
      ScaffoldMessenger.of(context)
          .showSnackBar(const SnackBar(content: Text('Keep a waste signal: perishability level or recent waste %.')));
      return;
    }

    Navigator.of(context).pop(update);
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(
        left: 16,
        right: 16,
        top: 8,
        bottom: 16 + MediaQuery.of(context).viewInsets.bottom,
      ),
      child: SingleChildScrollView(
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text('Edit record', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
              const SizedBox(height: 12),
              FormInputField(label: 'item_name', controller: itemName, validator: (v) => (v ?? '').trim().isEmpty ? 'Required' : null),
              const SizedBox(height: 10),
              Row(
                children: [
                  Expanded(
                    child: FormInputField(
                      label: 'current_stock',
                      controller: currentStock,
                      keyboardType: const TextInputType.numberWithOptions(decimal: true),
                      validator: (v) {
                        final n = double.tryParse((v ?? '').trim());
                        if (n == null) return 'Required';
                        if (n < 0) return 'Must be >= 0';
                        return null;
                      },
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: FormInputField(label: 'unit', controller: unit, validator: (v) => (v ?? '').trim().isEmpty ? 'Required' : null),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              Row(
                children: [
                  Expanded(
                    child: FormInputField(
                      label: 'usage_value',
                      controller: usageValue,
                      keyboardType: const TextInputType.numberWithOptions(decimal: true),
                      validator: (v) {
                        final n = double.tryParse((v ?? '').trim());
                        if (n == null) return 'Required';
                        if (n <= 0) return 'Must be > 0';
                        return null;
                      },
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: FormDropdown<UsagePeriod>(
                      label: 'usage_period',
                      value: usagePeriod,
                      onChanged: (v) => setState(() => usagePeriod = v),
                      validator: (v) => v == null ? 'Required' : null,
                      items: const [
                        DropdownMenuItem(value: UsagePeriod.daily, child: Text('daily')),
                        DropdownMenuItem(value: UsagePeriod.weekly, child: Text('weekly')),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              Row(
                children: [
                  Expanded(
                    child: FormInputField(
                      label: 'lead_time_days',
                      controller: leadTimeDays,
                      keyboardType: TextInputType.number,
                      validator: (v) {
                        final n = int.tryParse((v ?? '').trim());
                        if (n == null) return 'Required';
                        if (n <= 0) return 'Must be > 0';
                        return null;
                      },
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: FormInputField(
                      label: 'price_per_unit',
                      controller: pricePerUnit,
                      keyboardType: const TextInputType.numberWithOptions(decimal: true),
                      validator: (v) {
                        final n = double.tryParse((v ?? '').trim());
                        if (n == null) return 'Required';
                        if (n < 0) return 'Must be >= 0';
                        return null;
                      },
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              FormDropdown<double>(
                label: 'seasonal_factor',
                value: seasonalFactor,
                onChanged: (v) => setState(() => seasonalFactor = v),
                validator: (v) => v == null ? 'Required' : null,
                items: const [
                  DropdownMenuItem(value: 0.8, child: Text('Low demand (0.8)')),
                  DropdownMenuItem(value: 1.0, child: Text('Normal (1.0)')),
                  DropdownMenuItem(value: 1.2, child: Text('Busy (1.2)')),
                  DropdownMenuItem(value: 1.4, child: Text('Peak (1.4)')),
                ],
              ),
              const SizedBox(height: 10),
              FormDropdown<PerishabilityLevel>(
                label: 'perishability_level (optional)',
                value: perishabilityLevel,
                onChanged: (v) => setState(() => perishabilityLevel = v),
                items: const [
                  DropdownMenuItem(value: PerishabilityLevel.low, child: Text('Low')),
                  DropdownMenuItem(value: PerishabilityLevel.medium, child: Text('Medium')),
                  DropdownMenuItem(value: PerishabilityLevel.high, child: Text('High')),
                ],
              ),
              const SizedBox(height: 10),
              FormInputField(
                label: 'recent_waste_percentage (optional)',
                controller: recentWastePercentage,
                keyboardType: const TextInputType.numberWithOptions(decimal: true),
                validator: (v) {
                  final t = (v ?? '').trim();
                  if (t.isEmpty) return null;
                  final n = double.tryParse(t);
                  if (n == null) return 'Must be a number';
                  if (n < 0) return 'Must be >= 0';
                  return null;
                },
              ),
              const SizedBox(height: 12),
              ExpansionTile(
                tilePadding: EdgeInsets.zero,
                title: const Text('Advanced fields', style: TextStyle(fontWeight: FontWeight.w700)),
                children: [
                  const SizedBox(height: 10),
                  FormInputField(label: 'category (optional)', controller: category),
                  const SizedBox(height: 10),
                  FormInputField(label: 'subcategory (optional)', controller: subcategory),
                  const SizedBox(height: 10),
                  FormInputField(label: 'supplier_name (optional)', controller: supplierName),
                  const SizedBox(height: 10),
                  FormInputField(
                    label: 'manual_reorder_level (optional)',
                    controller: manualReorderLevel,
                    keyboardType: const TextInputType.numberWithOptions(decimal: true),
                    validator: (v) {
                      final t = (v ?? '').trim();
                      if (t.isEmpty) return null;
                      final n = double.tryParse(t);
                      if (n == null) return 'Must be a number';
                      if (n < 0) return 'Must be >= 0';
                      return null;
                    },
                  ),
                ],
              ),
              const SizedBox(height: 12),
              PrimaryButton(label: 'Save changes', icon: Icons.save, onPressed: _save),
            ],
          ),
        ),
      ),
    );
  }
}

