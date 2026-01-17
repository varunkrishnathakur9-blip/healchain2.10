/**
 * Date formatting utilities that work consistently on server and client
 */

/**
 * Format a Unix timestamp (seconds) to a consistent date string
 * Uses a fixed format to avoid locale/timezone differences between server and client
 */
export function formatDate(timestamp: number | string | bigint): string {
  const date = new Date(Number(timestamp) * 1000);
  
  // Use a consistent format that works the same on server and client
  const year = date.getUTCFullYear();
  const month = String(date.getUTCMonth() + 1).padStart(2, '0');
  const day = String(date.getUTCDate()).padStart(2, '0');
  
  return `${month}/${day}/${year}`;
}

/**
 * Format a Unix timestamp (seconds) or ISO string to a more readable format
 */
export function formatDateLong(timestamp: number | string | bigint | Date | undefined): string {
  if (!timestamp) {
    return 'Invalid date';
  }
  
  let date: Date;
  
  // Handle different input types
  if (timestamp instanceof Date) {
    date = timestamp;
  } else if (typeof timestamp === 'string') {
    // Check if it's an ISO string or a Unix timestamp string
    if (timestamp.includes('T') || timestamp.includes('-')) {
      // ISO string format
      date = new Date(timestamp);
    } else {
      // Unix timestamp in seconds (string)
      date = new Date(Number(timestamp) * 1000);
    }
  } else {
    // Number or bigint - assume Unix timestamp in seconds
    date = new Date(Number(timestamp) * 1000);
  }
  
  // Validate date
  if (isNaN(date.getTime())) {
    return 'Invalid date';
  }
  
  const year = date.getUTCFullYear();
  const month = String(date.getUTCMonth() + 1).padStart(2, '0');
  const day = String(date.getUTCDate()).padStart(2, '0');
  const hours = String(date.getUTCHours()).padStart(2, '0');
  const minutes = String(date.getUTCMinutes()).padStart(2, '0');
  
  return `${month}/${day}/${year} ${hours}:${minutes} UTC`;
}

