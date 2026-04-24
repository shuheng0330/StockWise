import React from 'react';
import Head from 'next/head';
import '../styles/globals.css';
import type { AppProps } from 'next/app';
import { Toaster } from 'react-hot-toast';
import { AuthProvider } from '@/lib/auth';

function App({ Component, pageProps }: AppProps) {
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
