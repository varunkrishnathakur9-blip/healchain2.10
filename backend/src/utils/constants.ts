/**
 * HealChain Backend – Global Constants
 * -----------------------------------
 * These constants define backend-level protocol behavior.
 * Smart contracts remain the final authority.
 */

/**
 * Task lifecycle states (off-chain mirror of protocol flow)
 */
export const TASK_STATUS = {
  CREATED: "CREATED",                 // M1: Task registered, escrow pending
  ESCROW_LOCKED: "ESCROW_LOCKED",     // Escrow confirmed (frontend tx)
  TRAINING: "TRAINING",               // M2/M3: Miner training phase
  AGGREGATED: "AGGREGATED",           // M4: Aggregation complete
  VERIFIED: "VERIFIED",               // M5: Miner consensus passed
  ONCHAIN_PUBLISHED: "ONCHAIN_PUBLISHED", // M6: Block published
  AWAITING_REVEAL: "AWAITING_REVEAL", // M7: Commit–reveal phase
  COMPLETED: "COMPLETED",             // Rewards distributed
  FAILED: "FAILED"                    // Task aborted / timeout
} as const;

export type TaskStatus =
  typeof TASK_STATUS[keyof typeof TASK_STATUS];

/**
 * Protocol thresholds (backend-side only)
 */
export const PROTOCOL_LIMITS = {
  MIN_MINERS: 2,            // Minimum miners required (M2)
  CONSENSUS_RATIO: 0.5,     // Simple majority (M5)
} as const;

/**
 * Time windows (milliseconds)
 * These are for backend coordination only.
 * Smart contracts enforce final deadlines.
 */
export const TIME_WINDOWS = {
  AGGREGATION_TIMEOUT: 60 * 60 * 1000,   // 1 hour
  VERIFICATION_TIMEOUT: 60 * 60 * 1000,  // 1 hour
} as const;

/**
 * Common error messages (optional but useful)
 */
export const ERROR_MESSAGES = {
  TASK_NOT_FOUND: "Task not found",
  INVALID_STATUS: "Invalid task status",
  UNAUTHORIZED: "Unauthorized request",
  INSUFFICIENT_MINERS: "Insufficient miners",
  DUPLICATE_SUBMISSION: "Duplicate submission"
} as const;
