import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import {
    ArrowLeft,
    ArrowRight,
    CheckCircle2,
    ClipboardList,
    Lightbulb,
    MessageSquare,
    Package,
    Sparkles,
    X,
} from 'lucide-react';

const TOUR_KEY = 'stockwise-tour-seen-v1';

interface TourStep {
    icon: React.ReactNode;
    title: string;
    body: string;
    accent: string;
    iconBg: string;
}

const STEPS: TourStep[] = [
    {
        icon: <Package className="w-7 h-7" />,
        title: 'Welcome to StockWise',
        body:
            'We help small cafes, stalls, and kiosks decide what to reorder — so you never run out of stock, and never waste money on items you bought too much of.',
        accent: 'bg-indigo-50',
        iconBg: 'bg-indigo-100 text-indigo-700',
    },
    {
        icon: <ClipboardList className="w-7 h-7" />,
        title: 'Step 1: Tell us about your stock',
        body:
            'Upload a CSV file or fill in our simple form. For each item, we just need to know how much you have, how fast you use it, and how long your supplier takes to deliver.',
        accent: 'bg-blue-50',
        iconBg: 'bg-blue-100 text-blue-700',
    },
    {
        icon: <Sparkles className="w-7 h-7" />,
        title: 'Step 2: We calculate the risks',
        body:
            'Our system works out which items are about to run out, which might spoil, and which are just right. Same data always gives the same answer — no guessing.',
        accent: 'bg-emerald-50',
        iconBg: 'bg-emerald-100 text-emerald-700',
    },
    {
        icon: <Lightbulb className="w-7 h-7" />,
        title: 'Step 3: Follow the action list',
        body:
            'Each item gets one clear label so you know what to do today. Open the dashboard daily and follow the list — sorted from most urgent to least.',
        accent: 'bg-amber-50',
        iconBg: 'bg-amber-100 text-amber-700',
    },
    {
        icon: <MessageSquare className="w-7 h-7" />,
        title: 'Bonus: AI explains the "why"',
        body:
            'Click any item to see a plain-language explanation of why we recommend that action. You stay in control — the AI just translates the numbers into advice you can act on.',
        accent: 'bg-purple-50',
        iconBg: 'bg-purple-100 text-purple-700',
    },
];

const ACTION_LABELS: Array<{ emoji: string; label: string; meaning: string; color: string }> = [
    { emoji: '🔴', label: 'Buy Now', meaning: 'Stock running out — order today', color: 'bg-rose-50 text-rose-900 border-rose-200' },
    { emoji: '🟡', label: 'Buy Less', meaning: 'Risk of spoilage — reduce next order', color: 'bg-amber-50 text-amber-900 border-amber-200' },
    { emoji: '🟢', label: 'Wait', meaning: 'Plenty of stock — delay reorder', color: 'bg-emerald-50 text-emerald-900 border-emerald-200' },
    { emoji: '🔵', label: 'Watch', meaning: 'No urgent action — keep an eye on it', color: 'bg-sky-50 text-sky-900 border-sky-200' },
];

interface GuidedTourProps {
    open: boolean;
    onClose: () => void;
}

export function GuidedTour({ open, onClose }: GuidedTourProps) {
    const [stepIndex, setStepIndex] = useState(0);

    useEffect(() => {
        if (open) setStepIndex(0);
    }, [open]);

    useEffect(() => {
        if (!open) return;
        const handleKey = (e: KeyboardEvent) => {
            if (e.key === 'Escape') onClose();
            if (e.key === 'ArrowRight') setStepIndex((i) => Math.min(STEPS.length - 1, i + 1));
            if (e.key === 'ArrowLeft') setStepIndex((i) => Math.max(0, i - 1));
        };
        window.addEventListener('keydown', handleKey);
        return () => window.removeEventListener('keydown', handleKey);
    }, [open, onClose]);

    if (!open) return null;

    const step = STEPS[stepIndex];
    const isLast = stepIndex === STEPS.length - 1;
    const isFirst = stepIndex === 0;

    const handleClose = () => {
        try {
            localStorage.setItem(TOUR_KEY, '1');
        } catch {
            // ignore
        }
        onClose();
    };

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm"
            onClick={handleClose}
            role="dialog"
            aria-modal="true"
            aria-label="StockWise quick tour"
        >
            <div
                className="relative w-full max-w-lg bg-white rounded-2xl shadow-2xl overflow-hidden"
                onClick={(e) => e.stopPropagation()}
            >
                <button
                    type="button"
                    onClick={handleClose}
                    className="absolute top-4 right-4 p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition"
                    aria-label="Close"
                >
                    <X className="w-5 h-5" />
                </button>

                <div className={`${step.accent} p-8 pt-10 text-center`}>
                    <div
                        className={`inline-flex items-center justify-center w-14 h-14 rounded-2xl ${step.iconBg} mb-4`}
                    >
                        {step.icon}
                    </div>
                    <h2 className="text-2xl font-bold text-slate-900 mb-3">{step.title}</h2>
                    <p className="text-base text-slate-700 leading-relaxed max-w-md mx-auto">
                        {step.body}
                    </p>

                    {/* Step 3: show the action labels inline */}
                    {stepIndex === 3 && (
                        <div className="mt-5 grid grid-cols-2 gap-2 text-left">
                            {ACTION_LABELS.map((a) => (
                                <div key={a.label} className={`p-2.5 rounded-lg border text-xs ${a.color}`}>
                                    <div className="font-semibold mb-0.5">
                                        {a.emoji} {a.label}
                                    </div>
                                    <div className="opacity-80">{a.meaning}</div>
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Last step: methodology link for technical readers */}
                    {isLast && (
                        <Link
                            href="/methodology"
                            className="inline-block mt-4 text-sm text-indigo-600 hover:underline"
                            onClick={handleClose}
                        >
                            See the full technical breakdown →
                        </Link>
                    )}
                </div>

                <div className="bg-white p-5 flex items-center justify-between gap-3">
                    {/* Progress dots */}
                    <div className="flex items-center gap-1.5">
                        {STEPS.map((_, i) => (
                            <button
                                key={i}
                                type="button"
                                onClick={() => setStepIndex(i)}
                                aria-label={`Go to step ${i + 1}`}
                                className={`h-2 rounded-full transition-all ${
                                    i === stepIndex
                                        ? 'w-6 bg-indigo-600'
                                        : i < stepIndex
                                            ? 'w-2 bg-indigo-300'
                                            : 'w-2 bg-slate-200'
                                }`}
                            />
                        ))}
                    </div>

                    <div className="flex items-center gap-2">
                        {!isFirst && (
                            <button
                                type="button"
                                onClick={() => setStepIndex((i) => Math.max(0, i - 1))}
                                className="inline-flex items-center gap-1 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 rounded-lg transition"
                            >
                                <ArrowLeft className="w-4 h-4" />
                                Back
                            </button>
                        )}
                        {isLast ? (
                            <button
                                type="button"
                                onClick={handleClose}
                                className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition"
                            >
                                <CheckCircle2 className="w-4 h-4" />
                                Got it
                            </button>
                        ) : (
                            <button
                                type="button"
                                onClick={() => setStepIndex((i) => Math.min(STEPS.length - 1, i + 1))}
                                className="inline-flex items-center gap-1 px-4 py-2 text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition"
                            >
                                Next
                                <ArrowRight className="w-4 h-4" />
                            </button>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}

export function shouldAutoOpenTour(): boolean {
    if (typeof window === 'undefined') return false;
    try {
        return localStorage.getItem(TOUR_KEY) !== '1';
    } catch {
        return false;
    }
}
