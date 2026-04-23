import React from 'react';
import { Button, Card } from '@/components/common';
import Link from 'next/link';

export default function NotFound() {

    return (
        <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
            <Card className="p-8 text-center max-w-md">
                <h1 className="text-4xl font-bold text-gray-900 mb-2">404</h1>
                <p className="text-gray-600 mb-6">Page not found</p>
                <Link href="/">
                    <Button variant="primary">Back to Home</Button>
                </Link>
            </Card>
        </div>
    );
}
