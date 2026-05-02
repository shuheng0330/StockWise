import React, { useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { Github, Shield, Trash2 } from 'lucide-react';
import { NavigationBar } from '@/components/Dashboard';
import { Button, Card, Select } from '@/components/common';
import {
    clearAnalysisHistory,
    clearLatestAnalysisId,
    getAnalysisHistory,
    getLatestAnalysisId,
} from '@/lib/analysisSession';

const DENSITY_KEY = 'stockwise-table-density';

type Density = 'comfortable' | 'compact' | 'spacious';

const DENSITY_OPTIONS: Array<{ value: Density; label: string }> = [
    { value: 'comfortable', label: 'Comfortable' },
    { value: 'compact', label: 'Compact' },
    { value: 'spacious', label: 'Spacious' },
];

function applyDensityClass(density: Density) {
    if (typeof document === 'undefined') return;
    const root = document.documentElement;
    root.classList.remove('density-comfortable', 'density-compact', 'density-spacious');
    root.classList.add(`density-${density}`);
}

export default function SettingsPage() {
    const [density, setDensity] = useState<Density>('comfortable');
    const [historyCount, setHistoryCount] = useState(0);
    const [hasLatestAnalysis, setHasLatestAnalysis] = useState(false);

    useEffect(() => {
        const stored = (localStorage.getItem(DENSITY_KEY) as Density | null) ?? 'comfortable';
        setDensity(stored);
        applyDensityClass(stored);
    }, []);

    useEffect(() => {
        setHistoryCount(getAnalysisHistory().length);
        setHasLatestAnalysis(Boolean(getLatestAnalysisId()));
    }, []);

    const handleDensityChange = (value: Density) => {
        setDensity(value);
        localStorage.setItem(DENSITY_KEY, value);
        applyDensityClass(value);
        toast.success(`Table density set to ${value}`);
    };

    const handleClearHistory = () => {
        if (historyCount === 0) return;
        if (!confirm(`Clear ${historyCount} entries from local history? This cannot be undone.`)) return;
        clearAnalysisHistory();
        setHistoryCount(0);
        toast.success('Entry history cleared');
    };

    const handleClearLatest = () => {
        if (!hasLatestAnalysis) return;
        if (!confirm('Clear the cached analysis ID? You will need to upload or enter data again to view a dashboard.')) return;
        clearLatestAnalysisId();
        setHasLatestAnalysis(false);
        toast.success('Cached analysis cleared');
    };

    const githubRepo = process.env.NEXT_PUBLIC_GITHUB_REPO ?? 'https://github.com/shuheng0330/StockWise';
    const frontendVersion = '0.1.0';

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
            <NavigationBar activeSection="settings" onFeatureSelect={() => null} />

            <main className="max-w-5xl mx-auto p-4 md:p-8">
                <div className="mb-8">
                    <h1 className="text-3xl md:text-4xl font-bold text-slate-900">Settings</h1>
                    <p className="mt-2 text-gray-600 max-w-2xl text-sm md:text-base">
                        Manage display preferences and locally cached data.
                    </p>
                </div>

                <div className="grid gap-6">
                    <Card className="p-6">
                        <h2 className="text-xl font-semibold text-slate-900 mb-2">Display</h2>
                        <p className="text-sm text-gray-600 mb-4">
                            Choose how dense data tables appear across the app. Applies to the dashboard, records, and export tables.
                        </p>
                        <div className="max-w-xs">
                            <Select
                                label="Table density"
                                value={density}
                                onChange={(e) => handleDensityChange(e.target.value as Density)}
                                options={DENSITY_OPTIONS}
                            />
                        </div>
                    </Card>

                    <Card className="p-6">
                        <h2 className="text-xl font-semibold text-slate-900 mb-2">Data Management</h2>
                        <p className="text-sm text-gray-600 mb-4">
                            Clear locally cached data stored by this browser. This does not affect your saved data on the server.
                        </p>
                        <div className="space-y-3">
                            <div className="flex flex-wrap items-center justify-between gap-3 p-4 border rounded-lg bg-slate-50">
                                <div>
                                    <p className="text-sm font-medium text-slate-900">Entry history</p>
                                    <p className="text-sm text-gray-600">
                                        {historyCount === 0
                                            ? 'No entries logged'
                                            : `${historyCount} entr${historyCount === 1 ? 'y' : 'ies'} logged`}
                                    </p>
                                </div>
                                <Button
                                    variant="outline"
                                    onClick={handleClearHistory}
                                    disabled={historyCount === 0}
                                    className="inline-flex items-center gap-2"
                                >
                                    <Trash2 className="w-4 h-4" />
                                    Clear history
                                </Button>
                            </div>

                            <div className="flex flex-wrap items-center justify-between gap-3 p-4 border rounded-lg bg-slate-50">
                                <div>
                                    <p className="text-sm font-medium text-slate-900">Cached latest analysis</p>
                                    <p className="text-sm text-gray-600">
                                        {hasLatestAnalysis
                                            ? 'A cached analysis ID is stored'
                                            : 'No cached analysis'}
                                    </p>
                                </div>
                                <Button
                                    variant="outline"
                                    onClick={handleClearLatest}
                                    disabled={!hasLatestAnalysis}
                                    className="inline-flex items-center gap-2"
                                >
                                    <Trash2 className="w-4 h-4" />
                                    Clear cache
                                </Button>
                            </div>
                        </div>
                    </Card>

                    <Card className="p-6">
                        <h2 className="text-xl font-semibold text-slate-900 mb-3">About</h2>
                        <dl className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm mb-4">
                            <div className="p-3 border rounded-lg bg-slate-50">
                                <dt className="text-xs uppercase tracking-wider text-gray-500">Frontend version</dt>
                                <dd className="text-slate-900 font-medium mt-1">v{frontendVersion}</dd>
                            </div>
                            <div className="p-3 border rounded-lg bg-slate-50">
                                <dt className="text-xs uppercase tracking-wider text-gray-500">Project</dt>
                                <dd className="text-slate-900 font-medium mt-1">StockWise — UMHack 2026</dd>
                            </div>
                        </dl>
                        <div className="flex flex-wrap gap-4 text-sm">
                            <a
                                href={githubRepo}
                                target="_blank"
                                rel="noreferrer"
                                className="inline-flex items-center gap-1.5 text-indigo-600 hover:underline"
                            >
                                <Github className="w-4 h-4" />
                                GitHub repository
                            </a>
                            <a
                                href={`${githubRepo}/blob/main/SECURITY.md`}
                                target="_blank"
                                rel="noreferrer"
                                className="inline-flex items-center gap-1.5 text-indigo-600 hover:underline"
                            >
                                <Shield className="w-4 h-4" />
                                Security policy
                            </a>
                        </div>
                    </Card>
                </div>
            </main>
        </div>
    );
}
