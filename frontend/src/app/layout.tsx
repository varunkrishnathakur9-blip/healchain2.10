/**
 * HealChain Frontend - Root Layout
 * Sets up Web3 providers (wagmi + RainbowKit) and global layout
 */

import type { Metadata } from 'next';
import { Geist, Geist_Mono } from 'next/font/google';
import '@/styles/globals.css';
import { Providers } from './providers';
import Nav from '@/components/Nav';
import { ErrorBoundary } from '@/components/ErrorBoundary';

const geistSans = Geist({
  variable: '--font-geist-sans',
  subsets: ['latin'],
});

const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
});

export const metadata: Metadata = {
  title: 'HealChain - Privacy-Preserving Federated Learning',
  description: 'Blockchain-enabled federated learning framework with privacy guarantees',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              // Suppress WebSocket errors IMMEDIATELY (before anything else loads)
              (function() {
                'use strict';
                
                // Override console.error to filter WebSocket errors
                const originalConsoleError = console.error;
                console.error = function(...args) {
                  const msg = args.join(' ');
                  if (msg.includes('Connection interrupted') || 
                      msg.includes('subscribe') || 
                      msg.includes('WebSocket') ||
                      msg.includes('EventEmitter') ||
                      msg.includes('onClose')) {
                    return; // Suppress
                  }
                  originalConsoleError.apply(console, args);
                };
                
                // Catch unhandled rejections with highest priority
                const handleRejection = function(event) {
                  const error = event.reason;
                  const msg = error?.message || error?.toString() || String(error) || '';
                  if (msg.includes('Connection interrupted') || 
                      msg.includes('subscribe') || 
                      msg.includes('WebSocket') ||
                      msg.includes('EventEmitter') ||
                      msg.includes('onClose')) {
                    event.preventDefault();
                    event.stopPropagation();
                    event.stopImmediatePropagation();
                    return false;
                  }
                };
                window.addEventListener('unhandledrejection', handleRejection, { capture: true, passive: false });
                
                // Catch synchronous errors with highest priority
                const handleError = function(event) {
                  const msg = event.message || event.error?.message || String(event.error) || '';
                  if (msg.includes('Connection interrupted') || 
                      msg.includes('subscribe') || 
                      msg.includes('WebSocket') ||
                      msg.includes('EventEmitter') ||
                      msg.includes('onClose')) {
                    event.preventDefault();
                    event.stopPropagation();
                    event.stopImmediatePropagation();
                    return false;
                  }
                };
                window.addEventListener('error', handleError, { capture: true, passive: false });
                
                // Also intercept Next.js error overlay if possible
                if (typeof window !== 'undefined' && (window as any).__NEXT_DATA__) {
                  const originalError = (window as any).__NEXT_DATA__;
                  // Try to suppress Next.js error reporting for these errors
                }
              })();
            `,
          }}
        />
      </head>
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
        <ErrorBoundary>
          <Providers>
            <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
              <Nav />
              <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {children}
              </main>
            </div>
          </Providers>
        </ErrorBoundary>
      </body>
    </html>
  );
}
