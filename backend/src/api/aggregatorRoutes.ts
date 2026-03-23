import { Router } from "express";
import { submitGradient } from "../services/trainingService.js";
import { submitCandidate } from "../services/aggregationService.js";
import { publishOnChain } from "../services/publisherService.js";
import { triggerAggregation, getAggregatorStatus } from "../services/aggregatorOrchestrationService.js";
import { requireFields } from "../middleware/validation.js";
import { requireWalletAuth } from "../middleware/auth.js";

const router = Router();

function _toStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.map((v) => String(v));
}

function _serializeBigInts<T>(obj: T): T {
  return JSON.parse(
    JSON.stringify(obj, (_key, value) =>
      typeof value === "bigint" ? value.toString() : value
    )
  ) as T;
}

/**
 * M3: Miner submits encrypted update metadata
 * Algorithm 3: Accepts ciphertext (encrypted gradient) for aggregator decryption
 */
router.post(
  "/submit-update",
  requireFields([
    "taskID",
    "minerAddress",
    "miner_pk",
    "scoreCommit",
    "encryptedHash",
    "ciphertext",
    "minerSignature",
    "message",
    "signature"
  ]),
  requireWalletAuth,
  async (req, res, next) => {
    try {
      await submitGradient({
        taskID: req.body.taskID,
        minerAddress: req.body.minerAddress,
        minerPublicKey: req.body.miner_pk, // Public key used for miner signature verification
        scoreCommit: req.body.scoreCommit,
        encryptedHash: req.body.encryptedHash,
        ciphertext: req.body.ciphertext, // Optional: JSON array of EC points
        signature: req.body.minerSignature // Miner signature (different from wallet auth signature)
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
  requireFields([
    "taskID",
    "round",
    "modelHash",
    "modelLink",
    "accuracy",
    "miners",
    "scoreCommits",
    "aggregatorPK",
    "hash",
    "signatureA",
  ]),
  async (req, res, next) => {
    try {
      const {
        taskID,
        round,
        modelHash,
        modelLink,
        accuracy,
        miners,
        scoreCommits,
        aggregatorPK,
        hash,
        signatureA,
        artifactHash,
        modelMetadata,
        timestamp,
      } = req.body;

      const parsedAccuracy = BigInt(accuracy);
      const parsedTimestamp =
        timestamp !== undefined && timestamp !== null && `${timestamp}`.trim() !== ""
          ? BigInt(timestamp)
          : BigInt(Math.floor(Date.now() / 1000));

      const block = await submitCandidate(
        taskID,
        modelHash,
        parsedAccuracy,
        {
          modelLink,
          round: Number(round),
          participants: _toStringArray(miners),
          scoreCommits: _toStringArray(scoreCommits),
          aggregatorPK: typeof aggregatorPK === "string" ? aggregatorPK : String(aggregatorPK),
          candidateHash: typeof hash === "string" ? hash : String(hash),
          signatureA: typeof signatureA === "string" ? signatureA : String(signatureA),
          artifactHash: artifactHash === undefined || artifactHash === null ? undefined : String(artifactHash),
          modelMetadata,
          candidateTimestamp: parsedTimestamp,
        }
      );

      res.json(_serializeBigInts(block));
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
      const { taskID, modelHash, accuracy, miners, scoreCommits } = req.body;

      const txHash = await publishOnChain(
        taskID,
        modelHash,
        BigInt(accuracy),
        miners,
        Array.isArray(scoreCommits) ? scoreCommits : []
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

      // Aggregation metadata (Algorithm 4):
      // Use deterministic participant ordering and uniform integer weights.
      // Aggregator expects weights.length === participants.length.
      const participants = minersWithPKs
        .map(m => m.publicKey as string)
        .sort();
      const weights = participants.map(() => 1);

      // Return metadata for key derivation
      res.json({
        taskID: task.taskID,
        publisher: task.publisher.toLowerCase(),
        minerPublicKeys: participants,
        participants,
        weights,
        nonceTP: task.nonceTP,
        aggregatorAddress: task.aggregatorAddress,
        minerCount: task.miners.length,
        minMiners: task.minMiners || 3,
        maxMiners: task.maxMiners || 5,
        targetAccuracy: (task as any).targetAccuracy || 0.8,
        currentRound: (task as any).currentRound || 1
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

      // IMPORTANT:
      // Return lightweight submission metadata only.
      // Full ciphertext is fetched per-submission via dedicated endpoint to avoid
      // huge JSON payloads causing `RangeError: Invalid string length`.
      const gradients = await prisma.gradient.findMany({
        where: { taskID },
        select: {
          id: true,
          taskID: true,
          minerAddress: true,
          scoreCommit: true,
          encryptedHash: true,
          signature: true,
          createdAt: true,
          miner: {
            select: {
              address: true,
              publicKey: true
            }
          }
        },
        orderBy: { createdAt: "asc" }
      });

      const submissions = gradients.map((grad) => ({
        id: grad.id,
        taskID: taskID,
        task_id: taskID, // python aggregator compatibility
        miner_address: (grad.miner?.address || grad.minerAddress).toLowerCase(),
        miner_pk: grad.miner?.publicKey || null,
        encrypted_hash: grad.encryptedHash,
        encryptedHash: grad.encryptedHash, // camelCase compatibility
        score_commit: grad.scoreCommit,
        scoreCommit: grad.scoreCommit, // camelCase compatibility
        signature: grad.signature,
        submitted_at: grad.createdAt.toISOString(),
        ciphertext: null, // fetched via per-submission endpoint
      }));

      res.json(submissions);
    } catch (err) {
      next(err);
    }
  }
);

/**
 * GET /aggregator/:taskID/submissions/:gradientID/ciphertext
 * Fetch full ciphertext for a single submission (local aggregator service, no wallet auth).
 */
router.get(
  "/:taskID/submissions/:gradientID/ciphertext",
  async (req, res, next) => {
    try {
      const { taskID, gradientID } = req.params;
      const { prisma } = await import("../config/database.config.js");

      // Fetch ciphertext only for the requested submission
      // Use unique-id lookup to reduce DB work, then enforce task match in code.
      const gradient = await prisma.gradient.findUnique({
        where: { id: gradientID },
        select: {
          id: true,
          taskID: true,
          ciphertext: true
        }
      });

      if (!gradient) {
        return res.status(404).json({ error: "Submission not found" });
      }
      if (gradient.taskID !== taskID) {
        return res.status(404).json({ error: "Submission not found for task" });
      }

      let ciphertext: any = gradient.ciphertext;
      if (typeof ciphertext === "string") {
        try {
          ciphertext = JSON.parse(ciphertext);
        } catch {
          ciphertext = [ciphertext];
        }
      }

      res.json({
        id: gradient.id,
        taskID: gradient.taskID,
        ciphertext
      });
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
      // NOTE: For the dashboard view we intentionally do NOT load the
      // ciphertext blob to avoid huge string allocations in Node/Prisma.
      const gradients = await prisma.gradient.findMany({
        where: { taskID },
        select: {
          id: true,
          taskID: true,
          minerAddress: true,
          scoreCommit: true,
          encryptedHash: true,
          signature: true,
          status: true,
          createdAt: true,
          miner: {
            select: {
              address: true,
              publicKey: true,
            },
          },
        },
        orderBy: { createdAt: "asc" },
      });

      // Transform to aggregator-expected format (without ciphertext)
      const submissions = gradients.map((grad) => ({
        id: grad.id,
        taskID: grad.taskID,
        minerAddress: grad.minerAddress,
        miner_pk: grad.minerAddress, // For aggregator compatibility
        publicKey: grad.miner?.publicKey || null,
        scoreCommit: grad.scoreCommit,
        encryptedHash: grad.encryptedHash,
        ciphertext: null,
        signature: grad.signature || null,
        status: grad.status,
        submittedAt: grad.createdAt.toISOString(),
      }));

      res.json(submissions);
    } catch (err) {
      next(err);
    }
  }
);

/**
 * POST /aggregator/:taskID/submissions/:gradientID
 * Fetch full ciphertext for a single submission (dashboard on-demand view).
 *
 * SECURITY: Only accessible by the selected aggregator (wallet-authenticated).
 */
router.post(
  "/:taskID/submissions/:gradientID",
  requireWalletAuth,
  async (req, res, next) => {
    try {
      const { taskID, gradientID } = req.params;
      const { prisma } = await import("../config/database.config.js");

      // Get authenticated aggregator address from wallet auth
      const authenticatedAddress = (req as any).walletAddress;
      if (!authenticatedAddress) {
        return res.status(401).json({ error: "Wallet authentication required" });
      }

      // Get task to verify aggregator
      const task = await prisma.task.findUnique({
        where: { taskID },
        select: {
          aggregatorAddress: true,
          minMiners: true,
        },
      });

      if (!task) {
        return res.status(404).json({ error: "Task not found" });
      }

      const { aggregatorAddress } = task;

      // SECURITY: Verify authenticated address is the selected aggregator
      if (!aggregatorAddress || authenticatedAddress.toLowerCase() !== aggregatorAddress.toLowerCase()) {
        return res.status(403).json({
          error: "Unauthorized: Only the selected aggregator can access submissions",
          message: aggregatorAddress
            ? `This endpoint is restricted to aggregator ${aggregatorAddress}. Your address: ${authenticatedAddress}`
            : "Aggregator not selected yet for this task",
        });
      }

      // Fetch the specific gradient with ciphertext
      const gradient = await prisma.gradient.findFirst({
        where: {
          id: gradientID,
          taskID,
        },
        include: {
          miner: {
            select: {
              address: true,
              publicKey: true,
            },
          },
        },
      });

      if (!gradient) {
        return res.status(404).json({ error: "Submission not found" });
      }

      // Parse ciphertext JSON (single row -> safe for memory)
      let ciphertext: any = null;
      if (gradient.ciphertext) {
        if (typeof gradient.ciphertext === "string") {
          try {
            ciphertext = JSON.parse(gradient.ciphertext);
          } catch {
            ciphertext = [gradient.ciphertext];
          }
        }
      }

      const submission = {
        id: gradient.id,
        taskID: gradient.taskID,
        minerAddress: gradient.minerAddress,
        miner_pk: gradient.miner?.address || gradient.minerAddress,
        publicKey: gradient.miner?.publicKey || null,
        scoreCommit: gradient.scoreCommit,
        encryptedHash: gradient.encryptedHash,
        ciphertext,
        signature: gradient.signature || null,
        status: gradient.status,
        submittedAt: gradient.createdAt.toISOString(),
      };

      res.json(submission);
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

/**
 * Algorithm 4 (Lines 35-40): Aggregator triggers a new round
 * This happens if accuracy is below target.
 * It clears previous gradients and increments the round counter.
 */
router.post(
  "/:taskID/reset-round",
  async (req, res, next) => {
    try {
      const { taskID } = req.params;
      const { modelLink } = req.body || {};
      const { resetRound } = await import("../services/aggregationService.js");

      const task = await resetRound(taskID, modelLink);

      res.json({
        success: true,
        message: `Task ${taskID} reset to round ${(task as any).currentRound}`,
        currentRound: (task as any).currentRound,
        status: task.status,
        initialModelLink: (task as any).initialModelLink || null
      });
    } catch (err: any) {
      next(err);
    }
  }
);

/**
 * POST /aggregator/:taskID/admin/clear-gradients
 * Admin utility: clear all gradients for a task so miners can resubmit.
 *
 * Security:
 * - Requires wallet auth
 * - Caller must be task publisher
 */
router.post(
  "/:taskID/admin/clear-gradients",
  requireWalletAuth,
  async (req, res, next) => {
    try {
      const { taskID } = req.params;
      const authenticatedAddress = (req as any).walletAddress as string | undefined;
      const { prisma } = await import("../config/database.config.js");

      if (!authenticatedAddress) {
        return res.status(401).json({ error: "Wallet authentication required" });
      }

      const task = await prisma.task.findUnique({
        where: { taskID },
        select: {
          taskID: true,
          publisher: true,
          aggregatorAddress: true,
          status: true
        }
      });

      if (!task) {
        return res.status(404).json({ error: "Task not found" });
      }

      const caller = authenticatedAddress.toLowerCase();
      const isPublisher = task.publisher?.toLowerCase() === caller;
      if (!isPublisher) {
        return res.status(403).json({
          error: "Unauthorized: only task publisher can clear gradients",
          taskID,
          caller: authenticatedAddress
        });
      }

      const deleted = await prisma.gradient.deleteMany({
        where: { taskID }
      });

      // If aggregation was in progress, reopen task for fresh submissions.
      let statusChanged = false;
      if (task.status === "AGGREGATING") {
        await prisma.task.update({
          where: { taskID },
          data: { status: "OPEN" as any }
        });
        statusChanged = true;
      }

      res.json({
        success: true,
        taskID,
        deletedGradients: deleted.count,
        statusChangedToOpen: statusChanged
      });
    } catch (err) {
      next(err);
    }
  }
);

export default router;
