import React, { useEffect } from 'react';
import Head from 'next/head';
import '../styles/globals.css';
import type { AppProps } from 'next/app';
import { Toaster } from 'react-hot-toast';
import { AuthProvider } from '@/lib/auth';

const DENSITY_KEY = 'stockwise-table-density';
const DENSITY_VALUES = ['comfortable', 'compact', 'spacious'] as const;

function App({ Component, pageProps }: AppProps) {
    useEffect(() => {
        try {
            const stored = localStorage.getItem(DENSITY_KEY);
            const density = (DENSITY_VALUES as readonly string[]).includes(stored ?? '')
                ? (stored as typeof DENSITY_VALUES[number])
                : 'comfortable';
            document.documentElement.classList.add(`density-${density}`);
        } catch {
            // ignore storage failures (private mode, etc.)
        }
    }, []);

    return (
        <AuthProvider>
            <Head>
                <meta name="viewport" content="width=device-width, initial-scale=1.0" />
                <meta name="description" content="StockWise - Intelligent Inventory Analysis" />
            </Head>
            <Component {...pageProps} />
            <Toaster position="top-right" />
        </AuthProvider>
    );
}

export default App;
