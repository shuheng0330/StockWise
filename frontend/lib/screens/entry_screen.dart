import 'dart:typed_data';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../models/inventory_models.dart';
import '../services/api_service.dart';
import '../state/providers.dart';
import '../utils/error_handler.dart';
import '../widgets/shared_components.dart';

class EntryScreen extends ConsumerStatefulWidget {
  const EntryScreen({super.key});

  @override
  ConsumerState<EntryScreen> createState() => _EntryScreenState();
}

class _EntryScreenState extends ConsumerState<EntryScreen> {
  bool _csvLoading = false;
  bool _manualLoading = false;

  final _manualFormKey = GlobalKey<FormState>();
  final List<_ManualItemDraft> _drafts = [_ManualItemDraft()];

  static const _csvHeaders =
      'item_name,current_stock,unit,usage_value,usage_period,lead_time_days,price_per_unit,seasonal_factor,perishability_level,category,subcategory,supplier_name,manual_reorder_level,recent_waste_percentage';

  @override
  void dispose() {
    for (final d in _drafts) {
      d.dispose();
    }
    super.dispose();
  }

  Future<void> _pickAndUploadCsv() async {
    setState(() => _csvLoading = true);
    try {
      final result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: const ['csv'],
        withData: true,
      );
      if (!mounted) return;
      if (result == null || result.files.isEmpty) return;

      final file = result.files.single;
      final Uint8List? bytes = file.bytes;
      if (bytes == null) {
        throw const ApiException(statusCode: 400, message: 'Could not read selected file.');
      }

      final api = ref.read(apiServiceProvider);
      final analysis = await api.createAnalysisFromCsv(bytes: bytes, filename: file.name);
      ref.read(analysisCacheProvider.notifier).upsert(analysis);
      if (!mounted) return;
      context.goNamed('dashboard', pathParameters: {'analysisId': analysis.analysisId});
    } catch (e) {
      if (!mounted) return;
      showApiError(context, e);
    } finally {
      if (mounted) setState(() => _csvLoading = false);
    }
  }

  void _addDraft() {
    setState(() => _drafts.add(_ManualItemDraft()));
  }

  void _removeDraft(int idx) {
    if (_drafts.length <= 1) return;
    setState(() {
      final d = _drafts.removeAt(idx);
      d.dispose();
    });
  }

  Future<void> _submitManual() async {
    final form = _manualFormKey.currentState;
    if (form == null) return;
    if (!form.validate()) return;

    final items = <ManualInventoryItemInput>[];
    for (final d in _drafts) {
      final item = d.toModel();
      final hasWasteSignal = item.perishabilityLevel != null || item.recentWastePercentage != null;
      if (!hasWasteSignal) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Each item needs a waste signal: perishability level or recent waste %.')),
        );
        return;
      }
      items.add(item);
    }

    setState(() => _manualLoading = true);
    try {
      final api = ref.read(apiServiceProvider);
      final analysis = await api.createManualAnalysis(ManualAnalysisRequest(items: items));
      ref.read(analysisCacheProvider.notifier).upsert(analysis);
      if (!mounted) return;
      context.goNamed('dashboard', pathParameters: {'analysisId': analysis.analysisId});
    } catch (e) {
      if (!mounted) return;
      showApiError(context, e);
    } finally {
      if (mounted) setState(() => _manualLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('StockWise'),
          bottom: const TabBar(
            tabs: [
              Tab(text: 'Upload CSV'),
              Tab(text: 'Manual Entry'),
            ],
          ),
        ),
        body: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 520),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: TabBarView(
                children: [
                  _CsvTab(
                    headers: _csvHeaders,
                    isLoading: _csvLoading,
                    onPickAndUpload: _pickAndUploadCsv,
                  ),
                  _ManualTab(
                    formKey: _manualFormKey,
                    drafts: _drafts,
                    isLoading: _manualLoading,
                    onAdd: _addDraft,
                    onRemove: _removeDraft,
                    onSubmit: _submitManual,
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _CsvTab extends StatelessWidget {
  final String headers;
  final bool isLoading;
  final VoidCallback onPickAndUpload;

  const _CsvTab({required this.headers, required this.isLoading, required this.onPickAndUpload});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Text(
          'Upload inventory CSV',
          style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800),
        ),
        const SizedBox(height: 8),
        Text(
          'Use these headers (owner-friendly). Legacy headers are also accepted by the backend.',
          style: TextStyle(color: Theme.of(context).hintColor),
        ),
        const SizedBox(height: 12),
        SoftSectionCard(
          child: SelectableText(headers, style: const TextStyle(fontFamily: 'monospace', fontSize: 12)),
        ),
        const SizedBox(height: 16),
        PrimaryButton(
          label: 'Choose CSV and Analyze',
          icon: Icons.upload_file,
          isLoading: isLoading,
          onPressed: onPickAndUpload,
        ),
        const SizedBox(height: 10),
        SecondaryButton(
          label: 'Tip: try the sample CSV in the repo',
          icon: Icons.lightbulb_outline,
          onPressed: null,
        ),
      ],
    );
  }
}

class _ManualTab extends StatelessWidget {
  final GlobalKey<FormState> formKey;
  final List<_ManualItemDraft> drafts;
  final bool isLoading;
  final VoidCallback onAdd;
  final void Function(int idx) onRemove;
  final VoidCallback onSubmit;

  const _ManualTab({
    required this.formKey,
    required this.drafts,
    required this.isLoading,
    required this.onAdd,
    required this.onRemove,
    required this.onSubmit,
  });

  @override
  Widget build(BuildContext context) {
    return Form(
      key: formKey,
      child: ListView(
        children: [
          const Text('Manual entry', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
          const SizedBox(height: 8),
          Text(
            'Add multiple items and submit once. Score-driving fields affect recommendations.',
            style: TextStyle(color: Theme.of(context).hintColor),
          ),
          const SizedBox(height: 12),
          ...List.generate(drafts.length, (idx) {
            final d = drafts[idx];
            return Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: SoftSectionCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Row(
                      children: [
                        Text('Item ${idx + 1}', style: const TextStyle(fontWeight: FontWeight.w800)),
                        const Spacer(),
                        IconButton(
                          onPressed: drafts.length <= 1 ? null : () => onRemove(idx),
                          icon: const Icon(Icons.delete_outline),
                          tooltip: 'Remove item',
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    FormInputField(
                      label: 'item_name',
                      controller: d.itemName,
                      validator: (v) => (v == null || v.trim().isEmpty) ? 'Required' : null,
                    ),
                    const SizedBox(height: 10),
                    Row(
                      children: [
                        Expanded(
                          child: FormInputField(
                            label: 'current_stock',
                            controller: d.currentStock,
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
                          child: FormInputField(
                            label: 'unit',
                            controller: d.unit,
                            validator: (v) => (v == null || v.trim().isEmpty) ? 'Required' : null,
                            hintText: 'kg / litre / pieces',
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    Row(
                      children: [
                        Expanded(
                          child: FormInputField(
                            label: 'usage_value',
                            controller: d.usageValue,
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
                            value: d.usagePeriod,
                            onChanged: (v) => d.usagePeriod = v,
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
                            controller: d.leadTimeDays,
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
                            controller: d.pricePerUnit,
                            keyboardType: const TextInputType.numberWithOptions(decimal: true),
                            validator: (v) {
                              final n = double.tryParse((v ?? '').trim());
                              if (n == null) return 'Required';
                              if (n < 0) return 'Must be >= 0';
                              return null;
                            },
                            hintText: 'Estimate is okay',
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    FormDropdown<double>(
                      label: 'seasonal_factor',
                      value: d.seasonalFactor,
                      onChanged: (v) => d.seasonalFactor = v,
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
                      value: d.perishabilityLevel,
                      onChanged: (v) => d.perishabilityLevel = v,
                      items: const [
                        DropdownMenuItem(value: PerishabilityLevel.low, child: Text('Low')),
                        DropdownMenuItem(value: PerishabilityLevel.medium, child: Text('Medium')),
                        DropdownMenuItem(value: PerishabilityLevel.high, child: Text('High')),
                      ],
                    ),
                    const SizedBox(height: 10),
                    FormInputField(
                      label: 'recent_waste_percentage (optional)',
                      controller: d.recentWastePercentage,
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
                      subtitle: Text(
                        'Use these only if you know the exact value. Otherwise, guided choices above are enough.',
                        style: TextStyle(color: Theme.of(context).hintColor, fontSize: 12),
                      ),
                      children: [
                        const SizedBox(height: 10),
                        FormInputField(label: 'category (optional)', controller: d.category),
                        const SizedBox(height: 10),
                        FormInputField(label: 'subcategory (optional)', controller: d.subcategory),
                        const SizedBox(height: 10),
                        FormInputField(label: 'supplier_name (optional)', controller: d.supplierName),
                        const SizedBox(height: 10),
                        FormInputField(
                          label: 'manual_reorder_level (optional)',
                          controller: d.manualReorderLevel,
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
                  ],
                ),
              ),
            );
          }),
          SecondaryButton(label: 'Add Item', icon: Icons.add, onPressed: onAdd),
          const SizedBox(height: 12),
          PrimaryButton(
            label: 'Submit and Analyze',
            icon: Icons.auto_graph,
            isLoading: isLoading,
            onPressed: onSubmit,
          ),
          const SizedBox(height: 20),
        ],
      ),
    );
  }
}

class _ManualItemDraft {
  final TextEditingController itemName;
  final TextEditingController currentStock;
  final TextEditingController unit;
  final TextEditingController usageValue;
  UsagePeriod? usagePeriod;
  final TextEditingController leadTimeDays;
  final TextEditingController pricePerUnit;
  double? seasonalFactor;
  PerishabilityLevel? perishabilityLevel;
  final TextEditingController recentWastePercentage;
  final TextEditingController category;
  final TextEditingController subcategory;
  final TextEditingController supplierName;
  final TextEditingController manualReorderLevel;

  _ManualItemDraft()
      : itemName = TextEditingController(),
        currentStock = TextEditingController(),
        unit = TextEditingController(),
        usageValue = TextEditingController(),
        leadTimeDays = TextEditingController(),
        pricePerUnit = TextEditingController(),
        recentWastePercentage = TextEditingController(),
        category = TextEditingController(),
        subcategory = TextEditingController(),
        supplierName = TextEditingController(),
        manualReorderLevel = TextEditingController();

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
  }

  ManualInventoryItemInput toModel() {
    return ManualInventoryItemInput(
      itemName: itemName.text.trim(),
      currentStock: double.parse(currentStock.text.trim()),
      unit: unit.text.trim(),
      usageValue: double.parse(usageValue.text.trim()),
      usagePeriod: usagePeriod!,
      leadTimeDays: int.parse(leadTimeDays.text.trim()),
      pricePerUnit: double.parse(pricePerUnit.text.trim()),
      seasonalFactor: seasonalFactor!,
      perishabilityLevel: perishabilityLevel,
      recentWastePercentage: recentWastePercentage.text.trim().isEmpty ? null : double.parse(recentWastePercentage.text.trim()),
      category: category.text.trim().isEmpty ? null : category.text.trim(),
      subcategory: subcategory.text.trim().isEmpty ? null : subcategory.text.trim(),
      supplierName: supplierName.text.trim().isEmpty ? null : supplierName.text.trim(),
      manualReorderLevel: manualReorderLevel.text.trim().isEmpty ? null : double.parse(manualReorderLevel.text.trim()),
    );
  }
}

