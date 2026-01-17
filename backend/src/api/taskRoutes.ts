import { Router } from "express";
import { createTask, getOpenTasks, getTaskById, getAllTasks, updateTaskStatus, checkTaskDeadlines } from "../services/taskService.js";
import { requireFields } from "../middleware/validation.js";
import { requireWalletAuth } from "../middleware/auth.js";

const router = Router();

/**
 * M1: Publish task (escrow must be locked on-chain first)
 * 
 * IMPORTANT: 
 * - commitHash and nonceTP must be provided by frontend to ensure Algorithm 1 compliance
 * - escrowTxHash is required to verify escrow is locked before creating task
 * - Task will only be created with status OPEN if escrow is verified as locked
 */
router.post(
  "/create",
  requireFields(["taskID", "publisher", "accuracy", "deadline", "commitHash", "nonceTP", "escrowTxHash", "message", "signature"]),
  requireWalletAuth,
  async (req, res, next) => {
    try {
      const { taskID, publisher, accuracy, deadline, commitHash, nonceTP, escrowTxHash, dataset, initialModelLink, minMiners, maxMiners } = req.body;

      // Validate commitHash and nonceTP are provided
      if (!commitHash || !nonceTP) {
        return res.status(400).json({ 
          error: "commitHash and nonceTP are required for Algorithm 1 compliance" 
        });
      }

      // Validate escrowTxHash is provided
      if (!escrowTxHash) {
        return res.status(400).json({ 
          error: "escrowTxHash is required - escrow must be locked on-chain before creating task" 
        });
      }

      // Validate nonceTP is 64 hex characters (32 bytes)
      if (!/^[0-9a-fA-F]{64}$/.test(nonceTP)) {
        return res.status(400).json({ 
          error: "nonceTP must be 64 hex characters (32 bytes)" 
        });
      }

      const result = await createTask(
        taskID,
        publisher,
        BigInt(accuracy),
        BigInt(deadline),
        commitHash,
        nonceTP,
        escrowTxHash,   // Escrow transaction hash for verification
        dataset,        // D: Dataset requirements (Algorithm 1)
        initialModelLink,  // L: Initial model link (Algorithm 1)
        minMiners ? parseInt(minMiners.toString()) : undefined,  // Min miners (optional, defaults to 3)
        maxMiners ? parseInt(maxMiners.toString()) : undefined   // Max miners (optional, defaults to 5)
      );

      res.status(201).json(result);
    } catch (err) {
      next(err);
    }
  }
);

/**
 * GET /tasks/:taskID/public-keys - Get public keys for NDD-FE encryption
 * Returns publisher and aggregator public keys for a task
 */
router.get("/:taskID/public-keys", async (req, res, next) => {
  try {
    const { taskID } = req.params;
    const task = await getTaskById(taskID);
    
    // Get aggregator public key (from aggregator or environment)
    // For MVP: Return from environment or task metadata
    const tpPublicKey = process.env.TP_PUBLIC_KEY || "";
    const aggregatorPublicKey = process.env.AGGREGATOR_PK || "";
    
    res.json({
      taskID,
      tpPublicKey,
      aggregatorPublicKey,
      aggregatorAddress: (task as any).aggregator
    });
  } catch (err) {
    next(err);
  }
});

/**
 * GET /tasks/open - Get open tasks for FL client polling
 */
router.get("/open", async (req, res, next) => {
  try {
    const tasks = await getOpenTasks();
    res.json(tasks);
  } catch (err) {
    next(err);
  }
});

/**
 * GET /tasks/:taskID - Get specific task details
 */
router.get("/:taskID", async (req, res, next) => {
  try {
    const { taskID } = req.params;
    console.log(`[GET /tasks/${taskID}] Fetching task...`);
    const task = await getTaskById(taskID);
    console.log(`[GET /tasks/${taskID}] Task found, returning response`);
    res.json(task);
  } catch (err: any) {
    console.error(`[GET /tasks/${req.params.taskID}] Error:`, {
      message: err?.message,
      stack: err?.stack,
      name: err?.name
    });
    next(err);
  }
});

/**
 * GET /tasks - Get all tasks with optional filtering
 */
router.get("/", async (req, res, next) => {
  try {
    const { status, publisher, limit, offset } = req.query;
    
    // Validate status if provided
    const validStatuses = ['CREATED', 'OPEN', 'COMMIT_CLOSED', 'REVEAL_OPEN', 'REVEAL_CLOSED', 'AGGREGATING', 'VERIFIED', 'REWARDED', 'CANCELLED'];
    const statusValue = status as string;
    if (statusValue && !validStatuses.includes(statusValue)) {
      return res.status(400).json({ error: `Invalid status. Must be one of: ${validStatuses.join(', ')}` });
    }
    
    const filters = {
      status: statusValue as any,
      publisher: publisher as string,
      limit: limit ? parseInt(limit as string) : undefined,
      offset: offset ? parseInt(offset as string) : undefined
    };
    
    const tasks = await getAllTasks(filters);
    res.json(tasks);
  } catch (err) {
    next(err);
  }
});

/**
 * PUT /tasks/:taskID/status - Update task status (admin only)
 */
router.put(
  "/:taskID/status",
  requireFields(["status"]),
  requireWalletAuth,
  async (req, res, next) => {
    try {
      const { taskID } = req.params;
      const { status } = req.body;
      
      const updatedTask = await updateTaskStatus(taskID, status);
      res.json(updatedTask);
    } catch (err) {
      next(err);
    }
  }
);

/**
 * POST /tasks/check-deadlines - Check and update task deadlines
 */
router.post("/check-deadlines", async (req, res, next) => {
  try {
    const result = await checkTaskDeadlines();
    res.json(result);
  } catch (err) {
    next(err);
  }
});

/**
 * GET /tasks/scheduler/status - Get task scheduler status
 */
router.get("/scheduler/status", async (req, res, next) => {
  try {
    const { getSchedulerStatus } = await import("../services/taskScheduler.js");
    const status = getSchedulerStatus();
    res.json(status);
  } catch (err) {
    next(err);
  }
});

/**
 * POST /tasks/:taskID/check-refund - Check if task was refunded on-chain
 */
router.post("/:taskID/check-refund", async (req, res, next) => {
  try {
    const { taskID } = req.params;
    const { checkTaskRefundStatus } = await import("../services/refundDetectionService.js");
    
    // Check specific task
    const refundStatus = await checkTaskRefundStatus(taskID);
    
    // If refunded, update status
    if (refundStatus.isRefunded && refundStatus.backendStatus !== "CANCELLED") {
      const { updateTaskStatus } = await import("../services/taskService.js");
      await updateTaskStatus(taskID, "CANCELLED" as any);
      refundStatus.backendStatus = "CANCELLED" as any;
    }
    
    let message = "";
    if (!refundStatus.existsOnChain) {
      message = "Task does not exist on-chain. This is normal for test tasks or tasks where escrow transaction failed.";
    } else if (refundStatus.isCompleted) {
      message = "Task is completed (rewards distributed). Escrow balance is zero due to successful reward distribution.";
    } else if (refundStatus.isRefunded) {
      message = refundStatus.isFailed 
        ? "Task was refunded on-chain (status: FAILED). Status updated to CANCELLED."
        : "Task escrow is zero after deadline (implicit refund). Status updated to CANCELLED.";
    } else {
      message = "Task is not refunded. Escrow balance is active.";
    }
    
    res.json({
      taskID,
      ...refundStatus,
      message
    });
  } catch (err) {
    next(err);
  }
});

/**
 * POST /tasks/check-refunds - Manually trigger refund detection for all tasks
 */
router.post("/check-refunds", async (req, res, next) => {
  try {
    const { checkRefundedTasks } = await import("../services/refundDetectionService.js");
    const result = await checkRefundedTasks();
    res.json(result);
  } catch (err) {
    next(err);
  }
});

export default router;
