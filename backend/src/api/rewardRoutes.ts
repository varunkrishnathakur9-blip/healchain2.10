import { Router } from "express";
import { distribute } from "../services/rewardService.js";
import { requireFields } from "../middleware/validation.js";

const router = Router();

/**
 * M7: Trigger reward distribution
 * (Reveal txs already done by TP + miners directly)
 */
router.post(
  "/distribute",
  requireFields(["taskID", "miners"]),
  async (req, res, next) => {
    try {
      const { taskID, miners } = req.body;

      const tx = await distribute(taskID, miners);

      res.json({ status: "DISTRIBUTED", txHash: tx.hash });
    } catch (err) {
      next(err);
    }
  }
);

export default router;
