import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import {
    Home,
    Upload,
    FileText,
    BarChart3,
    FileCheck,
    TrendingUp,
    MessageSquare,
    Database,
    Settings,
    LogOut
} from 'lucide-react';
import { Button } from '@/components/common';
import {
    getLatestAnalysisId,
    hydrateLatestAnalysisId,
    saveLatestAnalysisId,
    subscribeToLatestAnalysisId,
} from '@/lib/analysisSession';
import { buildAnalysisNavigationTargets } from '@/lib/navigationTargets';
import { apiClient } from '@/services/api';
import { useAuth } from '@/lib/auth';

interface NavItemProps {
    icon: React.ReactNode;
    label: string;
    href?: string;
    onClick?: () => void;
    disabled?: boolean;
    active?: boolean;
}

function NavItem({ icon, label, href, onClick, disabled, active }: NavItemProps) {
    const baseClasses = "flex items-center gap-2 px-4 py-2 rounded-lg transition-colors";
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
            <Link href={href} className={`${baseClasses} ${stateClasses}`}>
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

    return (
        <nav className="bg-white border-b border-gray-200 shadow-sm">
            <div className="max-w-7xl mx-auto px-4 md:px-8">
                <div className="flex items-center justify-between h-16">
                    {/* Logo/Brand */}
                    <div className="flex items-center gap-2">
                        <BarChart3 className="w-8 h-8 text-blue-600" />
                        <span className="text-xl font-bold text-gray-900">StockWise</span>
                    </div>

                    {/* Navigation Items */}
                    <div className="flex items-center gap-1">
                        {/* Home/Data Entry */}
                        <NavItem
                            icon={<Home className="w-5 h-5" />}
                            label="Home"
                            href="/"
                            active={activeSection === 'home'}
                        />

                        {/* Data Entry Submenu */}
                        <div className="relative group">
                            <button className="flex items-center gap-2 px-4 py-2 text-gray-700 hover:bg-gray-100 hover:text-gray-900 rounded-lg transition-colors font-medium">
                                <Upload className="w-5 h-5" />
                                Data Entry
                            </button>
                            <div className="absolute top-full left-0 mt-1 w-48 bg-white border border-gray-200 rounded-lg shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50">
                                <div className="py-2">
                                    <button
                                        onClick={() => onFeatureSelect('upload')}
                                        className="flex items-center gap-2 w-full px-4 py-2 text-left text-gray-700 hover:bg-gray-100 hover:text-gray-900"
                                    >
                                        <Upload className="w-4 h-4" />
                                        CSV Upload
                                    </button>
                                    <button
                                        onClick={() => onFeatureSelect('manual')}
                                        className="flex items-center gap-2 w-full px-4 py-2 text-left text-gray-700 hover:bg-gray-100 hover:text-gray-900"
                                    >
                                        <FileText className="w-4 h-4" />
                                        Manual Entry
                                    </button>
                                </div>
                            </div>
                        </div>

                        {/* Analysis Dashboard */}
                        <NavItem
                            icon={<BarChart3 className="w-5 h-5" />}
                            label="Analysis"
                            href={navigationTargets.analysisHref}
                            disabled={!navigationTargets.analysisHref}
                            active={activeSection === 'dashboard'}
                        />

                        {/* Records Management */}
                        <NavItem
                            icon={<FileCheck className="w-5 h-5" />}
                            label="Records"
                            href={navigationTargets.recordsHref}
                            disabled={!navigationTargets.recordsHref}
                            active={activeSection === 'records'}
                        />

                        {/* Simulation */}
                        <NavItem
                            icon={<TrendingUp className="w-5 h-5" />}
                            label="Simulation"
                            href={navigationTargets.simulationHref}
                            disabled={!navigationTargets.simulationHref}
                            active={activeSection === 'simulation'}
                        />

                        {/* AI Explanations */}
                        <NavItem
                            icon={<MessageSquare className="w-5 h-5" />}
                            label="Explanations"
                            href={navigationTargets.explanationHref}
                            disabled={!navigationTargets.explanationHref}
                            active={activeSection === 'explanation'}
                        />

                        {/* Data Export */}
                        <NavItem
                            icon={<Database className="w-5 h-5" />}
                            label="Export"
                            disabled={true}
                            active={activeSection === 'export'}
                        />

                        {/* Settings */}
                        <NavItem
                            icon={<Settings className="w-5 h-5" />}
                            label="Settings"
                            href="/settings"
                            active={activeSection === 'settings'}
                        />

                        {/* Logout */}
                        <button
                            onClick={handleLogout}
                            className="flex items-center gap-2 px-4 py-2 text-gray-700 hover:bg-gray-100 hover:text-gray-900 rounded-lg transition-colors font-medium"
                        >
                            <LogOut className="w-5 h-5" />
                            Logout
                        </button>
                    </div>
                </div>
            </div>
        </nav>
    );
}
