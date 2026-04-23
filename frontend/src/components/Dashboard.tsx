import React, { useState } from 'react';
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
    Settings,
    Menu,
    X,
    ChevronDown
} from 'lucide-react';

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
    const baseClasses = `flex items-center gap-2 px-3 lg:px-4 py-2 rounded-lg transition-colors text-sm lg:text-base ${fullWidth ? 'w-full' : ''}`;
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
    const [mobileOpen, setMobileOpen] = useState(false);
    const [dataEntryOpen, setDataEntryOpen] = useState(false);

    const closeMobile = () => {
        setMobileOpen(false);
        setDataEntryOpen(false);
    };

    return (
        <nav className="bg-white border-b border-gray-200 shadow-sm relative">
            <div className="max-w-7xl mx-auto px-4 md:px-8">
                <div className="flex items-center justify-between h-16">
                    {/* Logo/Brand */}
                    <div className="flex items-center gap-2">
                        <BarChart3 className="w-7 h-7 lg:w-8 lg:h-8 text-blue-600" />
                        <span className="text-lg lg:text-xl font-bold text-gray-900">StockWise</span>
                    </div>

                    {/* Desktop Navigation Items */}
                    <div className="hidden lg:flex items-center gap-1">
                        <NavItem
                            icon={<Home className="w-5 h-5" />}
                            label="Home"
                            href="/"
                            active={activeSection === 'home'}
                        />

                        {/* Data Entry Submenu (hover) */}
                        <div className="relative group">
                            <button className="flex items-center gap-2 px-3 lg:px-4 py-2 text-gray-700 hover:bg-gray-100 hover:text-gray-900 rounded-lg transition-colors font-medium text-sm lg:text-base">
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

                        <NavItem
                            icon={<BarChart3 className="w-5 h-5" />}
                            label="Analysis"
                            href={currentAnalysisId ? `/dashboard/${currentAnalysisId}` : undefined}
                            disabled={!currentAnalysisId}
                            active={activeSection === 'dashboard'}
                        />

                        <NavItem
                            icon={<FileCheck className="w-5 h-5" />}
                            label="Records"
                            href={currentAnalysisId ? `/records/${currentAnalysisId}` : undefined}
                            disabled={!currentAnalysisId}
                            active={activeSection === 'records'}
                        />

                        <NavItem
                            icon={<TrendingUp className="w-5 h-5" />}
                            label="Simulation"
                            href={currentAnalysisId ? `/dashboard/${currentAnalysisId}` : undefined}
                            disabled={!currentAnalysisId}
                            active={activeSection === 'simulation'}
                        />

                        <NavItem
                            icon={<MessageSquare className="w-5 h-5" />}
                            label="Explanations"
                            href={currentAnalysisId ? `/dashboard/${currentAnalysisId}` : undefined}
                            disabled={!currentAnalysisId}
                            active={activeSection === 'explanation'}
                        />

                        <NavItem
                            icon={<Database className="w-5 h-5" />}
                            label="Export"
                            disabled={true}
                            active={activeSection === 'export'}
                        />

                        <NavItem
                            icon={<Settings className="w-5 h-5" />}
                            label="Settings"
                            href="/settings"
                            active={activeSection === 'settings'}
                        />
                    </div>

                    {/* Mobile hamburger toggle */}
                    <button
                        type="button"
                        aria-label={mobileOpen ? 'Close menu' : 'Open menu'}
                        aria-expanded={mobileOpen}
                        onClick={() => setMobileOpen(!mobileOpen)}
                        className="lg:hidden inline-flex items-center justify-center p-2 rounded-lg text-gray-700 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                        {mobileOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
                    </button>
                </div>
            </div>

            {/* Mobile menu panel */}
            {mobileOpen && (
                <div className="lg:hidden border-t border-gray-200 bg-white shadow-lg">
                    <div className="px-4 py-3 space-y-1 max-h-[calc(100vh-4rem)] overflow-y-auto">
                        <NavItem
                            icon={<Home className="w-5 h-5" />}
                            label="Home"
                            href="/"
                            active={activeSection === 'home'}
                            fullWidth
                        />

                        {/* Data Entry collapsible */}
                        <div>
                            <button
                                type="button"
                                onClick={() => setDataEntryOpen(!dataEntryOpen)}
                                className="flex items-center justify-between w-full gap-2 px-3 py-2 text-gray-700 hover:bg-gray-100 hover:text-gray-900 rounded-lg transition-colors font-medium text-sm"
                            >
                                <span className="flex items-center gap-2">
                                    <Upload className="w-5 h-5" />
                                    Data Entry
                                </span>
                                <ChevronDown className={`w-4 h-4 transition-transform ${dataEntryOpen ? 'rotate-180' : ''}`} />
                            </button>
                            {dataEntryOpen && (
                                <div className="pl-6 mt-1 space-y-1">
                                    <button
                                        onClick={() => { onFeatureSelect('upload'); closeMobile(); }}
                                        className="flex items-center gap-2 w-full px-3 py-2 text-left text-gray-700 hover:bg-gray-100 hover:text-gray-900 rounded-lg text-sm"
                                    >
                                        <Upload className="w-4 h-4" />
                                        CSV Upload
                                    </button>
                                    <button
                                        onClick={() => { onFeatureSelect('manual'); closeMobile(); }}
                                        className="flex items-center gap-2 w-full px-3 py-2 text-left text-gray-700 hover:bg-gray-100 hover:text-gray-900 rounded-lg text-sm"
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
                            href={currentAnalysisId ? `/dashboard/${currentAnalysisId}` : undefined}
                            disabled={!currentAnalysisId}
                            active={activeSection === 'dashboard'}
                            fullWidth
                        />

                        <NavItem
                            icon={<FileCheck className="w-5 h-5" />}
                            label="Records"
                            href={currentAnalysisId ? `/records/${currentAnalysisId}` : undefined}
                            disabled={!currentAnalysisId}
                            active={activeSection === 'records'}
                            fullWidth
                        />

                        <NavItem
                            icon={<TrendingUp className="w-5 h-5" />}
                            label="Simulation"
                            href={currentAnalysisId ? `/dashboard/${currentAnalysisId}` : undefined}
                            disabled={!currentAnalysisId}
                            active={activeSection === 'simulation'}
                            fullWidth
                        />

                        <NavItem
                            icon={<MessageSquare className="w-5 h-5" />}
                            label="Explanations"
                            href={currentAnalysisId ? `/dashboard/${currentAnalysisId}` : undefined}
                            disabled={!currentAnalysisId}
                            active={activeSection === 'explanation'}
                            fullWidth
                        />

                        <NavItem
                            icon={<Database className="w-5 h-5" />}
                            label="Export"
                            disabled={true}
                            active={activeSection === 'export'}
                            fullWidth
                        />

                        <NavItem
                            icon={<Settings className="w-5 h-5" />}
                            label="Settings"
                            href="/settings"
                            active={activeSection === 'settings'}
                            fullWidth
                        />
                    </div>
                </div>
            )}
        </nav>
    );
}
