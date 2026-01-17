/**
 * HealChain Backend - Refund Detection Service
 * 
 * Detects when tasks are refunded on-chain and updates backend status to CANCELLED
 * Per BTP Report Chapter 4: When deadline passes and publisher exercises refund,
 * task status should be CANCELLED
 */

import { prisma } from "../config/database.config.js";
import { escrow } from "../contracts/escrow.js";
import { TaskStatus } from "@prisma/client";
import { logger } from "../utils/logger.js";

/**
 * Check on-chain task status and update backend if refunded
 * On-chain status FAILED (enum value 5) means task was refunded
 */
export async function checkRefundedTasks() {
  try {
    // Get all tasks that are not already CANCELLED or REWARDED
    // AND have a publishTx (meaning they were actually published on-chain)
    const activeTasks = await prisma.task.findMany({
      where: {
        status: {
          notIn: [TaskStatus.CANCELLED, TaskStatus.REWARDED]
        },
        publishTx: {
          not: null  // Only check tasks that were actually published on-chain
        }
      },
      select: {
        taskID: true,
        status: true,
        deadline: true,
        publishTx: true
      }
    });

    let updatedCount = 0;
    let skippedCount = 0;

    for (const task of activeTasks) {
      try {
        // Check on-chain task status
        const onChainTask = await escrow.tasks(task.taskID);
        
        // On-chain TaskStatus enum:
        // 0 = CREATED, 1 = LOCKED, 2 = PUBLISHED, 3 = AWAITING_REVEAL, 4 = COMPLETED, 5 = FAILED
        const onChainStatus = Number(onChainTask.status);
        const escrowBalance = await escrow.escrowBalance(task.taskID);
        const deadlinePassed = Number(task.deadline) <= Math.floor(Date.now() / 1000);
        
        // Distinguish between refund and reward distribution:
        // - Status 5 (FAILED) + escrowBalance = 0 → REFUND → CANCELLED
        // - Status 4 (COMPLETED) + escrowBalance = 0 → REWARD DISTRIBUTED → REWARDED (handled by checkRewardStatus)
        // - Status 1-3 (LOCKED/PUBLISHED/AWAITING_REVEAL) + escrowBalance = 0 + deadline passed → REFUND → CANCELLED
        
        const isFailed = onChainStatus === 5; // Explicitly marked as FAILED (refunded)
        const isCompleted = onChainStatus === 4; // Explicitly marked as COMPLETED (rewards distributed)
        const isRefunded = escrowBalance === 0n && deadlinePassed && !isCompleted;
        
        // Log for debugging (especially for COMMIT_CLOSED tasks)
        if (task.status === TaskStatus.COMMIT_CLOSED) {
          logger.info(`[RefundDetection] Checking COMMIT_CLOSED task ${task.taskID}: onChainStatus=${onChainStatus}, escrowBalance=${escrowBalance.toString()}, deadlinePassed=${deadlinePassed}, isFailed=${isFailed}, isCompleted=${isCompleted}, isRefunded=${isRefunded}`);
        }
        
        // Only update to CANCELLED if:
        // 1. Status is FAILED (explicit refund), OR
        // 2. Escrow is 0, deadline passed, and status is not COMPLETED (implicit refund)
        // Do NOT update if status is COMPLETED (rewards were distributed, handled by checkRewardStatus)
        if (isFailed || (isRefunded && !isCompleted)) {
          // Only update if not already CANCELLED or REWARDED
          if (task.status !== TaskStatus.CANCELLED && task.status !== TaskStatus.REWARDED) {
            await prisma.task.update({
              where: { taskID: task.taskID },
              data: { status: TaskStatus.CANCELLED }
            });
            updatedCount++;
            logger.info(`[RefundDetection] Updated task ${task.taskID}: ${task.status} → CANCELLED (refund detected: status=${onChainStatus}, escrowBalance=${escrowBalance.toString()})`);
          }
        }
      } catch (error: any) {
        // Check for specific "task doesn't exist" errors
        const isTaskNotFound = 
          error.code === "BAD_DATA" && 
          (error.message?.includes("could not decode") || error.value === "0x") ||
          error.message?.includes("revert") ||
          error.message?.includes("not found");
        
        if (isTaskNotFound) {
          // Task doesn't exist on-chain - this is normal for tasks that were created
          // but escrow transaction failed or was never confirmed
          skippedCount++;
          continue;
        }
        
        // Only log unexpected errors
        logger.warn(`[RefundDetection] Unexpected error checking task ${task.taskID}: ${error.message}`);
      }
    }

    if (skippedCount > 0) {
      logger.info(`[RefundDetection] Skipped ${skippedCount} tasks not found on-chain (expected for test/unpublished tasks)`);
    }

    return { updated: updatedCount > 0, count: updatedCount, skipped: skippedCount };
  } catch (error: any) {
    logger.error(`[RefundDetection] Error in checkRefundedTasks: ${error.message}`);
    throw error;
  }
}

/**
 * Check a specific task for refund status
 */
export async function checkTaskRefundStatus(taskID: string): Promise<{
  isRefunded: boolean;
  onChainStatus: number | null;
  escrowBalance: bigint;
  backendStatus: TaskStatus;
  existsOnChain: boolean;
  isCompleted: boolean;
  isFailed: boolean;
}> {
  try {
    const task = await prisma.task.findUnique({
      where: { taskID },
      select: { status: true, deadline: true, publishTx: true }
    });

    if (!task) {
      throw new Error(`Task ${taskID} not found`);
    }

    // Check if task exists on-chain
    let onChainStatus: number | null = null;
    let escrowBalance = 0n;
    let existsOnChain = false;

    try {
      const onChainTask = await escrow.tasks(taskID);
      onChainStatus = Number(onChainTask.status);
      escrowBalance = await escrow.escrowBalance(taskID);
      existsOnChain = true;
    } catch (error: any) {
      const isTaskNotFound = 
        error.code === "BAD_DATA" && 
        (error.message?.includes("could not decode") || error.value === "0x");
      
      if (isTaskNotFound) {
        // Task doesn't exist on-chain
        return {
          isRefunded: false,
          onChainStatus: null,
          escrowBalance: 0n,
          backendStatus: task.status,
          existsOnChain: false,
          isCompleted: false,
          isFailed: false
        };
      }
      throw error;
    }
    
    const deadlinePassed = Number(task.deadline) <= Math.floor(Date.now() / 1000);
    const isFailed = onChainStatus === 5; // FAILED status (explicit refund)
    const isCompleted = onChainStatus === 4; // COMPLETED status (rewards distributed)
    const isRefunded = escrowBalance === 0n && deadlinePassed && !isCompleted; // Implicit refund (escrow 0 but not completed)
    
    // Task is refunded if:
    // - Status is FAILED (explicit refund), OR
    // - Escrow is 0, deadline passed, and status is not COMPLETED
    const refunded = isFailed || isRefunded;

    return {
      isRefunded: refunded,
      onChainStatus,
      escrowBalance,
      backendStatus: task.status,
      existsOnChain: true,
      isCompleted: isCompleted,
      isFailed: isFailed
    };
  } catch (error: any) {
    throw new Error(`Failed to check refund status for task ${taskID}: ${error.message}`);
  }
}
