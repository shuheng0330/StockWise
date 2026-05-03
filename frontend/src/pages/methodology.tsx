import React, { useEffect, useState } from 'react';
import Head from 'next/head';
import Link from 'next/link';
import {
    ArrowLeft,
    ArrowRight,
    Calculator,
    CheckCircle2,
    Database,
    Layers,
    Shield,
    Sparkles,
    Target,
} from 'lucide-react';
import { NavigationBar } from '@/components/Dashboard';
import { Button, Card } from '@/components/common';
import { getLatestAnalysisId } from '@/lib/analysisSession';

const PIPELINE_STAGES = [
    {
        title: '1. Data Intake',
        icon: <Database className="w-5 h-5" />,
        body: 'CSV upload or manual entry. Each record is validated against a strict schema (required columns, types, ranges). Invalid rows are rejected with a clear error message.',
        accent: 'bg-blue-50 border-blue-200 text-blue-900',
        iconBg: 'bg-blue-100 text-blue-700',
    },
    {
        title: '2. Deterministic Scoring',
        icon: <Calculator className="w-5 h-5" />,
        body: 'Backend computes metrics (days of cover, lead-time demand, inventory value, etc.) and two scores (Reorder Urgency, Waste Risk) using fixed mathematical formulas. No AI is involved here.',
        accent: 'bg-emerald-50 border-emerald-200 text-emerald-900',
        iconBg: 'bg-emerald-100 text-emerald-700',
    },
    {
        title: '3. Action Classification',
        icon: <Target className="w-5 h-5" />,
        body: 'Each item is assigned exactly one action label — RESTOCK_NOW, BUY_LESS, DELAY_PURCHASE, or MONITOR_CLOSELY — based on the two scores. Same inputs always produce the same label.',
        accent: 'bg-amber-50 border-amber-200 text-amber-900',
        iconBg: 'bg-amber-100 text-amber-700',
    },
    {
        title: '4. AI Explanation Layer',
        icon: <Sparkles className="w-5 h-5" />,
        body: 'GLM (Z.AI) generates plain-language rationale using the already-computed metrics. AI does not change the recommendation — it explains it. JSON-validated; one strict retry; deterministic fallback if invalid.',
        accent: 'bg-purple-50 border-purple-200 text-purple-900',
        iconBg: 'bg-purple-100 text-purple-700',
    },
];

const COMPUTED_METRICS = [
    {
        name: 'days_of_cover',
        formula: 'current_stock / daily_usage',
        meaning: 'How many days the current stock will last at the current usage rate.',
    },
    {
        name: 'inventory_value',
        formula: 'current_stock × price_per_unit',
        meaning: 'Cash currently tied up in this item.',
    },
    {
        name: 'estimated_waste_cost',
        formula: 'inventory_value × (waste_percentage / 100)',
        meaning: 'Cash exposure from anticipated spoilage.',
    },
    {
        name: 'lead_time_demand',
        formula: 'daily_usage × lead_time × seasonal_factor',
        meaning: 'Quantity that will be consumed before the next replenishment arrives.',
    },
    {
        name: 'stock_gap_to_lead_demand',
        formula: 'current_stock − lead_time_demand',
        meaning: 'Negative values mean a stockout is likely before resupply.',
    },
    {
        name: 'avg_usage_7d & trend_direction',
        formula: 'mean(last 7 days) and direction (up/down/stable)',
        meaning: 'Recent demand momentum, used in the Records view.',
    },
];

export default function MethodologyPage() {
    const [dashboardHref, setDashboardHref] = useState<string>('/');

    useEffect(() => {
        const latestId = getLatestAnalysisId();
        setDashboardHref(latestId ? `/dashboard/${latestId}` : '/');
    }, []);

    return (
        <>
            <Head>
                <title>StockWise — How It Works</title>
            </Head>
            <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
                <NavigationBar activeSection="methodology" onFeatureSelect={() => null} />

                <main className="max-w-5xl mx-auto p-4 md:p-8 space-y-8">
                    {/* Hero */}
                    <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
                        <div className="flex-1 min-w-0">
                            <div className="inline-flex items-center gap-2 mb-3 px-3 py-1 rounded-full bg-indigo-100 text-indigo-700 text-xs font-medium">
                                <Layers className="w-3.5 h-3.5" />
                                Methodology
                            </div>
                            <h1 className="text-3xl md:text-4xl font-bold text-slate-900 mb-3">
                                How StockWise Decides
                            </h1>
                            <p className="text-base md:text-lg text-gray-600 max-w-3xl">
                                Every recommendation you see is the result of a four-stage pipeline: validated data,
                                deterministic scoring, rule-based classification, and an AI explanation layer.
                                <span className="font-medium text-slate-900"> The AI does not pick the action — it explains the math.</span>
                            </p>
                        </div>
                        <Link href={dashboardHref} className="flex-shrink-0">
                            <Button variant="secondary" className="inline-flex items-center gap-1.5 whitespace-nowrap">
                                <ArrowLeft className="w-4 h-4" />
                                Back to Dashboard
                            </Button>
                        </Link>
                    </div>

                    {/* Pipeline */}
                    <Card className="p-6">
                        <h2 className="text-xl font-semibold text-slate-900 mb-1">The pipeline</h2>
                        <p className="text-sm text-gray-600 mb-5">
                            Data flows left-to-right. Stages 1–3 are deterministic; stage 4 is the AI layer.
                        </p>
                        <div className="grid gap-4 md:grid-cols-2">
                            {PIPELINE_STAGES.map((stage, idx) => (
                                <div
                                    key={stage.title}
                                    className={`rounded-lg border p-4 ${stage.accent} relative`}
                                >
                                    <div className={`inline-flex items-center justify-center w-8 h-8 rounded-lg mb-3 ${stage.iconBg}`}>
                                        {stage.icon}
                                    </div>
                                    <h3 className="font-semibold text-base mb-1">{stage.title}</h3>
                                    <p className="text-sm leading-relaxed opacity-90">{stage.body}</p>
                                    {idx < PIPELINE_STAGES.length - 1 && (
                                        <ArrowRight className="hidden md:block absolute -right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 bg-white rounded-full" />
                                    )}
                                </div>
                            ))}
                        </div>
                    </Card>

                    {/* What goes in */}
                    <Card className="p-6">
                        <h2 className="text-xl font-semibold text-slate-900 mb-1">What you provide</h2>
                        <p className="text-sm text-gray-600 mb-4">
                            Eight required inputs per item (with three optional waste / category fields).
                            See the{' '}
                            <Link href="/" className="text-indigo-600 hover:underline">
                                CSV format reference on the home page
                            </Link>{' '}
                            for the full schema.
                        </p>
                        <div className="grid gap-2 sm:grid-cols-2 text-sm">
                            {[
                                { name: 'item_name', desc: 'identifier' },
                                { name: 'current_stock', desc: 'how much is on hand' },
                                { name: 'unit', desc: 'kg, liter, pieces, etc.' },
                                { name: 'usage_value + period', desc: 'consumption rate' },
                                { name: 'lead_time_days', desc: 'days to receive an order' },
                                { name: 'price_per_unit', desc: 'cost per unit' },
                                { name: 'seasonal_factor', desc: 'demand multiplier (typ. 0.8–1.5)' },
                                { name: 'waste signal', desc: 'perishability OR recent waste %' },
                            ].map((field) => (
                                <div key={field.name} className="flex items-baseline gap-2 p-2 rounded bg-slate-50">
                                    <code className="text-xs font-mono text-slate-900 whitespace-nowrap">{field.name}</code>
                                    <span className="text-gray-600 text-xs">{field.desc}</span>
                                </div>
                            ))}
                        </div>
                    </Card>

                    {/* Computed metrics */}
                    <Card className="p-6">
                        <h2 className="text-xl font-semibold text-slate-900 mb-1">Stage 2a — Computed metrics</h2>
                        <p className="text-sm text-gray-600 mb-4">
                            From your inputs, the backend computes six derived metrics. These are visible on every dashboard card.
                        </p>
                        <div className="overflow-x-auto -mx-2 sm:mx-0">
                            <table className="w-full text-sm border-collapse">
                                <thead>
                                    <tr className="bg-slate-50 border-b border-slate-200">
                                        <th className="text-left py-2 px-3 font-semibold text-gray-700">Metric</th>
                                        <th className="text-left py-2 px-3 font-semibold text-gray-700">Formula</th>
                                        <th className="text-left py-2 px-3 font-semibold text-gray-700">Meaning</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {COMPUTED_METRICS.map((m) => (
                                        <tr key={m.name} className="border-b border-slate-100">
                                            <td className="py-2 px-3 font-mono text-xs text-slate-900 align-top">{m.name}</td>
                                            <td className="py-2 px-3 font-mono text-xs text-emerald-700 align-top">{m.formula}</td>
                                            <td className="py-2 px-3 text-gray-700 align-top">{m.meaning}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </Card>

                    {/* Scoring */}
                    <Card className="p-6">
                        <h2 className="text-xl font-semibold text-slate-900 mb-1">Stage 2b — The two scores</h2>
                        <p className="text-sm text-gray-600 mb-4">
                            Both scores are bounded to the 0–100 range so they're comparable across items.
                        </p>

                        <div className="grid gap-4 md:grid-cols-2">
                            <div className="rounded-lg border border-rose-200 bg-rose-50 p-4">
                                <h3 className="font-semibold text-rose-900 mb-2">Reorder Urgency Score</h3>
                                <p className="text-sm text-rose-900 mb-3">
                                    How critical it is to place an order now, weighted by stockout risk and item importance.
                                </p>
                                <div className="space-y-2 text-xs font-mono bg-white border border-rose-100 rounded p-3 leading-relaxed">
                                    <div>
                                        <span className="text-rose-700">stockout_risk</span> = (lead_time_demand − current_stock) / lead_time_demand
                                    </div>
                                    <div>
                                        <span className="text-rose-700">reorder_gap</span> = (reorder_level − current_stock) / reorder_level
                                    </div>
                                    <div>
                                        <span className="text-rose-700">importance</span> = 15·(usage_share) + 10·(lead_time_share)
                                    </div>
                                    <div className="pt-2 border-t border-rose-100">
                                        <span className="text-rose-900 font-semibold">urgency</span> = 50·stockout_risk + 25·reorder_gap + importance·multiplier
                                    </div>
                                </div>
                                <p className="text-xs text-rose-800 mt-2 italic">
                                    Drops to 0 when current stock is significantly above the reorder level (overstocked).
                                </p>
                            </div>

                            <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
                                <h3 className="font-semibold text-amber-900 mb-2">Waste Risk Score</h3>
                                <p className="text-sm text-amber-900 mb-3">
                                    How likely it is the current stock will spoil before being used, weighted against urgency.
                                </p>
                                <div className="space-y-2 text-xs font-mono bg-white border border-amber-100 rounded p-3 leading-relaxed">
                                    <div>
                                        <span className="text-amber-700">base_waste</span> = waste_percentage × 10
                                    </div>
                                    <div>
                                        <span className="text-amber-700">discount</span> = urgency_score × 0.25
                                    </div>
                                    <div>
                                        <span className="text-amber-700">overstock_ratio</span> = clamp((days_of_cover − expected_cover) / threshold)
                                    </div>
                                    <div className="pt-2 border-t border-amber-100">
                                        <span className="text-amber-900 font-semibold">waste_risk</span> = (base_waste − discount) + 65·overstock_ratio
                                    </div>
                                </div>
                                <p className="text-xs text-amber-800 mt-2 italic">
                                    High urgency reduces waste risk — if you need to reorder soon, you won't waste current stock.
                                </p>
                            </div>
                        </div>
                    </Card>

                    {/* Action classification */}
                    <Card className="p-6">
                        <h2 className="text-xl font-semibold text-slate-900 mb-1">Stage 3 — Action classification</h2>
                        <p className="text-sm text-gray-600 mb-4">
                            Rules applied in order. The first match wins. Same inputs always produce the same action.
                        </p>
                        <div className="space-y-2">
                            {[
                                {
                                    rule: 'urgency ≥ 55  OR  stock_gap_to_lead_demand < 0',
                                    action: 'RESTOCK_NOW',
                                    color: 'bg-rose-100 text-rose-800 border-rose-200',
                                },
                                {
                                    rule: 'waste_risk ≥ 60  AND  urgency < 55',
                                    action: 'BUY_LESS',
                                    color: 'bg-amber-100 text-amber-800 border-amber-200',
                                },
                                {
                                    rule: 'urgency ≤ 35  AND  waste_risk ≤ 45',
                                    action: 'DELAY_PURCHASE',
                                    color: 'bg-emerald-100 text-emerald-800 border-emerald-200',
                                },
                                {
                                    rule: 'otherwise',
                                    action: 'MONITOR_CLOSELY',
                                    color: 'bg-slate-100 text-slate-700 border-slate-200',
                                },
                            ].map((row) => (
                                <div key={row.action} className="flex items-center gap-3 p-3 border rounded-lg bg-slate-50">
                                    <code className="flex-1 text-xs text-gray-700">{row.rule}</code>
                                    <ArrowRight className="w-4 h-4 text-gray-400 flex-shrink-0" />
                                    <span className={`inline-flex items-center px-2 py-1 text-xs font-mono font-semibold rounded border ${row.color}`}>
                                        {row.action}
                                    </span>
                                </div>
                            ))}
                        </div>
                    </Card>

                    {/* AI's role */}
                    <Card className="p-6">
                        <h2 className="text-xl font-semibold text-slate-900 mb-1">Stage 4 — Where AI fits in</h2>
                        <p className="text-sm text-gray-600 mb-4">
                            AI is a presentation layer over deterministic scoring. It writes the &quot;why&quot;, not the &quot;what&quot;.
                        </p>

                        <div className="grid gap-3 sm:grid-cols-2">
                            <div className="p-4 rounded-lg border-2 border-emerald-200 bg-emerald-50">
                                <h3 className="font-semibold text-emerald-900 mb-2 flex items-center gap-2">
                                    <CheckCircle2 className="w-4 h-4" />
                                    What AI does
                                </h3>
                                <ul className="text-sm text-emerald-900 space-y-1.5 list-disc list-inside">
                                    <li>Writes plain-language explanations of urgency &amp; waste scores</li>
                                    <li>Generates the dashboard-level Decision Brief</li>
                                    <li>Powers the AI Copilot Chat (grounded to current analysis)</li>
                                    <li>Translates technical metrics into actionable language</li>
                                </ul>
                            </div>
                            <div className="p-4 rounded-lg border-2 border-rose-200 bg-rose-50">
                                <h3 className="font-semibold text-rose-900 mb-2">What AI does not do</h3>
                                <ul className="text-sm text-rose-900 space-y-1.5 list-disc list-inside">
                                    <li>Compute scores — those are deterministic Python formulas</li>
                                    <li>Choose the action — that&apos;s rule-based classification</li>
                                    <li>Modify inputs — your data is immutable in the pipeline</li>
                                    <li>Hallucinate numbers — JSON-validated, strict retry, fallback ready</li>
                                </ul>
                            </div>
                        </div>

                        <div className="mt-4 p-4 rounded-lg bg-indigo-50 border border-indigo-200">
                            <h3 className="font-semibold text-indigo-900 mb-2 flex items-center gap-2">
                                <Shield className="w-4 h-4" />
                                Reliability guarantees
                            </h3>
                            <ul className="text-sm text-indigo-900 space-y-1.5 list-disc list-inside">
                                <li><span className="font-medium">JSON validation:</span> every AI response is parsed against a strict schema before being shown.</li>
                                <li><span className="font-medium">One strict retry:</span> if the first response is invalid, AI is re-prompted with stricter instructions.</li>
                                <li><span className="font-medium">Deterministic fallback:</span> if AI fails twice, the system shows a deterministic explanation built from the same metrics — the user is never blocked.</li>
                                <li><span className="font-medium">Mock mode:</span> the entire app runs without an AI provider, using fixture responses — useful for offline demos and CI.</li>
                            </ul>
                        </div>
                    </Card>

                    {/* Why this matters */}
                    <Card className="p-6 bg-gradient-to-r from-slate-900 to-slate-800 text-white">
                        <h2 className="text-xl font-semibold mb-3">Why this architecture</h2>
                        <p className="text-sm text-slate-200 mb-4">
                            Pure-LLM systems give different answers to the same question. SME owners need consistency.
                            Our design separates <span className="font-medium text-white">decisions</span> (rule-based, auditable) from <span className="font-medium text-white">explanations</span> (LLM, friendly).
                        </p>
                        <div className="grid gap-3 sm:grid-cols-3 text-sm">
                            <div>
                                <p className="font-medium text-white">Trustable</p>
                                <p className="text-slate-300 text-xs mt-1">Same inputs → same recommendation. Every time.</p>
                            </div>
                            <div>
                                <p className="font-medium text-white">Auditable</p>
                                <p className="text-slate-300 text-xs mt-1">Every score traces back to its formula and inputs.</p>
                            </div>
                            <div>
                                <p className="font-medium text-white">Resilient</p>
                                <p className="text-slate-300 text-xs mt-1">Works even when the LLM is down — with deterministic fallback.</p>
                            </div>
                        </div>
                    </Card>

                    {/* Footer link */}
                    <div className="text-center text-sm text-gray-500 pb-4">
                        <Link href="/judge-mode" className="text-indigo-600 hover:underline">
                            See live system status →
                        </Link>
                    </div>
                </main>
            </div>
        </>
    );
}
