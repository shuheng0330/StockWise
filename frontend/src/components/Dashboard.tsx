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
    MessageSquare,
    Settings,
    TrendingUp,
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
    const baseClasses = `flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${fullWidth ? 'w-full' : ''}`.trim();
    const stateClasses = disabled
        ? "text-gray-400 cursor-not-allowed"
        : active
            ? "bg-blue-100 text-blue-700"
            : "text-gray-700 hover:bg-gray-100 hover:text-gray-900";

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
        <button onClick={onClick} className={`${baseClasses} ${stateClasses}`}>
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
        onFeatureSelect(feature);
        closeMobile();
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
                <button className="flex items-center gap-2 px-4 py-2 text-gray-700 hover:bg-gray-100 hover:text-gray-900 rounded-lg transition-colors font-medium">
                    <Upload className="w-5 h-5" />
                    Data Entry
                </button>
                <div className="absolute top-full left-0 mt-1 w-48 bg-white border border-gray-200 rounded-lg shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50">
                    <div className="py-2">
                        <button
                            onClick={() => handleFeature('upload')}
                            className="flex items-center gap-2 w-full px-4 py-2 text-left text-gray-700 hover:bg-gray-100 hover:text-gray-900"
                        >
                            <Upload className="w-4 h-4" />
                            CSV Upload
                        </button>
                        <button
                            onClick={() => handleFeature('manual')}
                            className="flex items-center gap-2 w-full px-4 py-2 text-left text-gray-700 hover:bg-gray-100 hover:text-gray-900"
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
                    onClick={() => setDataEntryOpen(!dataEntryOpen)}
                    className="flex items-center gap-2 w-full px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg font-medium"
                >
                    <Upload className="w-5 h-5" />
                    Data Entry
                </button>
                {dataEntryOpen && (
                    <div className="pl-8 flex flex-col">
                        <button
                            onClick={() => handleFeature('upload')}
                            className="flex items-center gap-2 px-4 py-2 text-left text-gray-700 hover:bg-gray-100 rounded-lg"
                        >
                            <Upload className="w-4 h-4" />
                            CSV Upload
                        </button>
                        <button
                            onClick={() => handleFeature('manual')}
                            className="flex items-center gap-2 px-4 py-2 text-left text-gray-700 hover:bg-gray-100 rounded-lg"
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
                icon={<TrendingUp className="w-5 h-5" />}
                label="Simulation"
                href={navigationTargets.simulationHref}
                disabled={!navigationTargets.simulationHref}
                active={activeSection === 'simulation'}
                onClick={closeMobile}
                fullWidth
            />

            <NavItem
                icon={<MessageSquare className="w-5 h-5" />}
                label="Explanations"
                href={navigationTargets.explanationHref}
                disabled={!navigationTargets.explanationHref}
                active={activeSection === 'explanation'}
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
                onClick={() => {
                    closeMobile();
                    handleLogout();
                }}
                className="flex items-center gap-2 px-4 py-2 rounded-lg transition-colors text-gray-700 hover:bg-gray-100 hover:text-gray-900 font-medium"
            >
                <LogOut className="w-5 h-5" />
                <span className="font-medium">Logout</span>
            </button>
        </>
    );

    return (
        <nav className="bg-white border-b border-gray-200 shadow-sm">
            <div className="max-w-7xl mx-auto px-4 md:px-8">
                <div className="flex items-center justify-between h-16">
                    {/* Logo/Brand */}
                    <Link href="/" className="flex items-center gap-2">
                        <BarChart3 className="w-7 h-7 md:w-8 md:h-8 text-blue-600" />
                        <span className="text-lg md:text-xl font-bold text-gray-900">StockWise</span>
                    </Link>

                    {/* Desktop Navigation */}
                    <div className="hidden lg:flex items-center gap-1">
                        {navLinks}
                    </div>

                    {/* Mobile menu toggle */}
                    <button
                        type="button"
                        aria-label={mobileOpen ? 'Close menu' : 'Open menu'}
                        onClick={() => setMobileOpen(!mobileOpen)}
                        className="lg:hidden p-2 rounded-lg text-gray-700 hover:bg-gray-100"
                    >
                        {mobileOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
                    </button>
                </div>

                {/* Mobile Menu */}
                {mobileOpen && (
                    <div className="lg:hidden py-3 border-t border-gray-200">
                        <div className="flex flex-col gap-1">
                            {navLinks}
                        </div>
                    </div>
                )}
            </div>
        </nav>
    );
}
