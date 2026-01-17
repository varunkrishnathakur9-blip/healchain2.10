/**
 * HealChain Frontend - Backend API Client
 * Client for interacting with the HealChain backend API
 */

import axios, { AxiosInstance } from 'axios';
import { BACKEND_API_URL } from './web3';

// Create axios instance
const api: AxiosInstance = axios.create({
  baseURL: BACKEND_API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request interceptor for debugging
api.interceptors.request.use(
  (config) => {
    console.log('[API] Request:', {
      method: config.method?.toUpperCase(),
      url: config.url,
      baseURL: config.baseURL,
      fullURL: `${config.baseURL}${config.url}`,
      data: config.data ? { ...config.data, signature: config.data.signature ? '[REDACTED]' : undefined } : undefined,
    });
    return config;
  },
  (error) => {
    console.error('[API] Request error:', error);
    return Promise.reject(error);
  }
);

// Add response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    console.log('[API] Response:', {
      status: response.status,
      url: response.config.url,
      data: response.data,
    });
    return response;
  },
  (error) => {
    // Build error log object with only defined values
    const errorInfo: Record<string, any> = {};
    
    // Check for different error types
    if (error?.message) {
      errorInfo.message = error.message;
    }
    
    if (error?.response) {
      // Server responded with error status
      if (error.response.status) {
        errorInfo.status = error.response.status;
      }
      if (error.response.data) {
        // Safely serialize response data (handle circular references)
        try {
          errorInfo.data = JSON.parse(JSON.stringify(error.response.data));
        } catch {
          // If serialization fails, just include a string representation
          errorInfo.data = String(error.response.data);
        }
      }
    } else if (error?.request) {
      // Request made but no response (network error)
      errorInfo.type = 'Network Error';
      errorInfo.message = error.message || 'Could not reach backend server';
    } else {
      // Something else happened (setup error, etc.)
      errorInfo.type = 'Request Error';
      if (error?.message) {
        errorInfo.message = error.message;
      }
    }
    
    if (error?.config?.url) {
      errorInfo.url = error.config.url;
    }
    
    // Only log if there's actual information
    if (Object.keys(errorInfo).length > 0) {
      console.error('[API] Response error:', errorInfo);
    } else {
      // Fallback: log the error object itself
      console.error('[API] Response error (unknown format):', error);
    }
    if (error.response) {
      // Server responded with error status
      // Preserve the full error object so we can access response.data
      const message = error.response.data?.error || error.response.data?.message || error.message || 'An unknown error occurred';
      
      // Add error details to errorInfo for better debugging
      if (error.response.data) {
        errorInfo.data = error.response.data;
      }
      const enhancedError = new Error(String(message));
      // Attach the original error response for detailed error handling
      (enhancedError as any).response = error.response;
      (enhancedError as any).responseData = error.response.data;
      // For 403 (Unauthorized), don't log as console error - it's expected behavior
      if (error.response.status === 403) {
        // Silently reject - let the component handle the error gracefully
        return Promise.reject(enhancedError);
      }
      return Promise.reject(enhancedError);
    } else if (error.request) {
      // Request made but no response
      return Promise.reject(new Error('Network error: Could not reach backend server'));
    } else {
      // Something else happened
      return Promise.reject(error);
    }
  }
);

// Types
export interface Task {
  taskID: string;
  publisher: string;
  deadline: string | number;
  status: string; // CREATED, OPEN, COMMIT_CLOSED, REVEAL_OPEN, REVEAL_CLOSED, AGGREGATING, VERIFIED, REWARDED, CANCELLED
  createdAt?: string;
  updatedAt?: string;
  dataset?: string;
  commitHash?: string;
  rewardAmount?: number;
  accuracyRequired?: number;
  escrowBalance?: string;
  escrowContractAddress?: string; // Contract address where escrow is locked (for reading from correct contract)
  publishTx?: string; // Escrow transaction hash
  minMiners?: number; // Minimum miners required for PoS aggregator selection
  maxMiners?: number; // Maximum miners allowed for PoS aggregator selection
  _count?: {
    miners?: number;
    gradients?: number;
  };
}

export interface Miner {
  id: string;
  taskID: string;
  address: string;
  registeredAt: string;
  status: string;
}

export interface Block {
  id: string;
  taskID: string;
  round: number;
  modelHash: string;
  modelLink?: string;
  accuracy: number;
  publishedAt?: string;
  blockHash?: string;
}

export interface Reward {
  id: string;
  taskID: string;
  minerID: string;
  score: number;
  totalScore: number;
  sharePercent: number;
  amountETH: number;
  status: string;
  txHash?: string;
}

// Task API
export const taskAPI = {
  // M1: Create task (escrow must be locked on-chain first)
  // IMPORTANT: commitHash and nonceTP must be provided for Algorithm 1 compliance
  // escrowTxHash is required to verify escrow is locked before creating task
  create: async (data: {
    taskID: string;
    publisher: string;
    address: string; // Required by auth middleware
    accuracy: string;
    deadline: string;
    commitHash: string; // Commit hash generated by frontend (keccak256(accuracy || nonce))
    nonceTP: string;    // 32-byte nonce as hex string (64 hex characters)
    escrowTxHash: string; // Transaction hash of escrow lock - required for verification
    dataset?: string;   // D: Dataset requirements (Algorithm 1)
    initialModelLink?: string;  // L: Initial model link (Algorithm 1) - optional
    minMiners?: number;  // Minimum miners required for PoS aggregator selection
    maxMiners?: number;  // Maximum miners allowed for PoS aggregator selection
    message: string;
    signature: string;
  }) => {
    const response = await api.post('/tasks/create', data);
    return response.data;
  },

  // Get open tasks (for FL client polling)
  getOpen: async (): Promise<Task[]> => {
    const response = await api.get('/tasks/open');
    return response.data;
  },

  // Get task by ID
  getById: async (taskID: string): Promise<Task> => {
    const response = await api.get(`/tasks/${taskID}`);
    return response.data;
  },

  // Get all tasks with filters
  getAll: async (filters?: {
    status?: string;
    publisher?: string;
    limit?: number;
    offset?: number;
  }): Promise<Task[]> => {
    const response = await api.get('/tasks', { params: filters });
    return response.data;
  },

  // Update task status (admin)
  updateStatus: async (taskID: string, status: string, signature: string) => {
    const response = await api.put(`/tasks/${taskID}/status`, {
      status,
      signature,
    });
    return response.data;
  },

  // Check deadlines
  checkDeadlines: async () => {
    const response = await api.post('/tasks/check-deadlines');
    return response.data;
  },
};

// Miner API
export const minerAPI = {
  // M2: Register miner
  // Algorithm 2: Requires miner proof (IPFS link or system proof) and public key (recommended)
  register: async (data: {
    taskID: string;
    address: string;
    proof: string;  // Algorithm 2: Miner proof (IPFS link or system proof) - required
    publicKey?: string;  // Algorithm 2: Miner public key (EC point: x_hex,y_hex) - recommended for key derivation
    message: string;
    signature: string;
  }) => {
    const response = await api.post('/miners/register', data);
    return response.data;
  },

  // Get all tasks a miner is registered for
  getMyTasks: async (address: string) => {
    try {
      const response = await api.get(`/miners/my-tasks`, {
        params: { address }
      });
      return response.data;
    } catch (error: any) {
      console.error('getMyTasks API error:', error);
      throw error;
    }
  },

  // Trigger FL client training for a task
  startTraining: async (address: string, taskID: string, message: string, signature: string) => {
    const response = await api.post(`/miners/${address}/tasks/${taskID}/start-training`, {
      address, // Required by auth middleware
      message,
      signature
    });
    return response.data;
  },

  // Get training status for a miner on a task
  getTrainingStatus: async (address: string, taskID: string) => {
    const response = await api.get(`/miners/${address}/tasks/${taskID}/training-status`);
    return response.data;
  },

  // M3: Submit gradient to aggregator (manual trigger)
  submitGradient: async (address: string, taskID: string, message: string, signature: string) => {
    const response = await api.post(`/miners/${address}/tasks/${taskID}/submit-gradient`, {
      address, // Required by auth middleware
      message,
      signature
    });
    return response.data;
  },
};

// Aggregator API
export const aggregatorAPI = {
  // M3: Submit encrypted gradient update
  submitUpdate: async (data: {
    taskID: string;
    minerAddress: string;
    scoreCommit: string;
    encryptedHash: string;
    message: string;
    signature: string;
  }) => {
    const response = await api.post('/aggregator/submit-update', data);
    return response.data;
  },

  // M4: Submit candidate block
  submitCandidate: async (data: {
    taskID: string;
    modelHash: string;
    accuracy: string;
  }) => {
    const response = await api.post('/aggregator/submit-candidate', data);
    return response.data;
  },

  // M6: Publish block on-chain
  publish: async (data: {
    taskID: string;
    modelHash: string;
    accuracy: string;
    miners: string[];
  }) => {
    const response = await api.post('/aggregator/publish', data);
    return response.data;
  },

  // Trigger aggregator for a task
  startAggregation: async (taskID: string, aggregatorAddress: string, message: string, signature: string) => {
    const response = await api.post(`/aggregator/${taskID}/start`, {
      address: aggregatorAddress, // Required for wallet authentication middleware
      aggregatorAddress: aggregatorAddress, // Also include as fallback for backend
      message,
      signature
    });
    return response.data;
  },

  // Get aggregator status for a task
  getAggregatorStatus: async (taskID: string) => {
    const response = await api.get(`/aggregator/${taskID}/status`);
    return response.data;
  },

  // Algorithm 2: Get skFE key derivation status (requires aggregator authentication)
  getKeyStatus: async (taskID: string, address: string, message: string, signature: string) => {
    const response = await api.post(`/aggregator/${taskID}/key-status`, {
      address,
      message,
      signature
    });
    return response.data;
  },

  // Algorithm 3: Get all miner submissions with ciphertext (requires aggregator authentication)
  getSubmissions: async (taskID: string, address: string, message: string, signature: string) => {
    const response = await api.post(`/aggregator/${taskID}/submissions`, {
      address,
      message,
      signature
    });
    return response.data;
  },
};

// Reward API
export const rewardAPI = {
  // M7: Distribute rewards
  distribute: async (data: {
    taskID: string;
    miners: string[];
  }) => {
    const response = await api.post('/rewards/distribute', data);
    return response.data;
  },
};

export default api;

