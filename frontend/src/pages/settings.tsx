import React, { useEffect, useState } from 'react';
import { NavigationBar } from '@/components/Dashboard';
import { Button, Card, Input, Select, Alert } from '@/components/common';

const STORAGE_KEY = 'stockwise-settings';

const defaultValues = {
    defaultUsagePeriod: 'daily',
    defaultExportFormat: 'csv',
    tableDensity: 'comfortable',
    showRecommendations: true,
    showWasteAlerts: true,
};

export default function SettingsPage() {
    const [defaultUsagePeriod, setDefaultUsagePeriod] = useState(defaultValues.defaultUsagePeriod);
    const [defaultExportFormat, setDefaultExportFormat] = useState(defaultValues.defaultExportFormat);
    const [tableDensity, setTableDensity] = useState(defaultValues.tableDensity);
    const [showRecommendations, setShowRecommendations] = useState(defaultValues.showRecommendations);
    const [showWasteAlerts, setShowWasteAlerts] = useState(defaultValues.showWasteAlerts);
    const [saveStatus, setSaveStatus] = useState<'idle' | 'saved' | 'error'>('idle');

    useEffect(() => {
        if (typeof window === 'undefined') return;
        try {
            const stored = localStorage.getItem(STORAGE_KEY);
            if (!stored) return;
            const parsed = JSON.parse(stored);
            setDefaultUsagePeriod(parsed.defaultUsagePeriod ?? defaultValues.defaultUsagePeriod);
            setDefaultExportFormat(parsed.defaultExportFormat ?? defaultValues.defaultExportFormat);
            setTableDensity(parsed.tableDensity ?? defaultValues.tableDensity);
            setShowRecommendations(parsed.showRecommendations ?? defaultValues.showRecommendations);
            setShowWasteAlerts(parsed.showWasteAlerts ?? defaultValues.showWasteAlerts);
        } catch {
            // ignore invalid stored settings
        }
    }, []);

    const handleSave = () => {
        try {
            const settings = {
                defaultUsagePeriod,
                defaultExportFormat,
                tableDensity,
                showRecommendations,
                showWasteAlerts,
            };
            localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
            setSaveStatus('saved');
            window.setTimeout(() => setSaveStatus('idle'), 3000);
        } catch {
            setSaveStatus('error');
        }
    };

    const handleReset = () => {
        setDefaultUsagePeriod(defaultValues.defaultUsagePeriod);
        setDefaultExportFormat(defaultValues.defaultExportFormat);
        setTableDensity(defaultValues.tableDensity);
        setShowRecommendations(defaultValues.showRecommendations);
        setShowWasteAlerts(defaultValues.showWasteAlerts);
        setSaveStatus('idle');
        localStorage.removeItem(STORAGE_KEY);
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
            <NavigationBar activeSection="settings" onFeatureSelect={() => null} />

            <main className="max-w-6xl mx-auto p-4 md:p-8">
                <div className="mb-8">
                    <h1 className="text-4xl font-bold text-slate-900">Settings</h1>
                    <p className="mt-3 text-gray-600 max-w-2xl">
                        Configure StockWise behavior for analysis defaults, export preferences, and display settings.
                        These preferences are stored locally in your browser and help streamline future workflows.
                    </p>
                </div>

                <div className="grid gap-6">
                    <Card className="p-6">
                        <div className="flex flex-col gap-3">
                            <h2 className="text-2xl font-semibold text-slate-900">Analysis Preferences</h2>
                            <p className="text-sm text-gray-600">
                                Choose default behaviors for newly created inventory analyses.
                            </p>

                            <div className="grid gap-4 md:grid-cols-2">
                                <Select
                                    label="Default usage period"
                                    value={defaultUsagePeriod}
                                    onChange={(e) => setDefaultUsagePeriod(e.target.value)}
                                    options={[
                                        { value: 'daily', label: 'Daily' },
                                        { value: 'weekly', label: 'Weekly' },
                                    ]}
                                />
                                <Select
                                    label="Default export format"
                                    value={defaultExportFormat}
                                    onChange={(e) => setDefaultExportFormat(e.target.value)}
                                    options={[
                                        { value: 'csv', label: 'CSV' },
                                        { value: 'xlsx', label: 'XLSX' },
                                        { value: 'pdf', label: 'PDF' },
                                    ]}
                                />
                            </div>
                        </div>
                    </Card>

                    <Card className="p-6">
                        <div className="flex flex-col gap-3">
                            <h2 className="text-2xl font-semibold text-slate-900">Display Preferences</h2>
                            <p className="text-sm text-gray-600">
                                Adjust table density and on-screen alerts to match your reporting style.
                            </p>

                            <div className="grid gap-4 md:grid-cols-2">
                                <Select
                                    label="Table density"
                                    value={tableDensity}
                                    onChange={(e) => setTableDensity(e.target.value)}
                                    options={[
                                        { value: 'comfortable', label: 'Comfortable' },
                                        { value: 'compact', label: 'Compact' },
                                        { value: 'spacious', label: 'Spacious' },
                                    ]}
                                />

                                <div className="space-y-3">
                                    <div className="flex items-center justify-between gap-3 p-4 border rounded-lg bg-slate-50">
                                        <div>
                                            <p className="text-sm font-medium text-slate-900">Show recommendation warnings</p>
                                            <p className="text-sm text-gray-600">Display alert labels for urgent restock and waste risk items.</p>
                                        </div>
                                        <label className="inline-flex items-center gap-2 text-sm text-slate-700">
                                            <input
                                                type="checkbox"
                                                checked={showRecommendations}
                                                onChange={(e) => setShowRecommendations(e.target.checked)}
                                                className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                                            />
                                        </label>
                                    </div>

                                    <div className="flex items-center justify-between gap-3 p-4 border rounded-lg bg-slate-50">
                                        <div>
                                            <p className="text-sm font-medium text-slate-900">Show waste risk alerts</p>
                                            <p className="text-sm text-gray-600">Toggle on-screen notifications for high waste-risk inventory items.</p>
                                        </div>
                                        <label className="inline-flex items-center gap-2 text-sm text-slate-700">
                                            <input
                                                type="checkbox"
                                                checked={showWasteAlerts}
                                                onChange={(e) => setShowWasteAlerts(e.target.checked)}
                                                className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                                            />
                                        </label>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </Card>

                    <Card className="p-6">
                        <div className="flex flex-col gap-3">
                            <h2 className="text-2xl font-semibold text-slate-900">Data & Export</h2>
                            <p className="text-sm text-gray-600">Control how inventory reports are generated and exported from StockWise.</p>

                            <div className="grid gap-4 md:grid-cols-2">
                                <Input
                                    label="Preferred report name prefix"
                                    value="stockwise-report"
                                    readOnly
                                />
                                <Input
                                    label="Default note for exports"
                                    value="Inventory recommendations generated by StockWise"
                                    readOnly
                                />
                            </div>
                        </div>
                    </Card>

                    {saveStatus === 'saved' && (
                        <Alert type="success" message="Settings saved locally in your browser." />
                    )}
                    {saveStatus === 'error' && (
                        <Alert type="error" message="Unable to save settings. Please try again." />
                    )}

                    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                        <div className="space-x-3">
                            <Button variant="primary" onClick={handleSave}>
                                Save Settings
                            </Button>
                            <Button variant="secondary" onClick={handleReset}>
                                Reset to Defaults
                            </Button>
                        </div>
                        <p className="text-sm text-gray-600 max-w-2xl">
                            These settings are for the current browser only. They are not tied to a user profile or login.
                        </p>
                    </div>
                </div>
            </main>
        </div>
    );
}
