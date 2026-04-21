import React from 'react';
import Link from 'next/link';
import {
    Home,
    Upload,
    FileText,
    BarChart3,
    FileCheck,
    TrendingUp,
    MessageSquare,
    Database,
    Settings
} from 'lucide-react';
import { Button } from '@/components/common';

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
    activeSection?: string;
}

export function NavigationBar({ onFeatureSelect, currentAnalysisId, activeSection }: NavigationBarProps) {
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
                            href={currentAnalysisId ? `/dashboard/${currentAnalysisId}` : undefined}
                            disabled={!currentAnalysisId}
                            active={activeSection === 'dashboard'}
                        />

                        {/* Records Management */}
                        <NavItem
                            icon={<FileCheck className="w-5 h-5" />}
                            label="Records"
                            href={currentAnalysisId ? `/records/${currentAnalysisId}` : undefined}
                            disabled={!currentAnalysisId}
                            active={activeSection === 'records'}
                        />

                        {/* Simulation */}
                        <NavItem
                            icon={<TrendingUp className="w-5 h-5" />}
                            label="Simulation"
                            href={currentAnalysisId ? `/dashboard/${currentAnalysisId}` : undefined}
                            disabled={!currentAnalysisId}
                            active={activeSection === 'simulation'}
                        />

                        {/* AI Explanations */}
                        <NavItem
                            icon={<MessageSquare className="w-5 h-5" />}
                            label="Explanations"
                            href={currentAnalysisId ? `/dashboard/${currentAnalysisId}` : undefined}
                            disabled={!currentAnalysisId}
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
                    </div>
                </div>
            </div>
        </nav>
    );
}