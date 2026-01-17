/**
 * Complete task escrow transaction
 * Utility script to complete escrow for tasks where escrow wasn't locked on-chain
 * 
 * Usage:
 *   node scripts/complete_task_escrow.js <taskID> [rewardETH]
 * 
 * Example:
 *   node scripts/complete_task_escrow.js task_009 0.1
 * 
 * Environment variables required:
 *   - RPC_URL: RPC endpoint URL
 *   - ESCROW_ADDRESS: Escrow contract address
 *   - PRIVATE_KEY: Private key of the publisher wallet (with 0x prefix)
 */

import { PrismaClient } from '@prisma/client';
import { Contract, JsonRpcProvider, Wallet } from 'ethers';
import escrowArtifact from '../../contracts/artifacts/src/HealChainEscrow.sol/HealChainEscrow.json' with { type: 'json' };
import dotenv from 'dotenv';

dotenv.config();

const prisma = new PrismaClient();

const RPC_URL = process.env.RPC_URL || 'http://localhost:8545';
const ESCROW_ADDRESS = process.env.ESCROW_ADDRESS;
const PRIVATE_KEY = process.env.PRIVATE_KEY;

if (!ESCROW_ADDRESS) {
  console.error('❌ ESCROW_ADDRESS not set in environment');
  process.exit(1);
}

if (!PRIVATE_KEY) {
  console.error('❌ PRIVATE_KEY not set in environment');
  console.error('   This script requires the publisher\'s private key to send the transaction.');
  process.exit(1);
}

async function completeTaskEscrow(taskID, rewardETH) {
  try {
    console.log(`\nCompleting escrow for task: ${taskID}`);
    console.log('='.repeat(60));

    // Check backend
    const task = await prisma.task.findUnique({
      where: { taskID },
    });

    if (!task) {
      console.error('❌ Task not found in backend');
      process.exit(1);
    }

    console.log('\n✅ Task found in backend:');
    console.log(`   Task ID: ${task.taskID}`);
    console.log(`   Publisher: ${task.publisher}`);
    console.log(`   Status: ${task.status}`);
    console.log(`   Deadline: ${new Date(Number(task.deadline) * 1000).toLocaleString()}`);
    console.log(`   Commit Hash: ${task.commitHash || 'N/A'}`);

    // Get reward amount
    let rewardAmount = rewardETH;
    if (!rewardAmount) {
      // Try to get from task data
      if (task.rewardAmount) {
        rewardAmount = task.rewardAmount.toString();
        console.log(`\n📝 Using reward amount from task: ${rewardAmount} ETH`);
      } else {
        console.error('❌ Reward amount not provided and not found in task data');
        console.error('   Please provide reward amount as second argument:');
        console.error(`   node scripts/complete_task_escrow.js ${taskID} <rewardETH>`);
        process.exit(1);
      }
    }

    // Validate commitHash and deadline
    if (!task.commitHash) {
      console.error('❌ Task missing commitHash. Cannot complete escrow.');
      process.exit(1);
    }

    if (!task.deadline) {
      console.error('❌ Task missing deadline. Cannot complete escrow.');
      process.exit(1);
    }

    // Check on-chain status first
    const provider = new JsonRpcProvider(RPC_URL);
    const escrowContract = new Contract(ESCROW_ADDRESS, escrowArtifact.abi, provider);

    try {
      const escrowBalance = await escrowContract.escrowBalance(taskID);
      const contractTask = await escrowContract.tasks(taskID);

      if (contractTask.publisher !== '0x0000000000000000000000000000000000000000') {
        console.log('\n⚠️  Task already exists on-chain:');
        console.log(`   Escrow Balance: ${escrowBalance.toString()} Wei`);
        console.log(`   Publisher: ${contractTask.publisher}`);
        
        if (escrowBalance.toString() !== '0') {
          console.log('\n✅ Escrow is already locked. No action needed.');
          await prisma.$disconnect();
          process.exit(0);
        }
      }
    } catch (error) {
      console.log('\n⚠️  Could not check on-chain status (this is okay if task doesn\'t exist yet)');
      console.log(`   ${error.message}`);
    }

    // Connect wallet
    const wallet = new Wallet(PRIVATE_KEY, provider);
    const walletAddress = await wallet.getAddress();

    console.log(`\n🔐 Using wallet: ${walletAddress}`);

    // Verify wallet is the publisher
    if (walletAddress.toLowerCase() !== task.publisher.toLowerCase()) {
      console.error(`\n❌ Wallet address (${walletAddress}) does not match task publisher (${task.publisher})`);
      console.error('   This script must be run with the publisher\'s private key.');
      process.exit(1);
    }

    // Check wallet balance
    const balance = await provider.getBalance(walletAddress);
    const requiredAmount = BigInt(Math.floor(parseFloat(rewardAmount) * 1e18));
    
    console.log(`\n💰 Wallet balance: ${balance.toString()} Wei (${(Number(balance) / 1e18).toFixed(6)} ETH)`);
    console.log(`   Required: ${requiredAmount.toString()} Wei (${rewardAmount} ETH)`);

    if (balance < requiredAmount) {
      console.error(`\n❌ Insufficient balance. Need ${rewardAmount} ETH but have ${(Number(balance) / 1e18).toFixed(6)} ETH`);
      process.exit(1);
    }

    // Prepare transaction
    const escrowContractWithSigner = escrowContract.connect(wallet);
    const deadline = BigInt(task.deadline);
    const commitHash = task.commitHash;

    console.log('\n📝 Transaction details:');
    console.log(`   Task ID: ${taskID}`);
    console.log(`   Commit Hash: ${commitHash}`);
    console.log(`   Deadline: ${deadline.toString()} (${new Date(Number(deadline) * 1000).toLocaleString()})`);
    console.log(`   Reward: ${rewardAmount} ETH`);

    // Send transaction
    console.log('\n⏳ Sending transaction...');
    const tx = await escrowContractWithSigner.publishTask(
      taskID,
      commitHash,
      deadline,
      { value: requiredAmount }
    );

    console.log(`\n✅ Transaction sent!`);
    console.log(`   Transaction hash: ${tx.hash}`);
    console.log(`   Waiting for confirmation...`);

    // Wait for confirmation
    const receipt = await tx.wait();

    if (receipt.status === 1) {
      console.log(`\n✅ Transaction confirmed!`);
      console.log(`   Block number: ${receipt.blockNumber}`);
      console.log(`   Gas used: ${receipt.gasUsed.toString()}`);
      
      // Verify escrow is now locked
      const newEscrowBalance = await escrowContract.escrowBalance(taskID);
      console.log(`\n✅ Escrow locked successfully!`);
      console.log(`   Escrow balance: ${newEscrowBalance.toString()} Wei (${(Number(newEscrowBalance) / 1e18).toFixed(6)} ETH)`);
      
      console.log('\n🎉 Task escrow completed successfully!');
      console.log('   The task is now open for miner registration.');
    } else {
      console.error('\n❌ Transaction failed (status: 0)');
      process.exit(1);
    }

  } catch (error) {
    console.error('\n❌ Error completing escrow:');
    console.error(`   ${error.message}`);
    
    if (error.reason) {
      console.error(`   Reason: ${error.reason}`);
    }
    
    if (error.data) {
      console.error(`   Data: ${JSON.stringify(error.data)}`);
    }

    console.error('\n💡 Common issues:');
    console.error('   1. Task already exists on-chain (check with check_task_escrow.js)');
    console.error('   2. Insufficient balance in wallet');
    console.error('   3. Invalid deadline (must be in the future)');
    console.error('   4. Network/RPC issues');
    console.error('   5. Contract address incorrect');
    
    process.exit(1);
  } finally {
    await prisma.$disconnect();
  }
}

// Parse command line arguments
const taskID = process.argv[2];
const rewardETH = process.argv[3];

if (!taskID) {
  console.error('Usage: node scripts/complete_task_escrow.js <taskID> [rewardETH]');
  console.error('Example: node scripts/complete_task_escrow.js task_009 0.1');
  process.exit(1);
}

completeTaskEscrow(taskID, rewardETH);

