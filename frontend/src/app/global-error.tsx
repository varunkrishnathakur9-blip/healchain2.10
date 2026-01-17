/**
 * HealChain Frontend - Global Error Handler
 * Catches errors at the root level and suppresses WebSocket errors
 */

'use client';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const errorMessage = error.message || error.toString();
  const isConnectionError =
    errorMessage.includes('Connection interrupted') ||
    errorMessage.includes('subscribe') ||
    errorMessage.includes('WebSocket') ||
    errorMessage.includes('EventEmitter') ||
    errorMessage.includes('onClose');

  // Automatically reset for connection errors
  if (isConnectionError) {
    // Suppress the error completely
    if (typeof window !== 'undefined') {
      // Clear any error state
      window.dispatchEvent(new Event('error-cleared'));
      // Reset after a brief delay to avoid render issues
      setTimeout(() => {
        try {
          reset();
        } catch (e) {
          // Ignore reset errors
        }
      }, 50);
    }
    // Return minimal UI or null to suppress error
    return (
      <html>
        <body>
          <div style={{ display: 'none' }}>Error suppressed</div>
        </body>
      </html>
    );
  }

  // For other errors, show error UI
  return (
    <html>
      <body>
        <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
          <div className="text-center max-w-md">
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
              Something went wrong
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mb-6">{error.message}</p>
            <button
              onClick={reset}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Try again
            </button>
          </div>
        </div>
      </body>
    </html>
  );
}

