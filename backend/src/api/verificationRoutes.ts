/**
 * HealChain Backend - Verification Routes
 * M5: Miner Verification Feedback (Algorithm 5)
 */

import { Router } from "express";
import { submitVerification, getConsensusResult, getVerifications } from "../services/verificationService.js";
import { requireFields } from "../middleware/validation.js";
import { requireWalletAuth } from "../middleware/auth.js";

const router = Router();

/**
 * M5: Miner submits verification vote
 * Algorithm 5 from BTP Report Section 4.6
 */
router.post(
  "/submit",
  requireFields(["taskID", "minerAddress", "verdict", "message", "signature"]),
  requireWalletAuth,
  async (req, res, next) => {
    try {
      const { taskID, minerAddress, verdict, signature } = req.body;

      if (verdict !== "VALID" && verdict !== "INVALID") {
        return res.status(400).json({ error: "Verdict must be VALID or INVALID" });
      }

      const verification = await submitVerification(
        taskID,
        minerAddress,
        verdict as "VALID" | "INVALID",
        signature
      );

      res.status(201).json(verification);
    } catch (err) {
      next(err);
    }
  }
);

/**
 * M5: Get consensus result
 */
router.get(
  "/consensus/:taskID",
  async (req, res, next) => {
    try {
      const { taskID } = req.params;
      const result = await getConsensusResult(taskID);
      res.json(result);
    } catch (err) {
      next(err);
    }
  }
);

/**
 * Get all verifications for a task
 */
router.get(
  "/:taskID",
  async (req, res, next) => {
    try {
      const { taskID } = req.params;
      const verifications = await getVerifications(taskID);
      res.json(verifications);
    } catch (err) {
      next(err);
    }
  }
);

export default router;

