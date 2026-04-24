import {
    getLatestAnalysisId,
    hydrateLatestAnalysisId,
    saveLatestAnalysisId,
    subscribeToLatestAnalysisId,
} from '@/lib/analysisSession';
import { useAuth } from '@/lib/auth';
import { buildAnalysisNavigationTargets } from '@/lib/navigationTargets';
import { apiClient } from '@/services/api';
import {
    BarChart3,
    Database,
    FileCheck,
    FileText,
    History,
    Home,
    LogOut,
    Menu,
    Settings,
    Upload,
    X
} from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import React, { useEffect, useState } from 'react';

interface NavItemProps {
    icon: React.ReactNode;
    label: string;
    href?: string;
    onClick?: () => void;
    disabled?: boolean;
    active?: boolean;
    fullWidth?: boolean;
}

function NavItem({ icon, label, href, onClick, disabled, active, fullWidth }: NavItemProps) {
    const baseClasses = `flex items-center gap-2 rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-200 whitespace-nowrap ${fullWidth ? 'w-full justify-start lg:w-auto' : ''}`.trim();
    const stateClasses = disabled
        ? "cursor-not-allowed text-gray-400"
        : active
            ? "bg-blue-600 text-white shadow-sm"
            : "text-slate-700 hover:bg-white hover:text-slate-900";

    const content = (
        <>
            {icon}
            <span className="font-medium">{label}</span>
        </>
    );

    if (disabled) {
        return (
            <div className={`${baseClasses} ${stateClasses}`}>
                {content}
            </div>
        );
    }

    if (href) {
        return (
            <Link href={href} className={`${baseClasses} ${stateClasses}`} onClick={onClick}>
                {content}
            </Link>
        );
    }

    return (
        <button type="button" onClick={onClick} className={`${baseClasses} ${stateClasses}`}>
            {content}
        </button>
    );
}

interface NavigationBarProps {
    onFeatureSelect: (feature: 'upload' | 'manual') => void;
    currentAnalysisId?: string;
    currentItemId?: string | number;
    activeSection?: string;
}

export function NavigationBar({ onFeatureSelect, currentAnalysisId, currentItemId, activeSection }: NavigationBarProps) {
    const router = useRouter();
    const { signOut } = useAuth();
    const [storedAnalysisId, setStoredAnalysisId] = useState<string | null>(null);
    const [mobileOpen, setMobileOpen] = useState(false);
    const [dataEntryOpen, setDataEntryOpen] = useState(false);
    const activeAnalysisId = currentAnalysisId || storedAnalysisId || undefined;
    const navigationTargets = buildAnalysisNavigationTargets(activeAnalysisId, currentItemId);

    const handleLogout = async () => {
        await signOut();
        router.push('/login');
    };

    useEffect(() => {
        let isMounted = true;
        setStoredAnalysisId(getLatestAnalysisId());
        const unsubscribe = subscribeToLatestAnalysisId(setStoredAnalysisId);

        if (!currentAnalysisId) {
            hydrateLatestAnalysisId(async () => {
                const analysis = await apiClient.getLatestAnalysis();
                return analysis.analysis_id;
            })
                .then((analysisId) => {
                    if (isMounted) {
                        setStoredAnalysisId(analysisId);
                    }
                })
                .catch(() => {
                    if (isMounted) {
                        setStoredAnalysisId(getLatestAnalysisId());
                    }
                });
        }

        return () => {
            isMounted = false;
            unsubscribe();
        };
    }, [currentAnalysisId]);

    useEffect(() => {
        if (currentAnalysisId) {
            saveLatestAnalysisId(currentAnalysisId);
        }
    }, [currentAnalysisId]);

    const closeMobile = () => {
        setMobileOpen(false);
        setDataEntryOpen(false);
    };

    const handleFeature = (feature: 'upload' | 'manual') => {
        closeMobile();
        if (router.pathname === '/') {
            onFeatureSelect(feature);
        } else {
            router.push(`/?mode=${feature}`);
        }
    };

    const navLinks = (
        <>
            <NavItem
                icon={<Home className="w-5 h-5" />}
                label="Home"
                href="/"
                active={activeSection === 'home'}
                onClick={closeMobile}
                fullWidth
            />

            {/* Desktop-only hover submenu */}
            <div className="relative group hidden lg:block">
                <button
                    type="button"
                    className="flex items-center gap-2 rounded-xl px-3 py-2.5 text-sm font-medium text-slate-700 transition-all duration-200 hover:bg-white hover:text-slate-900"
                >
                    <Upload className="w-5 h-5" />
                    Data Entry
                </button>
                <div className="invisible absolute left-0 top-full z-50 mt-2 w-52 rounded-xl border border-slate-200 bg-white p-1.5 opacity-0 shadow-lg transition-all duration-200 group-hover:visible group-hover:opacity-100">
                    <div className="py-2">
                        <button
                            type="button"
                            onClick={() => handleFeature('upload')}
                            className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm font-medium text-slate-700 transition-colors hover:bg-slate-100 hover:text-slate-900"
                        >
                            <Upload className="w-4 h-4" />
                            CSV Upload
                        </button>
                        <button
                            type="button"
                            onClick={() => handleFeature('manual')}
                            className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm font-medium text-slate-700 transition-colors hover:bg-slate-100 hover:text-slate-900"
                        >
                            <FileText className="w-4 h-4" />
                            Manual Entry
                        </button>
                    </div>
                </div>
            </div>

            {/* Mobile-only collapsible Data Entry */}
            <div className="lg:hidden w-full">
                <button
                    type="button"
                    onClick={() => setDataEntryOpen(!dataEntryOpen)}
                    aria-expanded={dataEntryOpen}
                    className="flex w-full items-center gap-2 rounded-xl px-3 py-2.5 text-left text-sm font-medium text-slate-700 transition-colors hover:bg-white"
                >
                    <Upload className="w-5 h-5" />
                    Data Entry
                </button>
                {dataEntryOpen && (
                    <div className="mt-1 flex flex-col gap-1 pl-8">
                        <button
                            type="button"
                            onClick={() => handleFeature('upload')}
                            className="flex items-center gap-2 rounded-lg px-3 py-2 text-left text-sm font-medium text-slate-700 transition-colors hover:bg-white"
                        >
                            <Upload className="w-4 h-4" />
                            CSV Upload
                        </button>
                        <button
                            type="button"
                            onClick={() => handleFeature('manual')}
                            className="flex items-center gap-2 rounded-lg px-3 py-2 text-left text-sm font-medium text-slate-700 transition-colors hover:bg-white"
                        >
                            <FileText className="w-4 h-4" />
                            Manual Entry
                        </button>
                    </div>
                )}
            </div>

            <NavItem
                icon={<BarChart3 className="w-5 h-5" />}
                label="Analysis"
                href={navigationTargets.analysisHref}
                disabled={!navigationTargets.analysisHref}
                active={activeSection === 'dashboard'}
                onClick={closeMobile}
                fullWidth
            />

            <NavItem
                icon={<FileCheck className="w-5 h-5" />}
                label="Records"
                href={navigationTargets.recordsHref}
                disabled={!navigationTargets.recordsHref}
                active={activeSection === 'records'}
                onClick={closeMobile}
                fullWidth
            />

            <NavItem
                icon={<Database className="w-5 h-5" />}
                label="Export"
                href={navigationTargets.exportHref}
                disabled={!navigationTargets.exportHref}
                active={activeSection === 'export'}
                onClick={closeMobile}
                fullWidth
            />

            <NavItem
                icon={<History className="w-5 h-5" />}
                label="History"
                href="/history"
                active={activeSection === 'history'}
                onClick={closeMobile}
                fullWidth
            />

            <NavItem
                icon={<Settings className="w-5 h-5" />}
                label="Settings"
                href="/settings"
                active={activeSection === 'settings'}
                onClick={closeMobile}
                fullWidth
            />

            <button
                type="button"
                onClick={() => {
                    closeMobile();
                    handleLogout();
                }}
                className="flex w-full items-center gap-2 rounded-xl px-3 py-2.5 text-sm font-medium text-slate-700 transition-all duration-200 hover:bg-rose-50 hover:text-rose-700 lg:ml-1 lg:w-auto lg:border-l lg:border-slate-200 lg:pl-4"
            >
                <LogOut className="w-5 h-5" />
                <span className="font-medium">Logout</span>
            </button>
        </>
    );

    return (
        <nav className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/85 backdrop-blur supports-[backdrop-filter]:bg-white/75">
            <div className="mx-auto w-full max-w-[1400px] px-4 md:px-6">
                <div className="flex h-[74px] items-center gap-4">
                    <Link href="/" className="group flex flex-shrink-0 items-center gap-2.5">
                        <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-blue-600 to-indigo-600 shadow-sm transition-shadow group-hover:shadow-md">
                            <BarChart3 className="w-5 h-5 md:w-6 md:h-6 text-white" />
                        </span>
                        <span className="text-lg font-bold tracking-tight text-gray-900 md:text-xl">
                            Stock<span className="text-blue-600">Wise</span>
                        </span>
                    </Link>

                    <div className="ml-auto hidden items-center rounded-2xl border border-slate-200 bg-slate-50/80 p-1.5 shadow-[0_8px_24px_-18px_rgba(15,23,42,0.7)] lg:flex">
                        {navLinks}
                    </div>

                    <button
                        type="button"
                        aria-label={mobileOpen ? 'Close menu' : 'Open menu'}
                        aria-expanded={mobileOpen}
                        onClick={() => setMobileOpen(!mobileOpen)}
                        className="ml-auto rounded-xl p-2 text-slate-700 transition-colors hover:bg-slate-100 lg:hidden"
                    >
                        {mobileOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
                    </button>
                </div>

                {mobileOpen && (
                    <div className="border-t border-slate-200 py-3 lg:hidden">
                        <div className="flex flex-col gap-1 rounded-2xl bg-slate-50 p-2">
                            {navLinks}
                        </div>
                    </div>
                )}
            </div>
        </nav>
    );
}
