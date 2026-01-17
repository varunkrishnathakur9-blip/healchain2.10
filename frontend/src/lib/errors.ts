/**
 * HealChain Frontend - Error Handling Utilities
 * Provides specific error messages for different failure modes
 */

export class HealChainError extends Error {
  constructor(
    message: string,
    public code: string,
    public userMessage: string,
    public originalError?: unknown
  ) {
    super(message);
    this.name = 'HealChainError';
  }
}

// Error codes
export const ERROR_CODES = {
  // Wallet errors
  WALLET_NOT_CONNECTED: 'WALLET_NOT_CONNECTED',
  WALLET_CONNECTION_FAILED: 'WALLET_CONNECTION_FAILED',
  WALLET_SIGNATURE_REJECTED: 'WALLET_SIGNATURE_REJECTED',
  WALLET_WRONG_NETWORK: 'WALLET_WRONG_NETWORK',
  
  // Transaction errors
  TRANSACTION_REJECTED: 'TRANSACTION_REJECTED',
  TRANSACTION_FAILED: 'TRANSACTION_FAILED',
  TRANSACTION_TIMEOUT: 'TRANSACTION_TIMEOUT',
  INSUFFICIENT_BALANCE: 'INSUFFICIENT_BALANCE',
  
  // Contract errors
  CONTRACT_NOT_DEPLOYED: 'CONTRACT_NOT_DEPLOYED',
  CONTRACT_CALL_FAILED: 'CONTRACT_CALL_FAILED',
  INVALID_CONTRACT_ADDRESS: 'INVALID_CONTRACT_ADDRESS',
  
  // Task errors
  TASK_NOT_FOUND: 'TASK_NOT_FOUND',
  TASK_ALREADY_EXISTS: 'TASK_ALREADY_EXISTS',
  TASK_INVALID_STATUS: 'TASK_INVALID_STATUS',
  TASK_DEADLINE_PASSED: 'TASK_DEADLINE_PASSED',
  
  // Miner errors
  MINER_ALREADY_REGISTERED: 'MINER_ALREADY_REGISTERED',
  MINER_NOT_REGISTERED: 'MINER_NOT_REGISTERED',
  
  // Reveal errors
  COMMIT_MISMATCH: 'COMMIT_MISMATCH',
  ALREADY_REVEALED: 'ALREADY_REVEALED',
  PUBLISHER_NOT_REVEALED: 'PUBLISHER_NOT_REVEALED',
  
  // Backend errors
  BACKEND_CONNECTION_FAILED: 'BACKEND_CONNECTION_FAILED',
  BACKEND_AUTH_FAILED: 'BACKEND_AUTH_FAILED',
  BACKEND_VALIDATION_ERROR: 'BACKEND_VALIDATION_ERROR',
  
  // Network errors
  NETWORK_ERROR: 'NETWORK_ERROR',
  RPC_ERROR: 'RPC_ERROR',
} as const;

// Error message mapping
const ERROR_MESSAGES: Record<string, string> = {
  [ERROR_CODES.WALLET_NOT_CONNECTED]: 'Please connect your wallet to continue',
  [ERROR_CODES.WALLET_CONNECTION_FAILED]: 'Failed to connect wallet. Please try again or check if your wallet is unlocked',
  [ERROR_CODES.WALLET_SIGNATURE_REJECTED]: 'Message signature was rejected. Please try again',
  [ERROR_CODES.WALLET_WRONG_NETWORK]: 'Please switch to the correct network (localhost or Sepolia)',
  
  [ERROR_CODES.TRANSACTION_REJECTED]: 'Transaction was rejected. Please try again',
  [ERROR_CODES.TRANSACTION_FAILED]: 'Transaction failed. Please check your balance and try again',
  [ERROR_CODES.TRANSACTION_TIMEOUT]: 'Transaction timed out. Please check the network and try again',
  [ERROR_CODES.INSUFFICIENT_BALANCE]: 'Insufficient balance. Please add more ETH to your wallet',
  
  [ERROR_CODES.CONTRACT_NOT_DEPLOYED]: 'Smart contract not deployed on this network',
  [ERROR_CODES.CONTRACT_CALL_FAILED]: 'Failed to call smart contract. Please check the network connection',
  [ERROR_CODES.INVALID_CONTRACT_ADDRESS]: 'Invalid contract address. Please check your configuration',
  
  [ERROR_CODES.TASK_NOT_FOUND]: 'Task not found. It may have been deleted or the ID is incorrect',
  [ERROR_CODES.TASK_ALREADY_EXISTS]: 'Task with this ID already exists. Please use a different ID',
  [ERROR_CODES.TASK_INVALID_STATUS]: 'Task is not in the correct status for this operation',
  [ERROR_CODES.TASK_DEADLINE_PASSED]: 'Task deadline has passed. Cannot perform this operation',
  
  [ERROR_CODES.MINER_ALREADY_REGISTERED]: 'You are already registered as a miner for this task',
  [ERROR_CODES.MINER_NOT_REGISTERED]: 'You are not registered as a miner for this task',
  
  [ERROR_CODES.COMMIT_MISMATCH]: 'Score and nonce do not match the commit hash. Please verify your values',
  [ERROR_CODES.ALREADY_REVEALED]: 'You have already revealed your score for this task',
  [ERROR_CODES.PUBLISHER_NOT_REVEALED]: 'Publisher must reveal accuracy before miners can reveal scores',
  
  [ERROR_CODES.BACKEND_CONNECTION_FAILED]: 'Failed to connect to backend. Please check if the server is running',
  [ERROR_CODES.BACKEND_AUTH_FAILED]: 'Authentication failed. Please reconnect your wallet',
  [ERROR_CODES.BACKEND_VALIDATION_ERROR]: 'Invalid input. Please check your form data',
  
  [ERROR_CODES.NETWORK_ERROR]: 'Network error. Please check your internet connection',
  [ERROR_CODES.RPC_ERROR]: 'Blockchain RPC error. Please try again later',
};

/**
 * Parse error and return user-friendly message
 */
export function parseError(error: unknown): { code: string; message: string; originalError?: unknown } {
  // If it's already a HealChainError, return it
  if (error instanceof HealChainError) {
    return {
      code: error.code,
      message: error.userMessage,
      originalError: error.originalError,
    };
  }

  // If it's a standard Error, try to match it
  if (error instanceof Error) {
    const message = error.message.toLowerCase();
    
    // Wallet errors
    if (message.includes('user rejected') || message.includes('user denied')) {
      return {
        code: ERROR_CODES.WALLET_SIGNATURE_REJECTED,
        message: ERROR_MESSAGES[ERROR_CODES.WALLET_SIGNATURE_REJECTED],
        originalError: error,
      };
    }
    
    if (message.includes('insufficient funds') || message.includes('insufficient balance')) {
      return {
        code: ERROR_CODES.INSUFFICIENT_BALANCE,
        message: ERROR_MESSAGES[ERROR_CODES.INSUFFICIENT_BALANCE],
        originalError: error,
      };
    }
    
    if (message.includes('network') || message.includes('connection')) {
      return {
        code: ERROR_CODES.NETWORK_ERROR,
        message: ERROR_MESSAGES[ERROR_CODES.NETWORK_ERROR],
        originalError: error,
      };
    }
    
    if (message.includes('timeout')) {
      return {
        code: ERROR_CODES.TRANSACTION_TIMEOUT,
        message: ERROR_MESSAGES[ERROR_CODES.TRANSACTION_TIMEOUT],
        originalError: error,
      };
    }
    
    // Contract errors - check for specific revert reasons
    if (message.includes('task exists') || message.includes('taskid') || message.includes('Task exists')) {
      return {
        code: ERROR_CODES.TASK_ALREADY_EXISTS,
        message: ERROR_MESSAGES[ERROR_CODES.TASK_ALREADY_EXISTS],
        originalError: error,
      };
    }
    
    if (message.includes('invalid deadline') || message.includes('deadline')) {
      return {
        code: ERROR_CODES.TASK_DEADLINE_PASSED,
        message: 'Deadline must be in the future. Please select a future date and time.',
        originalError: error,
      };
    }
    
    if (message.includes('reward must be') || message.includes('value') && message.includes('0')) {
      return {
        code: ERROR_CODES.TRANSACTION_FAILED,
        message: 'Reward amount must be greater than 0. Please enter a valid reward amount.',
        originalError: error,
      };
    }
    
    // Contract errors
    if (message.includes('contract') || message.includes('call exception') || message.includes('revert') || message.includes('execution reverted')) {
      // Try to extract revert reason
      const revertMatch = message.match(/revert\s+(.+?)(?:\s|$)/i) || message.match(/execution reverted:\s*(.+?)(?:\s|$)/i);
      if (revertMatch && revertMatch[1]) {
        return {
          code: ERROR_CODES.CONTRACT_CALL_FAILED,
          message: `Transaction failed: ${revertMatch[1]}`,
          originalError: error,
        };
      }
      return {
        code: ERROR_CODES.CONTRACT_CALL_FAILED,
        message: ERROR_MESSAGES[ERROR_CODES.CONTRACT_CALL_FAILED],
        originalError: error,
      };
    }
    
    // RPC errors - check error object for revert reason
    if (message.includes('internal json-rpc error') || message.includes('rpc error') || message.includes('simulation failed')) {
      // Try to extract revert reason from error object (check multiple possible locations)
      const errorObj = error as any;
      
      // Check various possible locations for revert reason (prioritize details field)
      let revertReason = errorObj?.revertReason ||
                        errorObj?.details ||
                        errorObj?.cause?.details ||
                        errorObj?.data?.message || 
                        errorObj?.data?.reason ||
                        errorObj?.reason || 
                        errorObj?.shortMessage || 
                        errorObj?.cause?.reason ||
                        errorObj?.cause?.data?.message ||
                        errorObj?.cause?.data?.reason ||
                        (errorObj?.data && typeof errorObj.data === 'string' ? errorObj.data : null);
      
      // Extract revert reason from "revert X" format (e.g., "revert Task exists")
      if (revertReason && typeof revertReason === 'string') {
        // Try multiple patterns to capture the full revert reason
        let extractedReason = null;
        
        // Pattern 1: "VM Exception while processing transaction: revert Task exists\nVersion..."
        let match = revertReason.match(/VM Exception while processing transaction:\s*revert\s+([^\n]+)/i);
        if (match && match[1]) {
          extractedReason = match[1].trim();
        } else {
          // Pattern 2: "revert Task exists\nVersion..." or "revert Task exists"
          match = revertReason.match(/revert\s+([^\n]+)/i);
          if (match && match[1]) {
            extractedReason = match[1].trim();
          } else {
            // Pattern 3: Just use the reason as-is if it doesn't contain "revert"
            extractedReason = revertReason.trim();
          }
        }
        
        if (extractedReason) {
          revertReason = extractedReason;
        }
      }
      
      // Also check if error has a nested structure
      let nestedReason = null;
      try {
        if (errorObj?.data && typeof errorObj.data === 'object') {
          nestedReason = JSON.stringify(errorObj.data);
        }
        if (errorObj?.cause && typeof errorObj.cause === 'object') {
          nestedReason = nestedReason || JSON.stringify(errorObj.cause);
        }
      } catch {
        // Ignore JSON stringify errors
      }
      
      // Combine all possible revert reasons
      const allReasons = [revertReason, nestedReason].filter(Boolean).join(' ');
      
      if (revertReason) {
        const reasonLower = revertReason.toLowerCase();
        
        // Check for specific revert reasons
        if (reasonLower.includes('task exists') || reasonLower.includes('taskid')) {
          return {
            code: ERROR_CODES.TASK_ALREADY_EXISTS,
            message: ERROR_MESSAGES[ERROR_CODES.TASK_ALREADY_EXISTS],
            originalError: error,
          };
        }
        if (reasonLower.includes('invalid deadline') || (reasonLower.includes('deadline') && reasonLower.includes('past'))) {
          return {
            code: ERROR_CODES.TASK_DEADLINE_PASSED,
            message: 'Deadline must be in the future. Please select a future date and time.',
            originalError: error,
          };
        }
        if (reasonLower.includes('reward must be') || (reasonLower.includes('value') && reasonLower.includes('0'))) {
          return {
            code: ERROR_CODES.TRANSACTION_FAILED,
            message: 'Reward amount must be greater than 0. Please enter a valid reward amount.',
            originalError: error,
          };
        }
        
        // Try to extract a clean revert reason message (remove "revert" prefix if present)
        let cleanReason = revertReason;
        if (cleanReason.includes('revert')) {
          const revertMatch = cleanReason.match(/revert\s+(.+?)(?:\s|$|\.)/i);
          if (revertMatch && revertMatch[1]) {
            cleanReason = revertMatch[1].trim();
          }
        }
        
        return {
          code: ERROR_CODES.RPC_ERROR,
          message: `Transaction failed: ${cleanReason}. Please check your inputs and try again.`,
          originalError: error,
        };
      }
      
      // Log the full error for debugging
      if (process.env.NEXT_PUBLIC_DEBUG === 'true') {
        console.error('RPC Error details:', {
          error,
          errorObj,
          keys: Object.keys(errorObj || {}),
          data: errorObj?.data,
          cause: errorObj?.cause,
        });
      }
      
      return {
        code: ERROR_CODES.RPC_ERROR,
        message: 'Transaction failed on blockchain. Common causes: 1) Task ID already exists, 2) Deadline is in the past, 3) Reward is 0, 4) Insufficient gas. Please check your inputs and try again.',
        originalError: error,
      };
    }
    
    // Backend errors
    if (message.includes('fetch') || message.includes('network')) {
      return {
        code: ERROR_CODES.BACKEND_CONNECTION_FAILED,
        message: ERROR_MESSAGES[ERROR_CODES.BACKEND_CONNECTION_FAILED],
        originalError: error,
      };
    }
    
    // Default: return the error message
    return {
      code: 'UNKNOWN_ERROR',
      message: error.message || 'An unexpected error occurred',
      originalError: error,
    };
  }

  // Unknown error type
  return {
    code: 'UNKNOWN_ERROR',
    message: 'An unexpected error occurred. Please try again',
    originalError: error,
  };
}

/**
 * Create a HealChainError from an error code
 */
export function createError(code: string, originalError?: unknown): HealChainError {
  const userMessage = ERROR_MESSAGES[code] || 'An error occurred';
  return new HealChainError(userMessage, code, userMessage, originalError);
}

