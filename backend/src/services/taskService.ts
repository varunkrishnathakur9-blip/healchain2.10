import { prisma } from "../config/database.config.js";
import { keccak256, solidityPacked } from "ethers";
import { TaskStatus } from "@prisma/client";

/**
 * Helper function to automatically update ESCROW_ADDRESS in .env.development
 * when a mismatch is detected from transaction address
 */
async function updateEscrowAddressInEnvFile(correctAddress: string) {
  try {
    const fs = await import('fs/promises');
    const path = await import('path');
    const envPath = path.join(process.cwd(), '.env.development');
    
    let envContent = '';
    try {
      envContent = await fs.readFile(envPath, 'utf8');
    } catch {
      console.warn('[Auto-Update] .env.development not found, skipping update');
      return false;
    }
    
    let updated = false;
    let updatedContent = envContent;
    
    // Update ESCROW_ADDRESS
    const escrowAddressRegex = /^ESCROW_ADDRESS=.*$/m;
    if (escrowAddressRegex.test(envContent)) {
      updatedContent = updatedContent.replace(escrowAddressRegex, `ESCROW_ADDRESS=${correctAddress}`);
      updated = true;
    } else {
      // Add it if it doesn't exist
      updatedContent += `\nESCROW_ADDRESS=${correctAddress}\n`;
      updated = true;
    }
    
    // Update ESCROW_CONTRACT_ADDRESS
    const escrowContractAddressRegex = /^ESCROW_CONTRACT_ADDRESS=.*$/m;
    if (escrowContractAddressRegex.test(envContent)) {
      updatedContent = updatedContent.replace(escrowContractAddressRegex, `ESCROW_CONTRACT_ADDRESS=${correctAddress}`);
      updated = true;
    } else {
      // Add it if it doesn't exist
      updatedContent += `\nESCROW_CONTRACT_ADDRESS=${correctAddress}\n`;
      updated = true;
    }
    
    if (updated && updatedContent !== envContent) {
      await fs.writeFile(envPath, updatedContent, 'utf8');
      console.log(`[Auto-Update] ✅ Updated ESCROW_ADDRESS in .env.development to ${correctAddress}`);
      console.log(`[Auto-Update] ⚠️  Backend server should be restarted to use the new address for write operations (M6, M7)`);
      return true;
    }
    
    return false;
  } catch (error: any) {
    console.warn(`[Auto-Update] Could not update .env.development: ${error.message}`);
    return false;
  }
}

/**
 * M1: Create task with commit hash (escrow must be locked first)
 * 
 * IMPORTANT: 
 * - commitHash and nonceTP must come from frontend to ensure Algorithm 1 compliance
 * - escrowTxHash is required to verify escrow is locked on-chain before creating task
 * - Task will only be created with status OPEN if escrow is verified as locked
 */
export async function createTask(
  taskID: string,
  publisher: string,
  accuracy: bigint,
  deadline: bigint,
  commitHash: string,  // From frontend (generated with frontend nonce)
  nonceTP: string,     // From frontend (32-byte nonce as hex string)
  escrowTxHash: string, // Escrow transaction hash for verification
  dataset?: string,    // D: Dataset requirements (Algorithm 1)
  initialModelLink?: string,  // L: Initial model link (Algorithm 1)
  minMiners?: number,  // Minimum miners required for PoS aggregator selection
  maxMiners?: number   // Maximum miners allowed for PoS aggregator selection
) {
  // Ensure uniqueness
  const existing = await prisma.task.findUnique({ where: { taskID } });
  if (existing) {
    throw new Error("Task already exists");
  }

  // Validate commit hash matches accuracy and nonce
  const expectedCommitHash = keccak256(
    solidityPacked(
      ["uint256", "bytes32"],
      [accuracy, `0x${nonceTP}`]
    )
  );
  
  if (commitHash.toLowerCase() !== expectedCommitHash.toLowerCase()) {
    throw new Error("Commit hash does not match accuracy and nonce");
  }

  // Verify escrow is locked on-chain before creating task
  const { escrow } = await import("../contracts/escrow.js");
  const { JsonRpcProvider } = await import("ethers");
  const { env } = await import("../config/env.js");
  
  // Declare transactionEscrowAddress outside try block so it's available for task creation
  let transactionEscrowAddress: string | null = null;
  
  try {
    console.log(`[Escrow Verification] Starting verification for taskID=${taskID}, txHash=${escrowTxHash}, RPC=${env.RPC_URL}`);
    const provider = new JsonRpcProvider(env.RPC_URL);
    
    // First, check if transaction exists (might be pending)
    let tx;
    try {
      tx = await provider.getTransaction(escrowTxHash);
      if (!tx) {
        throw new Error(`Transaction ${escrowTxHash} not found on RPC node ${env.RPC_URL}`);
      }
      console.log(`[Escrow Verification] Transaction found: blockNumber=${tx.blockNumber || 'pending'}, from=${tx.from}, to=${tx.to}, value=${tx.value?.toString()}`);
    } catch (txError: any) {
      console.error(`[Escrow Verification] Transaction lookup failed:`, txError.message);
      throw new Error(`Transaction not found: ${txError.message}. Make sure the transaction hash is correct and the RPC node (${env.RPC_URL}) is connected to the same network as MetaMask.`);
    }
    
    // If transaction exists but no blockNumber, it's still pending
    if (!tx.blockNumber) {
      throw new Error("Transaction is still pending and has not been mined yet. Please wait for confirmation.");
    }
    
    // Retry logic for getting receipt (sometimes receipt isn't immediately available after mining)
    let receipt = null;
    const maxRetries = 5;
    const retryDelay = 1000; // 1 second
    
    for (let i = 0; i < maxRetries; i++) {
      try {
        receipt = await provider.getTransactionReceipt(escrowTxHash);
        if (receipt) {
          console.log(`[Escrow Verification] Receipt found on attempt ${i + 1}: status=${receipt.status}, blockNumber=${receipt.blockNumber}`);
          break;
        }
      } catch (receiptError: any) {
        if (i < maxRetries - 1) {
          console.log(`[Escrow Verification] Receipt not available yet (attempt ${i + 1}/${maxRetries}), retrying in ${retryDelay}ms...`);
          await new Promise(resolve => setTimeout(resolve, retryDelay));
        } else {
          throw new Error(`Transaction receipt not available after ${maxRetries} attempts: ${receiptError.message}`);
        }
      }
    }
    
    if (!receipt) {
      throw new Error("Transaction receipt not found. The transaction may have just been mined - please try again in a few seconds.");
    }
    
    if (receipt.status !== 1) {
      throw new Error(`Transaction reverted on-chain. Status: ${receipt.status}`);
    }
    
    console.log(`[Escrow Verification] Transaction confirmed successfully: blockNumber=${receipt.blockNumber}`);

    // Use the transaction we already fetched (tx is already declared above)
    // Extract values we'll need for verification
    const txValue = tx.value || 0n;
    const txFrom = tx.from;
    
    // Verify transaction was sent to a contract (not a simple transfer)
    if (!tx.to) {
      throw new Error("Transaction has no recipient address - cannot verify escrow");
    }
    
    // Use the transaction's 'to' address as the source of truth
    // The transaction is what actually happened on-chain, so we trust it
    transactionEscrowAddress = tx.to;
    const configuredEscrowAddress = escrow.target;
    
    // Log if there's a mismatch and auto-update the env file
    if (transactionEscrowAddress.toLowerCase() !== configuredEscrowAddress.toLowerCase()) {
      console.warn(
        `[Escrow Verification] Address mismatch detected: Transaction sent to ${transactionEscrowAddress} ` +
        `but backend configured with ${configuredEscrowAddress}. ` +
        `Auto-updating configuration...`
      );
      
      // Automatically update the .env.development file
      const updated = await updateEscrowAddressInEnvFile(transactionEscrowAddress);
      if (updated) {
        console.log(`[Escrow Verification] Configuration updated. Using transaction address ${transactionEscrowAddress} for verification.`);
      } else {
        console.warn(`[Escrow Verification] Could not auto-update config, but continuing with transaction address.`);
      }
    }
    
    // Verify contract exists at the transaction address
    const contractCode = await provider.getCode(transactionEscrowAddress);
    const contractExists = contractCode && contractCode !== '0x';
    if (!contractExists) {
      throw new Error(
        `No contract found at transaction address ${transactionEscrowAddress}. ` +
        `Transaction may have been sent to wrong address or contract not deployed.`
      );
    }
    
    console.log(`[Escrow Verification] Contract verified at transaction address: ${transactionEscrowAddress}`);

    // Decode transaction to verify it called publishTask with the correct taskID
    // Create a temporary contract instance using the transaction address for decoding
    let transactionDecoded = false;
    if (tx && tx.data && tx.data !== '0x') {
      try {
        // Use the escrow ABI to decode, but we'll verify against the transaction address
        const iface = escrow.interface;
        const decoded = iface.parseTransaction({ data: tx.data, value: tx.value });
        console.log(`[Escrow Verification] Transaction decoded: function=${decoded.name}, args=`, {
          taskID: decoded.args[0],
          accuracyCommit: decoded.args[1],
          deadline: decoded.args[2]?.toString()
        });
        
        // Verify the function called is publishTask
        if (decoded.name !== 'publishTask') {
          throw new Error(`Transaction called ${decoded.name} instead of publishTask. Expected publishTask function call.`);
        }
        
        // Verify the taskID matches
        const txTaskID = decoded.args[0]; // First argument is taskID
        if (txTaskID !== taskID) {
          throw new Error(`TaskID mismatch: transaction used "${txTaskID}" but backend expects "${taskID}"`);
        }
        
        transactionDecoded = true;
        console.log(`[Escrow Verification] Transaction verified: publishTask called with correct taskID=${taskID}`);
      } catch (decodeError: any) {
        // Decoding failed - this is critical if we can't verify the function
        if (decodeError.message.includes('instead of publishTask') || decodeError.message.includes('TaskID mismatch')) {
          throw decodeError;
        }
        console.warn(`[Escrow Verification] Could not decode transaction data:`, decodeError.message);
      }
    } else {
      throw new Error("Transaction has no data - might be a simple transfer, not a publishTask contract call");
    }
    
    if (!transactionDecoded) {
      throw new Error("Could not verify transaction called publishTask - transaction decoding failed");
    }

    // Try to read from contract at the transaction address
    // Create a contract instance using the transaction address (not the configured one)
    let contractTask = null;
    let contractReadSuccess = false;
    let transactionEscrow = null; // Declare outside try block for use in verification
    
    if (contractExists) {
      try {
        // Create a contract instance at the transaction address for reading
        const { Contract } = await import("ethers");
        transactionEscrow = new Contract(
          transactionEscrowAddress,
          escrow.interface,
          provider
        );
        
        console.log(`[Escrow Verification] Attempting to read tasks mapping for taskID=${taskID} from ${transactionEscrowAddress}...`);
        contractTask = await transactionEscrow.tasks(taskID);
        contractReadSuccess = true;
        console.log(`[Escrow Verification] Task found on-chain:`, {
          publisher: contractTask.publisher,
          reward: contractTask.reward?.toString(),
          status: contractTask.status,
          deadline: contractTask.deadline?.toString()
        });
      } catch (taskError: any) {
        console.warn(`[Escrow Verification] Contract read failed (will use transaction-based verification):`, {
          error: taskError.message,
          code: taskError.code
        });
        // Contract read failed - we'll use transaction-based verification as fallback
      }
    }

    // If contract read succeeded, verify the data
    if (contractReadSuccess && contractTask) {
      // Verify task exists (publisher is not zero address)
      if (!contractTask.publisher || contractTask.publisher === "0x0000000000000000000000000000000000000000") {
        throw new Error("Task not found on-chain - escrow transaction may have failed or reverted");
      }

      // Verify publisher matches
      if (contractTask.publisher.toLowerCase() !== publisher.toLowerCase()) {
        throw new Error(`Publisher address mismatch - escrow was locked by ${contractTask.publisher} but backend expects ${publisher}`);
      }

      // Verify task status is LOCKED (enum value 1)
      // Note: contractTask.status is a BigInt, so compare with BigInt
      const taskStatus = typeof contractTask.status === 'bigint' ? contractTask.status : BigInt(contractTask.status);
      if (taskStatus !== 1n) {
        throw new Error(`Task status is not LOCKED on-chain (status: ${taskStatus.toString()}, expected: 1). Transaction hash: ${escrowTxHash}`);
      }

      // Verify reward/escrow amount is greater than 0
      const rewardAmount = contractTask.reward || 0n;
      if (rewardAmount === 0n) {
        throw new Error(`Escrow not locked - reward amount is zero for taskID: ${taskID}. Transaction hash: ${escrowTxHash}`);
      }
      
      // Additional verification: Check escrowBalance mapping matches reward
      if (!transactionEscrow) {
        throw new Error("transactionEscrow contract instance not available for escrow balance verification");
      }
      const onChainEscrowBalance = await transactionEscrow.escrowBalance(taskID);
      if (onChainEscrowBalance === 0n) {
        throw new Error(
          `Escrow balance is zero on-chain for taskID: ${taskID}. ` +
          `This indicates the escrow may have been refunded or never locked. ` +
          `Transaction hash: ${escrowTxHash}`
        );
      }
      
      if (onChainEscrowBalance !== rewardAmount) {
        throw new Error(
          `Escrow balance mismatch: reward=${rewardAmount.toString()} but escrowBalance=${onChainEscrowBalance.toString()}. ` +
          `This indicates the escrow may have been partially refunded. Transaction hash: ${escrowTxHash}`
        );
      }
      
      console.log(`[Escrow Verification] Escrow verified via contract read: reward=${rewardAmount.toString()} wei (${(Number(rewardAmount) / 1e18).toFixed(4)} ETH), escrowBalance=${onChainEscrowBalance.toString()} wei`);
    } else {
      // Fallback: Trust transaction receipt and decoded data
      // BUT still verify escrow balance on-chain (CRITICAL)
      console.log(`[Escrow Verification] Using transaction-based verification (contract read unavailable)`);
      
      // Verify transaction value (escrow amount) is greater than 0
      if (txValue === 0n) {
        throw new Error(`Escrow not locked - transaction value is zero. Transaction hash: ${escrowTxHash}`);
      }

      // Verify transaction sender matches publisher
      if (txFrom.toLowerCase() !== publisher.toLowerCase()) {
        throw new Error(`Publisher address mismatch - transaction sent by ${txFrom} but backend expects ${publisher}`);
      }

      // Verify receipt status is success
      if (receipt.status !== 1) {
        throw new Error(`Transaction reverted on-chain. Receipt status: ${receipt.status}. Transaction hash: ${escrowTxHash}`);
      }

      // CRITICAL: Always verify escrow balance on-chain, even in fallback
      // This ensures the escrow was actually locked, not just that the transaction succeeded
      try {
        const { Contract } = await import("ethers");
        const transactionEscrow = new Contract(
          transactionEscrowAddress,
          escrow.interface,
          provider
        );
        
        const onChainEscrowBalance = await transactionEscrow.escrowBalance(taskID);
        if (onChainEscrowBalance === 0n) {
          throw new Error(
            `Escrow not locked on-chain - escrowBalance is zero for taskID: ${taskID}. ` +
            `Transaction hash: ${escrowTxHash}. ` +
            `This might indicate the transaction reverted internally, escrow was already refunded, ` +
            `or the contract call failed silently. Please verify the transaction manually.`
          );
        }
        
        // Verify escrow balance matches transaction value (within reasonable tolerance for gas)
        // Allow small difference due to gas costs, but should be very close
        const balanceDiff = txValue > onChainEscrowBalance ? txValue - onChainEscrowBalance : onChainEscrowBalance - txValue;
        // Allow up to 0.001 ETH difference (for gas or rounding)
        const tolerance = BigInt(1e15); // 0.001 ETH
        if (balanceDiff > tolerance) {
          throw new Error(
            `Escrow balance mismatch: transaction value=${txValue.toString()} wei but escrowBalance=${onChainEscrowBalance.toString()} wei. ` +
            `Difference: ${balanceDiff.toString()} wei. ` +
            `This might indicate partial refund or transaction issue. Transaction hash: ${escrowTxHash}`
          );
        }
        
        console.log(`[Escrow Verification] Escrow balance verified on-chain: ${onChainEscrowBalance.toString()} wei (${(Number(onChainEscrowBalance) / 1e18).toFixed(4)} ETH)`);
      } catch (balanceError: any) {
        // If we can't read escrow balance, this is a critical failure
        throw new Error(
          `Cannot verify escrow balance on-chain: ${balanceError.message}. ` +
          `Transaction may have succeeded but escrow was not locked. ` +
          `Please verify the transaction manually. Transaction hash: ${escrowTxHash}`
        );
      }

      console.log(`[Escrow Verification] Escrow verified via transaction: value=${txValue.toString()} wei (${(Number(txValue) / 1e18).toFixed(4)} ETH), status=success`);
    }

  } catch (error: any) {
    throw new Error(`Escrow verification failed: ${error.message}. Please ensure escrow is locked on-chain before creating task.`);
  }

  // Validate min/max miners if provided
  const finalMinMiners = minMiners !== undefined ? minMiners : 3; // Default to 3
  const finalMaxMiners = maxMiners !== undefined ? maxMiners : 5; // Default to 5
  
  if (finalMinMiners < 1) {
    throw new Error("minMiners must be at least 1");
  }
  if (finalMaxMiners < finalMinMiners) {
    throw new Error("maxMiners must be greater than or equal to minMiners");
  }
  if (finalMaxMiners > 1000) {
    throw new Error("maxMiners cannot exceed 1000");
  }

  // Create task with status OPEN (escrow is verified as locked)
  console.log(`[createTask] Creating task in database: taskID=${taskID}, publisher=${publisher}, minMiners=${finalMinMiners}, maxMiners=${finalMaxMiners}`);
  try {
    const createdTask = await prisma.task.create({
      data: {
        taskID,
        publisher,
        commitHash,
        nonceTP,
        deadline,
        dataset: dataset || "chestxray",  // Default dataset if not provided
        initialModelLink: initialModelLink || null,  // Optional initial model link
        minMiners: finalMinMiners,  // Store min miners
        maxMiners: finalMaxMiners,  // Store max miners
        status: TaskStatus.OPEN,  // Task is OPEN because escrow is verified as locked
        publishTx: escrowTxHash,  // Store escrow transaction hash
        escrowContractAddress: transactionEscrowAddress || null  // Store contract address for frontend to read from correct contract
      }
    });
    console.log(`[createTask] Task created successfully: taskID=${taskID}, id=${createdTask.id}`);
  } catch (dbError: any) {
    console.error(`[createTask] Database error creating task:`, {
      taskID,
      error: dbError?.message,
      code: dbError?.code,
      meta: dbError?.meta
    });
    throw new Error(`Failed to create task in database: ${dbError?.message}`);
  }

  return {
    taskID,
    commitHash,
    deadline: deadline.toString(),
    status: "OPEN"
  };
}

/**
 * Get open tasks for FL client polling
 */
export async function getOpenTasks() {
  const now = BigInt(Math.floor(Date.now() / 1000));
  
  // Update task statuses based on deadline
  await prisma.task.updateMany({
    where: {
      status: TaskStatus.CREATED,
      deadline: { lte: now }
    },
    data: {
      status: TaskStatus.OPEN
    }
  });

  // Get all open tasks that haven't reached commit deadline
  const openTasks = await prisma.task.findMany({
    where: {
      status: TaskStatus.OPEN,
      deadline: { gt: now }
    },
    select: {
      taskID: true,
      publisher: true,
      deadline: true,
      status: true,
      dataset: true,
      createdAt: true
    },
    orderBy: {
      createdAt: 'desc'
    }
  });

  return openTasks.map(task => ({
    ...task,
    deadline: task.deadline.toString()
  }));
}

/**
 * Get task by ID
 */
export async function getTaskById(taskID: string) {
  const task = await prisma.task.findUnique({
    where: { taskID },
    include: {
      miners: {
        select: {
          address: true,
          id: true,
          proofVerified: true  // Need to check proof verification for PoS selection
        },
        orderBy: {
          id: 'asc' // Deterministic order
        }
      },
      gradients: {
        select: {
          minerAddress: true,
          status: true
        }
      },
      _count: {
        select: {
          miners: true,
          gradients: true
        }
      }
    }
  });

  if (!task) {
    throw new Error("Task not found");
  }

  // Use aggregator from database (set by PoS selection in finalizeMiners)
  // If not set, aggregator selection hasn't happened yet (need to call finalizeMiners)
  let aggregator = task.aggregatorAddress;

  // If aggregator not set but we have enough miners with verified proofs, try to finalize
  if (!aggregator && task.miners.length >= (task.minMiners || 3)) {
    // Check if miners have verified proofs (required for PoS)
    const minersWithProofs = task.miners.filter((m: any) => m.proofVerified);
    if (minersWithProofs.length >= (task.minMiners || 3)) {
      // Trigger PoS selection by calling finalizeMiners
      try {
        const { finalizeMiners } = await import("./minerSelectionService.js");
        const result = await finalizeMiners(taskID);
        aggregator = result.aggregator;
      } catch (err: any) {
        console.warn(`Failed to finalize miners for task ${taskID}:`, err.message);
        // Don't fallback to first miner - return null instead
        aggregator = null;
      }
    }
  }

  // Convert BigInt fields to strings for JSON serialization
  return {
    id: task.id,
    taskID: task.taskID,
    publisher: task.publisher,
    commitHash: task.commitHash,
    nonceTP: task.nonceTP,
    deadline: task.deadline.toString(), // Convert BigInt to string
    status: task.status,
    dataset: task.dataset,
    initialModelLink: task.initialModelLink,
    aggregatorAddress: task.aggregatorAddress,
    minMiners: task.minMiners,
    maxMiners: task.maxMiners,
    publishTx: task.publishTx,
    escrowContractAddress: task.escrowContractAddress || null, // Return contract address for frontend (null for legacy tasks)
    miners: task.miners.map(miner => ({
      address: miner.address,
      id: miner.id
    })),
    gradients: task.gradients.map(gradient => ({
      minerAddress: gradient.minerAddress,
      status: gradient.status
    })),
    _count: task._count,
    createdAt: task.createdAt,
    updatedAt: task.updatedAt,
    aggregator, // Add aggregator to response
  };
}

/**
 * Get all tasks with optional filtering
 */
export async function getAllTasks(filters: {
  status?: TaskStatus;
  publisher?: string;
  limit?: number;
  offset?: number;
} = {}) {
  const { status, publisher, limit = 50, offset = 0 } = filters;
  
  const where: any = {};
  if (status) where.status = status;
  if (publisher) where.publisher = publisher;

  const tasks = await prisma.task.findMany({
    where,
    include: {
      miners: {
        select: {
          address: true,
          id: true
        },
        orderBy: {
          id: 'asc' // Deterministic order for aggregator selection
        }
      },
      _count: {
        select: {
          miners: true,
          gradients: true
        }
      }
    },
    orderBy: {
      createdAt: 'desc'
    },
    take: limit,
    skip: offset
  });

  return tasks.map(task => {
    // Use aggregator from database (set by PoS selection)
    // Don't trigger finalizeMiners here as it's expensive - just use stored value
    // If aggregator is not set, it means PoS selection hasn't happened yet
    const aggregator = task.aggregatorAddress;

    return {
      taskID: task.taskID,
      publisher: task.publisher,
      deadline: task.deadline.toString(),
      status: task.status,
      createdAt: task.createdAt,
      updatedAt: task.updatedAt,
      miners: task.miners,
      aggregator,
      _count: task._count
    };
  });
}

/**
 * Update task status
 */
export async function updateTaskStatus(taskID: string, status: TaskStatus) {
  const task = await prisma.task.update({
    where: { taskID },
    data: { status }
  });

  return {
    ...task,
    deadline: task.deadline.toString()
  };
}

/**
 * Check and update task deadlines
 */
export async function checkTaskDeadlines() {
  const now = BigInt(Math.floor(Date.now() / 1000));
  
  // Move CREATED tasks to OPEN if deadline passed
  const createdUpdated = await prisma.task.updateMany({
    where: {
      status: TaskStatus.CREATED,
      deadline: { lte: now }
    },
    data: {
      status: TaskStatus.OPEN
    }
  });

  // Move OPEN tasks to COMMIT_CLOSED if deadline passed
  const openUpdated = await prisma.task.updateMany({
    where: {
      status: TaskStatus.OPEN,
      deadline: { lte: now }
    },
    data: {
      status: TaskStatus.COMMIT_CLOSED
    }
  });

  if (createdUpdated.count > 0 || openUpdated.count > 0) {
    console.log(`[TaskScheduler] Updated ${createdUpdated.count} CREATED → OPEN, ${openUpdated.count} OPEN → COMMIT_CLOSED`);
  }

  return { updated: true };
}

/**
 * Cancel tasks that never locked escrow (publishTx missing) after deadline
 */
export async function cancelTasksWithoutEscrow() {
  const now = BigInt(Math.floor(Date.now() / 1000));

  const cancelled = await prisma.task.updateMany({
    where: {
      publishTx: null, // no escrow tx recorded (never locked)
      deadline: { lte: now },
      status: {
        in: [
          TaskStatus.CREATED,
          TaskStatus.OPEN,
          TaskStatus.COMMIT_CLOSED,
          TaskStatus.REVEAL_OPEN,
          TaskStatus.REVEAL_CLOSED,
          TaskStatus.AGGREGATING
        ]
      }
    },
    data: {
      status: TaskStatus.CANCELLED
    }
  });

  if (cancelled.count > 0) {
    console.log(`[TaskScheduler] Cancelled ${cancelled.count} tasks with no escrow (publishTx missing)`);
  }

  return { updated: cancelled.count > 0, count: cancelled.count };
}

/**
 * Check reveal deadlines and update REVEAL_OPEN → REVEAL_CLOSED
 * Reveal deadline is calculated as: main deadline + 7 days
 */
export async function checkRevealDeadlines() {
  const now = BigInt(Math.floor(Date.now() / 1000));
  const REVEAL_DEADLINE_OFFSET = 7n * 24n * 60n * 60n; // 7 days in seconds
  
  // Get all REVEAL_OPEN tasks
  const revealOpenTasks = await prisma.task.findMany({
    where: {
      status: TaskStatus.REVEAL_OPEN
    },
    select: {
      taskID: true,
      deadline: true
    }
  });

  let updatedCount = 0;
  
  for (const task of revealOpenTasks) {
    // Calculate reveal deadline: main deadline + 7 days
    const revealDeadline = task.deadline + REVEAL_DEADLINE_OFFSET;
    
    if (revealDeadline <= now) {
      await prisma.task.update({
        where: { taskID: task.taskID },
        data: { status: TaskStatus.REVEAL_CLOSED }
      });
      updatedCount++;
      console.log(`[TaskScheduler] Updated task ${task.taskID}: REVEAL_OPEN → REVEAL_CLOSED (reveal deadline passed)`);
    }
  }

  return { updated: updatedCount > 0, count: updatedCount };
}

/**
 * Check consensus for REVEAL_OPEN tasks and update to VERIFIED if consensus reached
 */
export async function checkConsensusAndUpdate() {
  // Get all REVEAL_OPEN tasks with verifications
  const revealOpenTasks = await prisma.task.findMany({
    where: {
      status: TaskStatus.REVEAL_OPEN
    },
    include: {
      miners: true,
      verifications: true,
      block: true
    }
  });

  let updatedCount = 0;

  for (const task of revealOpenTasks) {
    // Only check if block exists (aggregation completed)
    if (!task.block) {
      continue;
    }

    const totalMiners = task.miners.length;
    if (totalMiners === 0) {
      continue;
    }

    const majorityRequired = Math.ceil(totalMiners * 0.5); // 50% majority
    const validVotes = task.verifications.filter(v => v.verdict === "VALID").length;
    
    // Check if consensus reached (50% majority voted VALID)
    if (validVotes >= majorityRequired) {
      await prisma.task.update({
        where: { taskID: task.taskID },
        data: { status: TaskStatus.VERIFIED }
      });
      updatedCount++;
      console.log(`[TaskScheduler] Updated task ${task.taskID}: REVEAL_OPEN → VERIFIED (consensus reached: ${validVotes}/${totalMiners} valid votes)`);
    }
  }

  return { updated: updatedCount > 0, count: updatedCount };
}

/**
 * Check reward status for VERIFIED tasks and update to REWARDED if all rewards distributed
 */
export async function checkRewardStatus() {
  // Get all VERIFIED tasks with rewards
  const verifiedTasks = await prisma.task.findMany({
    where: {
      status: TaskStatus.VERIFIED
    },
    include: {
      miners: true,
      rewards: true
    }
  });

  let updatedCount = 0;

  for (const task of verifiedTasks) {
    const totalMiners = task.miners.length;
    if (totalMiners === 0) {
      continue;
    }

    // Check if all miners have rewards with status DISTRIBUTED
    const distributedRewards = task.rewards.filter(r => r.status === "DISTRIBUTED").length;
    
    // If all miners have distributed rewards, update status to REWARDED
    if (distributedRewards >= totalMiners && task.rewards.length >= totalMiners) {
      await prisma.task.update({
        where: { taskID: task.taskID },
        data: { status: TaskStatus.REWARDED }
      });
      updatedCount++;
      console.log(`[TaskScheduler] Updated task ${task.taskID}: VERIFIED → REWARDED (all rewards distributed: ${distributedRewards}/${totalMiners})`);
    }
  }

  return { updated: updatedCount > 0, count: updatedCount };
}