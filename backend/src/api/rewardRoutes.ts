import { Router } from "express";
import { distribute, syncRewardRowsFromChain } from "../services/rewardService.js";
import { requireFields } from "../middleware/validation.js";

const router = Router();

/**
 * M7: Trigger reward distribution
 * (Reveal txs already done by TP + miners directly)
 */
router.post(
  "/distribute",
  requireFields(["taskID"]),
  async (req, res, next) => {
    try {
      const { taskID } = req.body;

      const tx = await distribute(taskID);

      res.json({ status: "DISTRIBUTED", txHash: tx.hash });
    } catch (err) {
      next(err);
    }
  }
);

/**
 * Force backfill Reward rows from on-chain M7 state.
 * Useful when distribution happened directly from wallet and DB rows are stale.
 */
router.post(
  "/sync",
  requireFields(["taskID"]),
  async (req, res, next) => {
    try {
      const { taskID } = req.body;
      const result = await syncRewardRowsFromChain(taskID);
      res.json({ taskID, ...result });
    } catch (err) {
      next(err);
    }
  }
);

export default router;
