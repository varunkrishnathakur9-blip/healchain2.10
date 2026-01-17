/**
 * HealChain Backend - Task Status Scheduler
 * 
 * Automatically updates task statuses based on deadlines and consensus
 * Runs periodically to check and update task statuses
 */

import { prisma } from "../config/database.config.js";
import { TaskStatus } from "@prisma/client";
import { checkTaskDeadlines, checkConsensusAndUpdate, checkRevealDeadlines, checkRewardStatus } from "./taskService.js";
import { checkRefundedTasks } from "./refundDetectionService.js";
import { logger } from "../utils/logger.js";

const SCHEDULE_INTERVAL_MS = 60000; // Check every 60 seconds
const REVEAL_DEADLINE_OFFSET_SECONDS = 7 * 24 * 60 * 60; // 7 days after main deadline

let schedulerInterval: NodeJS.Timeout | null = null;

/**
 * Start the task status scheduler
 */
export function startTaskScheduler() {
  if (schedulerInterval) {
    logger.warn("Task scheduler already running");
    return;
  }

  logger.info("Starting task status scheduler (interval: 60s)");
  
  // Run immediately on startup (with delay to let server fully start)
  setTimeout(() => {
    runSchedulerCycle().catch(err => {
      logger.error(`Initial scheduler cycle failed: ${err.message}`);
    });
  }, 5000); // Wait 5 seconds after startup

  // Then run periodically
  schedulerInterval = setInterval(() => {
    runSchedulerCycle().catch(err => {
      logger.error(`Scheduler cycle failed: ${err.message}`);
    });
  }, SCHEDULE_INTERVAL_MS);
}

/**
 * Stop the task status scheduler
 */
export function stopTaskScheduler() {
  if (schedulerInterval) {
    clearInterval(schedulerInterval);
    schedulerInterval = null;
    logger.info("Task scheduler stopped");
  }
}

/**
 * Run one complete scheduler cycle
 */
async function runSchedulerCycle() {
  try {
    // 1. Check deadlines (CREATED → OPEN, OPEN → COMMIT_CLOSED)
    await checkTaskDeadlines();
    
    // 2. Check reveal deadlines (REVEAL_OPEN → REVEAL_CLOSED)
    await checkRevealDeadlines();
    
    // 3. Check consensus for REVEAL_OPEN tasks (REVEAL_OPEN → VERIFIED)
    await checkConsensusAndUpdate();
    
    // 4. Check reward status for VERIFIED tasks (VERIFIED → REWARDED)
    await checkRewardStatus();
    
    // 5. Check for refunded tasks (any status → CANCELLED)
    await checkRefundedTasks();
    
  } catch (error: any) {
    logger.error(`Scheduler cycle error: ${error.message}`, { stack: error.stack });
  }
}

/**
 * Get scheduler status
 */
export function getSchedulerStatus() {
  return {
    running: schedulerInterval !== null,
    interval: SCHEDULE_INTERVAL_MS,
    revealDeadlineOffset: REVEAL_DEADLINE_OFFSET_SECONDS
  };
}
