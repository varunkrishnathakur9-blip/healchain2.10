import { Router } from "express";
import { submitGradient } from "../services/trainingService.js";
import { submitCandidate } from "../services/aggregationService.js";
import { publishOnChain } from "../services/publisherService.js";
import { triggerAggregation, getAggregatorStatus } from "../services/aggregatorOrchestrationService.js";
import { requireFields } from "../middleware/validation.js";
import { requireWalletAuth } from "../middleware/auth.js";

const router = Router();

/**
 * M3: Miner submits encrypted update metadata
 * Algorithm 3: Accepts ciphertext (encrypted gradient) for aggregator decryption
 */
router.post(
  "/submit-update",
  requireFields([
    "taskID",
    "minerAddress",
    "scoreCommit",
    "encryptedHash",
    "message",
    "signature"
  ]),
  requireWalletAuth,
  async (req, res, next) => {
    try {
      await submitGradient({
        taskID: req.body.taskID,
        minerAddress: req.body.minerAddress,
        scoreCommit: req.body.scoreCommit,
        encryptedHash: req.body.encryptedHash,
        ciphertext: req.body.ciphertext, // Optional: JSON array of EC points
        signature: req.body.minerSignature || req.body.signature // Miner signature (different from wallet auth signature)
      });

      res.json({ status: "SUBMITTED" });
    } catch (err) {
      next(err);
    }
  }
);

/**
 * M4: Aggregator submits candidate block metadata
 */
router.post(
  "/submit-candidate",
  requireFields(["taskID", "modelHash", "accuracy"]),
  async (req, res, next) => {
    try {
      const { taskID, modelHash, accuracy } = req.body;

      const block = await submitCandidate(
        taskID,
        modelHash,
        BigInt(accuracy)
      );

      res.json(block);
    } catch (err) {
      next(err);
    }
  }
);

/**
 * M6: Aggregator publishes block on-chain
 */
router.post(
  "/publish",
  requireFields(["taskID", "modelHash", "accuracy", "miners"]),
  async (req, res, next) => {
    try {
      const { taskID, modelHash, accuracy, miners } = req.body;

      const txHash = await publishOnChain(
        taskID,
        modelHash,
        BigInt(accuracy),
        miners
      );

      res.json({ txHash });
    } catch (err) {
      next(err);
    }
  }
);

/**
 * M2: Fetch delivered skFE key for aggregator
 * Algorithm 2.3: Returns encrypted key (for verification)
 * 
 * NOTE: Since encryption is hash-based (not reversible), aggregator should
 * derive skFE directly using /key-derivation/:taskID endpoint instead.
 */
router.get(
  "/key/:taskID",
  async (req, res, next) => {
    try {
      const { taskID } = req.params;
      const { aggregatorAddress } = req.query;

      if (!aggregatorAddress) {
        return res.status(400).json({ error: "aggregatorAddress required" });
      }

      const { fetchDeliveredKey } = await import("../crypto/keyDelivery.js");
      const encryptedKey = await fetchDeliveredKey(taskID, aggregatorAddress as string);

      if (!encryptedKey) {
        return res.status(404).json({ error: "Key not delivered for this task" });
      }

      res.json({ encryptedKey });
    } catch (err) {
      next(err);
    }
  }
);

/**
 * M2: Get key derivation metadata for aggregator
 * Algorithm 2.2: Returns inputs needed to derive skFE deterministically
 * 
 * Since key derivation is deterministic, aggregator can derive skFE
 * using the same method as backend: H(publisher || minerPKs || taskID || nonceTP)
 */
router.get(
  "/key-derivation/:taskID",
  async (req, res, next) => {
    try {
      const { taskID } = req.params;
      const { prisma } = await import("../config/database.config.js");

      // Get task with miners
      const task = await prisma.task.findUnique({
        where: { taskID },
        include: {
          miners: {
            where: { proofVerified: true }, // Only verified miners (Algorithm 2)
            orderBy: { address: 'asc' },
            select: {
              address: true,
              publicKey: true
            }
          }
        }
      });

      if (!task) {
        return res.status(404).json({ error: "Task not found" });
      }

      // Check if aggregator is selected
      if (!task.aggregatorAddress) {
        const minMinersRequired = task.minMiners || 3;
        return res.status(400).json({ 
          error: `Aggregator not selected yet. Need at least ${minMinersRequired} verified miners.` 
        });
      }

      // Validate all miners have public keys
      const minersWithPKs = task.miners.filter(m => m.publicKey);
      if (minersWithPKs.length !== task.miners.length) {
        return res.status(400).json({ 
          error: "Some miners missing public keys. Cannot derive skFE." 
        });
      }

      // Return metadata for key derivation
      res.json({
        taskID: task.taskID,
        publisher: task.publisher.toLowerCase(),
        minerPublicKeys: minersWithPKs.map(m => m.publicKey).sort(),
        nonceTP: task.nonceTP,
        aggregatorAddress: task.aggregatorAddress,
        minerCount: task.miners.length,
        minMiners: task.minMiners || 3,  // Task-specific min miners (default to 3 for legacy tasks)
        maxMiners: task.maxMiners || 5   // Task-specific max miners (default to 5 for legacy tasks)
      });
    } catch (err) {
      next(err);
    }
  }
);

/**
 * POST /aggregator/:taskID/start
 * Trigger aggregator for a specific task
 */
router.post(
  "/:taskID/start",
  requireWalletAuth,
  async (req, res, next) => {
    try {
      const { taskID } = req.params;
      const aggregatorAddress = (req as any).walletAddress || req.body.aggregatorAddress;

      if (!aggregatorAddress) {
        return res.status(400).json({
          error: "Aggregator address is required"
        });
      }

      const result = await triggerAggregation(taskID, aggregatorAddress);
      
      if (result.success) {
        res.json({ success: true, message: result.message });
      } else {
        res.status(400).json({ 
          success: false, 
          error: result.message,
          message: result.message 
        });
      }
    } catch (err: any) {
      // Handle errors from triggerAggregation (task not found, address mismatch, etc.)
      const errorMessage = err?.message || "Failed to start aggregation";
      return res.status(400).json({
        success: false,
        error: errorMessage,
        message: errorMessage
      });
    }
  }
);

/**
 * GET /aggregator/:taskID/status
 * Get aggregator status for a task
 */
router.get(
  "/:taskID/status",
  async (req, res, next) => {
    try {
      const { taskID } = req.params;
      const status = await getAggregatorStatus(taskID);
      res.json(status);
    } catch (err) {
      next(err);
    }
  }
);

/**
 * GET /aggregator/:taskID/submissions
 * Algorithm 3: Get all miner submissions with ciphertext for aggregator (local service)
 * Returns full submission data including encrypted gradients (ciphertext)
 * SECURITY: Only accessible by the aggregator service running locally
 * 
 * This endpoint is for the aggregator Python service running on localhost.
 * It validates the aggregator address from the task instead of requiring wallet auth.
 */
router.get(
  "/:taskID/submissions",
  async (req, res, next) => {
    try {
      const { taskID } = req.params;
      const { prisma } = await import("../config/database.config.js");
      
      // Get task to verify aggregator
      const task = await prisma.task.findUnique({
        where: { taskID },
        include: {
          miners: {
            where: { proofVerified: true },
            orderBy: { address: 'asc' },
            select: {
              address: true
            }
          }
        }
      });

      if (!task) {
        return res.status(404).json({ error: "Task not found" });
      }

      // Use aggregator from database (set by PoS selection in finalizeMiners)
      // If not set, try to trigger PoS selection
      let aggregatorAddress = task.aggregatorAddress;
      if (!aggregatorAddress && task.miners.length >= (task.minMiners || 3)) {
        // Check if miners have verified proofs (required for PoS)
        const minersWithProofs = task.miners.filter((m: any) => m.proofVerified);
        if (minersWithProofs.length >= (task.minMiners || 3)) {
          try {
            const { finalizeMiners } = await import("../services/minerSelectionService.js");
            const result = await finalizeMiners(taskID);
            aggregatorAddress = result.aggregator;
          } catch (err: any) {
            console.warn(`Failed to finalize miners for task ${taskID}:`, err.message);
            // Don't fallback to first miner - return error instead
            return res.status(400).json({ 
              error: "Aggregator not selected yet. PoS selection failed.",
              details: err.message
            });
          }
        }
      }

      if (!aggregatorAddress) {
        return res.status(400).json({ 
          error: "Aggregator not selected yet for this task"
        });
      }

      // Get all gradients (submissions) for this task
      const gradients = await prisma.gradient.findMany({
        where: { taskID },
        include: {
          miner: {
            select: {
              address: true,
              publicKey: true
            }
          }
        },
        orderBy: { createdAt: "asc" }
      });

      // Transform to aggregator-expected format
      const submissions = gradients.map((grad: any) => {
        // Parse ciphertext if it's a JSON string
        let ciphertext = grad.ciphertext;
        if (typeof ciphertext === 'string') {
          try {
            ciphertext = JSON.parse(ciphertext);
          } catch (e) {
            // If parsing fails, treat as single string
            ciphertext = [ciphertext];
          }
        }
        
        return {
          taskID: taskID, // Required by aggregator
          task_id: taskID, // Also include snake_case version
          miner_address: grad.miner.address.toLowerCase(),
          miner_pk: grad.miner.publicKey,
          ciphertext: ciphertext, // Parsed array of EC points
          encrypted_hash: grad.encryptedHash,
          encryptedHash: grad.encryptedHash, // Also include camelCase
          score_commit: grad.scoreCommit,
          scoreCommit: grad.scoreCommit, // Also include camelCase for normalization
          signature: grad.signature,
          submitted_at: grad.createdAt.toISOString()
        };
      });

      res.json(submissions);
    } catch (err) {
      next(err);
    }
  }
);

/**
 * POST /aggregator/:taskID/submissions
 * Algorithm 3: Get all miner submissions with ciphertext for aggregator
 * Returns full submission data including encrypted gradients (ciphertext)
 * SECURITY: Only accessible by the selected aggregator
 * 
 * Note: Changed to POST to support wallet authentication (signature in body)
 * This endpoint is for frontend/UI access with wallet authentication
 */
router.post(
  "/:taskID/submissions",
  requireWalletAuth,
  async (req, res, next) => {
    try {
      const { taskID } = req.params;
      const { prisma } = await import("../config/database.config.js");
      
      // Get authenticated aggregator address from wallet auth
      const authenticatedAddress = (req as any).walletAddress;
      if (!authenticatedAddress) {
        return res.status(401).json({ error: "Wallet authentication required" });
      }

      // Get task to verify aggregator
      const task = await prisma.task.findUnique({
        where: { taskID },
        include: {
          miners: {
            where: { proofVerified: true },
            orderBy: { address: 'asc' },
            select: {
              address: true
            }
          }
        }
      });

      if (!task) {
        return res.status(404).json({ error: "Task not found" });
      }

      // Use aggregator from database (set by PoS selection in finalizeMiners)
      // If not set, try to trigger PoS selection
      let aggregatorAddress = task.aggregatorAddress;
      if (!aggregatorAddress && task.miners.length >= (task.minMiners || 3)) {
        // Check if miners have verified proofs (required for PoS)
        const minersWithProofs = task.miners.filter((m: any) => m.proofVerified);
        if (minersWithProofs.length >= (task.minMiners || 3)) {
          try {
            const { finalizeMiners } = await import("../services/minerSelectionService.js");
            const result = await finalizeMiners(taskID);
            aggregatorAddress = result.aggregator;
          } catch (err: any) {
            console.warn(`Failed to finalize miners for task ${taskID}:`, err.message);
            // Don't fallback to first miner - return error instead
            return res.status(400).json({ 
              error: "Aggregator not selected yet. PoS selection failed.",
              details: err.message
            });
          }
        }
      }

      // SECURITY: Verify authenticated address is the selected aggregator
      if (!aggregatorAddress || authenticatedAddress.toLowerCase() !== aggregatorAddress.toLowerCase()) {
        return res.status(403).json({ 
          error: "Unauthorized: Only the selected aggregator can access submissions",
          message: aggregatorAddress 
            ? `This endpoint is restricted to aggregator ${aggregatorAddress}. Your address: ${authenticatedAddress}`
            : "Aggregator not selected yet for this task"
        });
      }

      // Get all gradients (submissions) for this task
      const gradients = await prisma.gradient.findMany({
        where: { taskID },
        include: {
          miner: {
            select: {
              address: true,
              publicKey: true
            }
          }
        },
        orderBy: { createdAt: "asc" }
      });

      // Transform to aggregator-expected format
      const submissions = gradients.map((grad) => ({
        taskID: grad.taskID,
        minerAddress: grad.minerAddress,
        miner_pk: grad.minerAddress, // For aggregator compatibility
        publicKey: grad.miner?.publicKey || null,
        scoreCommit: grad.scoreCommit,
        encryptedHash: grad.encryptedHash,
        ciphertext: grad.ciphertext ? JSON.parse(grad.ciphertext) : null, // Parse JSON array
        signature: grad.signature || null,
        status: grad.status,
        submittedAt: grad.createdAt.toISOString()
      }));

      res.json(submissions);
    } catch (err) {
      next(err);
    }
  }
);

/**
 * POST /aggregator/:taskID/key-status
 * Algorithm 2: Get skFE derivation status and metadata
 * Returns key derivation information for the aggregator dashboard
 * SECURITY: Only accessible by the selected aggregator
 * 
 * Note: Changed to POST to support wallet authentication (signature in body)
 */
router.post(
  "/:taskID/key-status",
  requireWalletAuth,
  async (req, res, next) => {
    try {
      const { taskID } = req.params;
      const { prisma } = await import("../config/database.config.js");
      
      // Get authenticated aggregator address from wallet auth
      const authenticatedAddress = (req as any).walletAddress;
      if (!authenticatedAddress) {
        return res.status(401).json({ error: "Wallet authentication required" });
      }

      // Get task with miners
      const task = await prisma.task.findUnique({
        where: { taskID },
        include: {
          miners: {
            where: { proofVerified: true },
            orderBy: { address: 'asc' },
            select: {
              address: true,
              publicKey: true
            }
          }
        }
      });

      if (!task) {
        return res.status(404).json({ error: "Task not found" });
      }

      // Use aggregator from database (set by PoS selection in finalizeMiners)
      // If not set, try to trigger PoS selection
      let aggregatorAddress = task.aggregatorAddress;
      if (!aggregatorAddress && task.miners.length >= (task.minMiners || 3)) {
        // Check if miners have verified proofs (required for PoS)
        const minersWithProofs = task.miners.filter((m: any) => m.proofVerified);
        if (minersWithProofs.length >= (task.minMiners || 3)) {
          try {
            const { finalizeMiners } = await import("../services/minerSelectionService.js");
            const result = await finalizeMiners(taskID);
            aggregatorAddress = result.aggregator;
          } catch (err: any) {
            console.warn(`Failed to finalize miners for task ${taskID}:`, err.message);
            // Don't fallback to first miner - return error instead
            return res.status(400).json({ 
              error: "Aggregator not selected yet. PoS selection failed.",
              details: err.message
            });
          }
        }
      }

      // Check if aggregator is selected (either in DB or computed)
      if (!aggregatorAddress) {
        const minMinersRequired = task.minMiners || 3;
        return res.json({
          taskID,
          keyDerived: false,
          aggregatorSelected: false,
          message: `Aggregator not selected yet. Need at least ${minMinersRequired} verified miners.`,
          minerCount: task.miners.length,
          requiredMiners: minMinersRequired
        });
      }

      // SECURITY: Verify authenticated address is the selected aggregator
      if (authenticatedAddress.toLowerCase() !== aggregatorAddress.toLowerCase()) {
        return res.status(403).json({ 
          error: "Unauthorized: Only the selected aggregator can access key derivation metadata",
          message: `This endpoint is restricted to aggregator ${aggregatorAddress}. Your address: ${authenticatedAddress}`
        });
      }

      // Check if key delivery exists
      const keyDelivery = await prisma.keyDelivery.findUnique({
        where: {
          taskID_aggregatorAddress: {
            taskID,
            aggregatorAddress: aggregatorAddress.toLowerCase()
          }
        }
      });

      // Prepare derivation metadata
      const minersWithPKs = task.miners.filter(m => m.publicKey);
      const minMinersRequired = task.minMiners || 3;
      const canDerive = minersWithPKs.length === task.miners.length && task.miners.length >= minMinersRequired;

      return res.json({
        taskID,
        keyDerived: !!keyDelivery || canDerive,
        aggregatorSelected: true,
        aggregatorAddress: aggregatorAddress,
        publisher: task.publisher.toLowerCase(),
        minerCount: task.miners.length,
        minersWithPublicKeys: minersWithPKs.length,
        canDerive,
        derivationMetadata: canDerive ? {
          publisher: task.publisher.toLowerCase(),
          minerPublicKeys: minersWithPKs.map(m => m.publicKey).sort(),
          nonceTP: task.nonceTP,
          aggregatorAddress: aggregatorAddress.toLowerCase()
        } : null,
        keyDelivered: !!keyDelivery,
        keyDeliveredAt: keyDelivery?.deliveredAt.toISOString() || null,
        derivationMethod: "Algorithm 2.2: H(publisher || minerPKs || taskID || nonceTP)"
      });
    } catch (err) {
      next(err);
    }
  }
);

export default router;
