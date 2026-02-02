import { Router } from "express";
import { registerMiner, finalizeMiners } from "../services/minerSelectionService.js";
import { triggerTraining, getTrainingStatus, triggerSubmission } from "../services/trainingOrchestrationService.js";
import { requireFields } from "../middleware/validation.js";
import { requireWalletAuth } from "../middleware/auth.js";
import { prisma } from "../config/database.config.js";

const router = Router();

/**
 * M2: Miner registers for a task
 * Algorithm 2 from BTP Report Section 4.3
 * 
 * Algorithm 2 Requirements:
 * - Miner must provide proof (IPFS link or system proof)
 * - Proof is verified against dataset requirements (D)
 * - Only miners with valid proofs are accepted
 * - Miner selection and key derivation proceed only after proof verification
 */
router.post(
  "/register",
  requireFields(["taskID", "address", "proof", "message", "signature"]), // proof is now required
  requireWalletAuth,
  async (req, res, next) => {
    try {
      const { taskID, address, publicKey, stake, proof, flClientUrl } = req.body;

      // Validate proof is provided (Algorithm 2 requirement)
      if (!proof || proof.trim() === '') {
        return res.status(400).json({
          error: "Miner proof is required (Algorithm 2). Please provide IPFS link or system proof."
        });
      }

      // Use the verified address from auth middleware
      const verifiedAddress = (req as any).walletAddress || address;

      // Convert stake to BigInt if provided
      let stakeBigInt: bigint | undefined = undefined;
      if (stake !== undefined && stake !== null) {
        try {
          stakeBigInt = typeof stake === 'string' ? BigInt(stake) : BigInt(Number(stake));
        } catch (err) {
          return res.status(400).json({
            error: `Invalid stake value: ${stake}. Must be a valid number.`
          });
        }
      }

      const miner = await registerMiner(
        taskID,
        verifiedAddress,
        publicKey, // Optional: miner's public key for key derivation
        stakeBigInt, // Optional: miner's stake for PoS selection
        proof,        // Algorithm 2: Miner proof (required)
        flClientUrl  // Optional: FL Client service URL for distributed training
      );

      // Convert BigInt fields to strings for JSON serialization
      const minerResponse = {
        ...miner,
        stake: miner.stake?.toString(),
      };

      res.status(201).json(minerResponse);
    } catch (err: any) {
      // Log error for debugging
      console.error('Miner registration error:', {
        message: err?.message,
        stack: err?.stack,
        name: err?.name,
        code: err?.code
      });
      next(err);
    }
  }
);

/**
 * GET /miners/my-tasks - Get all tasks a miner is registered for
 * Returns list of taskIDs where the miner has registered
 */
router.get(
  "/my-tasks",
  async (req, res, next) => {
    try {
      const { address } = req.query;

      if (!address || typeof address !== 'string') {
        return res.status(400).json({
          error: "Miner address is required"
        });
      }

      // Get all tasks where this miner is registered
      const miners = await prisma.miner.findMany({
        where: {
          address: address.toLowerCase(),
          proofVerified: true  // Only count verified registrations
        },
        select: {
          taskID: true,
          address: true,
          proofVerified: true,
          task: {
            select: {
              taskID: true,
              status: true,
              publisher: true,
              deadline: true,
            }
          }
        }
      });

      // Extract taskIDs
      const taskIDs = miners.map(m => m.taskID);

      res.json({
        address: address.toLowerCase(),
        registeredTaskIDs: taskIDs,
        count: taskIDs.length,
        tasks: miners.map(m => ({
          taskID: m.taskID,
          status: m.task.taskID ? m.task.status : null,
          publisher: m.task.taskID ? m.task.publisher : null,
          deadline: m.task.taskID ? m.task.deadline?.toString() : null,
        }))
      });
    } catch (err) {
      next(err);
    }
  }
);

/**
 * POST /miners/:address/tasks/:taskID/start-training
 * Trigger FL client training for a miner on a specific task
 */
router.post(
  "/:address/tasks/:taskID/start-training",
  requireWalletAuth,
  async (req, res, next) => {
    try {
      const { address, taskID } = req.params;
      const verifiedAddress = (req as any).walletAddress || address;

      // Verify the address matches
      if (verifiedAddress.toLowerCase() !== address.toLowerCase()) {
        return res.status(403).json({
          error: "Address mismatch. You can only trigger training for your own address."
        });
      }

      const result = await triggerTraining(taskID, verifiedAddress);

      if (result.success) {
        res.json({ success: true, message: result.message });
      } else {
        res.status(400).json({ success: false, message: result.message });
      }
    } catch (err: any) {
      // Log the error for debugging
      console.error(`[Start Training] Error for taskID=${req.params.taskID}, address=${req.params.address}:`, {
        message: err?.message,
        stack: err?.stack
      });
      next(err);
    }
  }
);

/**
 * GET /miners/:address/tasks/:taskID/training-status
 * Get training status for a miner on a task
 */
router.get(
  "/:address/tasks/:taskID/training-status",
  async (req, res, next) => {
    try {
      const { address, taskID } = req.params;
      const status = await getTrainingStatus(taskID, address);
      res.json(status);
    } catch (err: any) {
      // Handle database connection errors gracefully
      if (err?.code === 'P1001' || err?.message?.includes("Can't reach database server")) {
        console.error(`[GET /miners/${req.params.address}/tasks/${req.params.taskID}/training-status] Database connection error:`, err.message);
        // Return IDLE status if database is unavailable - let FL client service handle status
        return res.json({
          taskID: req.params.taskID,
          minerAddress: req.params.address.toLowerCase(),
          status: "IDLE"
        });
      }
      next(err);
    }
  }
);

/**
 * POST /miners/:address/tasks/:taskID/submit-gradient
 * M3: Manually trigger gradient submission to aggregator
 * This calls the FL client service to submit the gradient
 */
router.post(
  "/:address/tasks/:taskID/submit-gradient",
  requireWalletAuth,
  async (req, res, next) => {
    try {
      const { address, taskID } = req.params;
      const verifiedAddress = (req as any).walletAddress || address;

      if (verifiedAddress.toLowerCase() !== address.toLowerCase()) {
        return res.status(403).json({
          error: "Address mismatch. You can only submit gradients for your own address."
        });
      }

      // Pass wallet auth signature to FL client service so it can authenticate with backend
      const walletAuth = {
        address: verifiedAddress,
        message: req.body.message,
        signature: req.body.signature
      };

      const result = await triggerSubmission(taskID, verifiedAddress, walletAuth);

      if (result.success) {
        res.json({ success: true, message: result.message });
      } else {
        res.status(400).json({ success: false, message: result.message });
      }
    } catch (err) {
      console.error(`[POST /miners/${req.params.address}/tasks/${req.params.taskID}/submit-gradient] Error:`, err);
      next(err);
    }
  }
);

export default router;
