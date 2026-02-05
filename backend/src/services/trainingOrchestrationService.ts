/**
 * HealChain Backend - Training Orchestration Service
 * 
 * Orchestrates FL client training by communicating with local FL client service
 * Option 1: Backend as Orchestrator
 * 
 * The FL client service fetches task details from backend when triggered,
 * so .env only needs static miner-specific config (MINER_ADDRESS, keys, etc.)
 */

import { prisma } from "../config/database.config.js";
import { TaskStatus } from "@prisma/client";
import axios from "axios";
import { getTaskById } from "./taskService.js";

export interface TrainingStatus {
  taskID: string;
  minerAddress: string;
  status: "IDLE" | "TRAINING" | "COMPLETED" | "FAILED";
  progress?: number; // 0-100
  error?: string;
  submittedAt?: string; // ISO string or Unix timestamp in seconds (string)
  submitted?: boolean;
  submissionStatus?: string;
  submissionError?: string;
}

/**
 * Trigger FL client training for a miner on a specific task
 * 
 * This communicates with the local FL client service running on the miner's machine
 */
export async function triggerTraining(
  taskID: string,
  minerAddress: string
): Promise<{ success: boolean; message: string; suggestion?: string }> {
  // Validate miner is registered for this task
  const miner = await prisma.miner.findUnique({
    where: {
      taskID_address: {
        taskID,
        address: minerAddress.toLowerCase()
      }
    },
    include: {
      task: true
    }
  });

  if (!miner) {
    return {
      success: false,
      message: `Miner ${minerAddress} is not registered for task ${taskID}. Please register as a miner first.`
    };
  }

  if (!miner.proofVerified) {
    return {
      success: false,
      message: `Miner proof not verified for task ${taskID}. Please complete miner registration and proof verification first.`
    };
  }

  // Validate task is in correct status
  if (miner.task.status !== TaskStatus.OPEN) {
    return {
      success: false,
      message: `Task ${taskID} is not open for training. Current status: ${miner.task.status}. Task must be OPEN to start training.`
    };
  }

  // Check if training already in progress or completed
  const existingGradient = await prisma.gradient.findFirst({
    where: {
      taskID,
      minerAddress: minerAddress.toLowerCase()
    }
  });

  if (existingGradient) {
    return {
      success: false,
      message: "Training already completed for this task. You have already submitted a gradient."
    };
  }

  // Use stored FL client URL, fallback to localhost if not provided
  const flClientServiceUrl = (miner as any)?.flClientUrl || process.env.FL_CLIENT_SERVICE_URL || "http://localhost:5001";

  console.log(`[triggerTraining] Using FL client URL for miner ${minerAddress}: ${flClientServiceUrl}`);

  try {
    // Fetch public keys for NDD-FE encryption from backend
    let tpPublicKey = "";
    let aggregatorPublicKey = "";
    try {
      // Use the backend's own URL (localhost:3000 or from env)
      const backendUrl = process.env.BACKEND_URL || `http://localhost:${process.env.PORT || 3000}`;
      const publicKeysResponse = await axios.get(
        `${backendUrl}/tasks/${taskID}/public-keys`,
        { timeout: 3000 }
      );
      if (publicKeysResponse.data) {
        tpPublicKey = publicKeysResponse.data.tpPublicKey || "";
        aggregatorPublicKey = publicKeysResponse.data.aggregatorPublicKey || "";
      }
    } catch (keyError: any) {
      console.warn(`[triggerTraining] Could not fetch public keys for task ${taskID}:`, keyError.message);
      // Continue without keys - FL client service will try to get them from task details
    }

    // Trigger training on FL client service (local or remote)
    // Pass all necessary configuration so FL client service doesn't need .env updates
    const response = await axios.post(
      `${flClientServiceUrl}/api/train`,
      {
        taskID,  // FL client service fetches task details from backend using this
        minerAddress: minerAddress.toLowerCase(),
        // Pass configuration that would normally be in .env
        config: {
          minerAddress: minerAddress.toLowerCase(),
          backendUrl: process.env.BACKEND_URL || `http://localhost:${process.env.PORT || 3000}`,
          tpPublicKey: tpPublicKey,
          aggregatorPublicKey: aggregatorPublicKey,
          // Note: MINER_PRIVATE_KEY is not passed for security - must be in .env
        }
      },
      {
        timeout: 5000, // 5 second timeout for connection check
        validateStatus: (status) => status < 500 // Don't throw on 4xx
      }
    );

    if (response.status === 200) {
      return {
        success: true,
        message: "Training started successfully"
      };
    } else {
      // FL client service returned an error
      const errorMessage = response.data?.error || response.data?.message || `FL client service returned status ${response.status}`;
      return {
        success: false,
        message: `Failed to start training: ${errorMessage}`
      };
    }
  } catch (error: any) {
    // If FL client service is not running, return helpful error
    if (error.code === "ECONNREFUSED" || error.code === "ETIMEDOUT") {
      return {
        success: false,
        message: "FL client service is not running. Please start the FL client service on your machine (default: http://localhost:5001)."
      };
    }

    // Handle 404 from FL client service
    if (error.response?.status === 404) {
      return {
        success: false,
        message: "FL client service endpoint not found. Please ensure the FL client service is running and has the /api/train endpoint."
      };
    }

    // For other errors, return a user-friendly message instead of throwing
    return {
      success: false,
      message: `Failed to trigger training: ${error.message || 'Unknown error'}`
    };
  }
}

/**
 * Get training status for a miner on a task
 */
export async function getTrainingStatus(
  taskID: string,
  minerAddress: string
): Promise<TrainingStatus> {
  // Check if gradient submission exists (with error handling for DB connection issues)
  let gradient = null;
  try {
    gradient = await prisma.gradient.findFirst({
      where: {
        taskID,
        minerAddress: minerAddress.toLowerCase()
      },
      orderBy: {
        id: "desc"
      }
    });
  } catch (dbError: any) {
    // Handle database connection errors gracefully
    if (dbError.code === 'P1001' || dbError.message?.includes('Can\'t reach database server')) {
      console.warn(`[getTrainingStatus] Database connection error: ${dbError.message}`);
      console.warn(`[getTrainingStatus] Continuing with FL client service check instead`);
      // Continue to check FL client service instead of failing completely
    } else {
      // For other database errors, log and continue
      console.error(`[getTrainingStatus] Database error:`, dbError);
      // Continue to check FL client service
    }
  }

  if (gradient) {
    // Convert createdAt to Unix timestamp (seconds) for frontend formatDateLong function
    // Prisma returns createdAt as a Date object
    let submittedAtTimestamp: number;
    try {
      if (gradient.createdAt) {
        const createdAtDate = gradient.createdAt instanceof Date
          ? gradient.createdAt
          : new Date(gradient.createdAt);
        // Validate the date is valid
        if (isNaN(createdAtDate.getTime())) {
          console.warn(`[getTrainingStatus] Invalid createdAt date for task ${taskID}, using current time`);
          submittedAtTimestamp = Math.floor(Date.now() / 1000);
        } else {
          submittedAtTimestamp = Math.floor(createdAtDate.getTime() / 1000);
        }
      } else {
        submittedAtTimestamp = Math.floor(Date.now() / 1000);
      }
    } catch (e) {
      // Fallback to current time if date parsing fails
      console.warn(`[getTrainingStatus] Error parsing createdAt for task ${taskID}:`, e);
      submittedAtTimestamp = Math.floor(Date.now() / 1000);
    }

    return {
      taskID,
      minerAddress: minerAddress.toLowerCase(),
      status: "COMPLETED",
      submitted: true,
      submittedAt: submittedAtTimestamp.toString(), // Unix timestamp in seconds as string
      submissionStatus: "SUBMITTED"
    };
  }

  // Get miner's FL client service URL from database (for distributed status check)
  const miner = await prisma.miner.findUnique({
    where: {
      taskID_address: {
        taskID,
        address: minerAddress.toLowerCase()
      }
    }
  });

  // Use stored FL client URL, fallback to localhost if not provided
  const flClientServiceUrl = (miner as any)?.flClientUrl || process.env.FL_CLIENT_SERVICE_URL || "http://localhost:5001";

  try {
    const response = await axios.get(
      `${flClientServiceUrl}/api/train/status`,
      {
        params: {
          taskID,
          minerAddress: minerAddress.toLowerCase()
        }
        // Timeout removed as per user request to prevent "timeout exceeded" errors
      }
    );

    return response.data as TrainingStatus;
  } catch (error: any) {
    // If service not available (404, connection refused, timeout), return IDLE status
    // This is expected when FL client service is not running
    if (error.code === "ECONNREFUSED" || error.code === "ETIMEDOUT" || error.response?.status === 404) {
      return {
        taskID,
        minerAddress: minerAddress.toLowerCase(),
        status: "IDLE"
      };
    }

    // Only throw error for unexpected errors (not 404)
    throw new Error(`Failed to get training status: ${error.message}`);
  }
}

/**
 * Trigger gradient submission to aggregator (M3)
 * This calls the FL client service to submit the gradient
 * @param walletAuth - Optional wallet authentication for backend API calls from FL client service
 */
export async function triggerSubmission(
  taskID: string,
  minerAddress: string,
  walletAuth?: { address: string; message: string; signature: string }
): Promise<{ success: boolean; message: string; suggestion?: string }> {
  // Validate miner is registered for this task
  const miner = await prisma.miner.findUnique({
    where: {
      taskID_address: {
        taskID,
        address: minerAddress.toLowerCase()
      }
    }
  });

  if (!miner) {
    return {
      success: false,
      message: `Miner ${minerAddress} is not registered for task ${taskID}.`
    };
  }

  // Check if gradient already submitted
  const existingGradient = await prisma.gradient.findFirst({
    where: {
      taskID,
      minerAddress: minerAddress.toLowerCase()
    }
  });

  if (existingGradient) {
    return {
      success: true,
      message: "Gradient already submitted to aggregator."
    };
  }

  // Use stored FL client URL, fallback to localhost if not provided
  const flClientServiceUrl = (miner as any)?.flClientUrl || process.env.FL_CLIENT_SERVICE_URL || "http://localhost:5001";

  try {
    // Pass wallet auth if provided so FL client service can authenticate with backend
    const requestBody: any = {
      taskID,
      minerAddress: minerAddress.toLowerCase()
    };

    if (walletAuth) {
      requestBody.walletAuth = walletAuth;
    }

    const response = await axios.post(
      `${flClientServiceUrl}/api/submit`,
      requestBody,
      {
        // Timeout removed as per user request to handle large sparse payloads without being cut off
        validateStatus: (status) => status < 500
      }
    );

    if (response.status === 200 && response.data.success) {
      return {
        success: true,
        message: response.data.message || "Gradient submitted successfully"
      };
    } else {
      const errorMessage = response.data?.error || response.data?.message || `Submission returned status ${response.status}`;
      return {
        success: false,
        message: errorMessage
      };
    }
  } catch (error: any) {
    if (error.code === "ECONNREFUSED" || error.code === "ETIMEDOUT") {
      return {
        success: false,
        message: "FL client service is not running. Please start the FL client service on your machine."
      };
    }

    if (error.response?.status === 404) {
      // Extract error message and suggestion from FL client service
      const errorData = error.response?.data || {};
      const errorMessage = errorData.error || errorData.message || "";
      const suggestion = errorData.suggestion || "";

      // Check if it's a missing payload with old training data
      if (errorMessage.includes("submission payload is missing") || errorMessage.includes("payload may have been lost") || errorData.action === "RETRAIN") {
        return {
          success: false,
          message: errorMessage || "Training payload not found. Please retrain the task to generate a new payload.",
          suggestion: suggestion || "Click 'Retry Training' on the training dashboard, then click 'Submit Gradient' after training completes."
        };
      }

      // Use suggestion from FL client service if available
      if (suggestion) {
        return {
          success: false,
          message: errorMessage || "No training payload found. Please complete training first.",
          suggestion: suggestion
        };
      }

      return {
        success: false,
        message: errorMessage || "No training payload found. Please complete training first."
      };
    }

    // Handle 400 errors (bad request) - might be missing wallet auth or other validation errors
    if (error.response?.status === 400) {
      const errorMessage = error.response?.data?.error || error.response?.data?.message || error.message;
      return {
        success: false,
        message: errorMessage || "Submission failed due to invalid request. Please check your wallet connection and try again."
      };
    }

    return {
      success: false,
      message: `Failed to submit gradient: ${error.message || 'Unknown error'}`
    };
  }
}
