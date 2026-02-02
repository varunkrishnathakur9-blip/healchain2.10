/**
 * HealChain Backend - Aggregator Orchestration Service
 * 
 * Orchestrates aggregator operations by communicating with local aggregator service
 * Option 1: Backend as Orchestrator
 */

import { prisma } from "../config/database.config.js";
import { TaskStatus } from "@prisma/client";
import axios from "axios";
import { NotFoundError } from "../utils/errors.js";

export interface AggregatorStatus {
  taskID: string;
  status: "IDLE" | "WAITING_SUBMISSIONS" | "AGGREGATING" | "VERIFYING" | "PUBLISHING" | "COMPLETED" | "FAILED";
  progress?: number; // 0-100
  submissionCount?: number;
  requiredSubmissions?: number;
  error?: string;
  completedAt?: Date;
}

/**
 * Trigger aggregator for a specific task
 * 
 * This communicates with the local aggregator service running on the aggregator's machine
 */
export async function triggerAggregation(
  taskID: string,
  aggregatorAddress: string
): Promise<{ success: boolean; message: string }> {
  // Validate task exists and aggregator is selected
  const task = await prisma.task.findUnique({
    where: { taskID },
    include: {
      miners: {
        where: { proofVerified: true }
      },
      gradients: true
    }
  });

  if (!task) {
    throw new Error(`Task ${taskID} not found`);
  }

  if (task.aggregatorAddress?.toLowerCase() !== aggregatorAddress.toLowerCase()) {
    throw new Error(`Address ${aggregatorAddress} is not the selected aggregator for task ${taskID}`);
  }

  // Validate task is in correct status - use type assertion to avoid redundant check lint error
  if (![TaskStatus.OPEN, TaskStatus.AGGREGATING].includes(task.status as any)) {
    throw new Error(`Task ${taskID} is not ready for aggregation. Current status: ${task.status}`);
  }

  // Check if aggregation already completed
  if (task.status as any === "VERIFIED" || task.status as any === "REWARDED") {
    return {
      success: false,
      message: "Aggregation already completed for this task"
    };
  }

  // Get aggregator service URL from environment or use default
  const aggregatorServiceUrl = process.env.AGGREGATOR_SERVICE_URL || "http://localhost:5002";

  try {
    // Trigger aggregation on local aggregator service
    const response = await axios.post(
      `${aggregatorServiceUrl}/api/aggregate`,
      {
        taskID,
        aggregatorAddress: aggregatorAddress.toLowerCase()
      },
      {
        timeout: 5000, // 5 second timeout for connection check
        validateStatus: (status) => status < 500 // Don't throw on 4xx
      }
    );

    if (response.status === 200) {
      // Update task status to AGGREGATING
      await prisma.task.update({
        where: { taskID },
        data: { status: TaskStatus.AGGREGATING }
      });

      return {
        success: true,
        message: "Aggregation started successfully"
      };
    } else {
      return {
        success: false,
        message: response.data?.error || "Failed to start aggregation"
      };
    }
  } catch (error: any) {
    // If aggregator service is not running, return helpful error
    if (error.code === "ECONNREFUSED" || error.code === "ETIMEDOUT") {
      return {
        success: false,
        message: "Aggregator service is not running. Please start the aggregator service on your machine."
      };
    }

    throw new Error(`Failed to trigger aggregation: ${error.message}`);
  }
}

/**
 * Get aggregator status for a task
 */
export async function getAggregatorStatus(
  taskID: string
): Promise<AggregatorStatus> {
  const task = await prisma.task.findUnique({
    where: { taskID },
    include: {
      miners: {
        where: { proofVerified: true }
      },
      gradients: true,
      block: true
    }
  });

  if (!task) {
    throw new NotFoundError(`Task ${taskID} not found`);
  }

  // If block exists, aggregation is completed
  if (task.block) {
    return {
      taskID,
      status: "COMPLETED",
      completedAt: task.updatedAt
    };
  }

  // Check with aggregator service for current status
  const aggregatorServiceUrl = process.env.AGGREGATOR_SERVICE_URL || "http://localhost:5002";

  try {
    const response = await axios.get(
      `${aggregatorServiceUrl}/api/status/${taskID}`,
      {
        timeout: 3000
      }
    );

    // Map aggregator service response to AggregatorStatus format
    const aggregatorData = response.data;
    console.log(`[getAggregatorStatus] Aggregator service response for task ${taskID}:`, aggregatorData);

    if (aggregatorData.running) {
      return {
        taskID,
        status: "AGGREGATING",
        submissionCount: task.gradients.length,
        requiredSubmissions: task.miners.length
      };
    } else {
      // Aggregator not running, check database state
      const submissionCount = task.gradients.length;
      const requiredSubmissions = task.miners.length;

      console.log(`[getAggregatorStatus] Aggregator not running. Submissions: ${submissionCount}/${requiredSubmissions}`);

      if (submissionCount === 0) {
        return {
          taskID,
          status: "WAITING_SUBMISSIONS",
          submissionCount: 0,
          requiredSubmissions
        };
      } else if (submissionCount < requiredSubmissions) {
        return {
          taskID,
          status: "WAITING_SUBMISSIONS",
          submissionCount,
          requiredSubmissions
        };
      } else {
        return {
          taskID,
          status: "IDLE",
          submissionCount,
          requiredSubmissions
        };
      }
    }
  } catch (error: any) {
    console.error(`[getAggregatorStatus] Error fetching status for task ${taskID}:`, error.message);
    if (error.response) {
      console.error(`[getAggregatorStatus] Error response data:`, error.response.data);
      console.error(`[getAggregatorStatus] Error response status:`, error.response.status);
    }

    // If service not available, infer status from database
    if (error.code === "ECONNREFUSED" || error.code === "ETIMEDOUT") {
      const submissionCount = task.gradients.length;
      const requiredSubmissions = task.miners.length;

      if (submissionCount === 0) {
        return {
          taskID,
          status: "WAITING_SUBMISSIONS",
          submissionCount: 0,
          requiredSubmissions
        };
      } else if (submissionCount < requiredSubmissions) {
        return {
          taskID,
          status: "WAITING_SUBMISSIONS",
          submissionCount,
          requiredSubmissions
        };
      } else {
        return {
          taskID,
          status: "IDLE",
          submissionCount,
          requiredSubmissions
        };
      }
    }

    throw new Error(`Failed to get aggregator status: ${error.message}`);
  }
}

