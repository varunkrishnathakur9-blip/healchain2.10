/**
 * Check task escrow status
 * Verifies if task exists in backend and if escrow is locked on-chain
 */

import { PrismaClient } from '@prisma/client';
import { Contract, JsonRpcProvider } from 'ethers';
import escrowArtifact from '../../contracts/artifacts/src/HealChainEscrow.sol/HealChainEscrow.json' with { type: 'json' };
import dotenv from 'dotenv';

dotenv.config();

const prisma = new PrismaClient();

const RPC_URL = process.env.RPC_URL || 'http://localhost:8545';
const ESCROW_ADDRESS = process.env.ESCROW_ADDRESS;

if (!ESCROW_ADDRESS) {
  console.error('ESCROW_ADDRESS not set in environment');
  process.exit(1);
}

async function checkTaskEscrow(taskID) {
  try {
    console.log(`\nChecking task: ${taskID}`);
    console.log('='.repeat(60));

    // Check backend
    const task = await prisma.task.findUnique({
      where: { taskID },
      include: {
        miners: {
          select: {
            address: true,
            proofVerified: true
          }
        }
      }
    });

    if (!task) {
      console.log('❌ Task not found in backend');
      return;
    }

    console.log('\n✅ Backend Status:');
    console.log(`   Task ID: ${task.taskID}`);
    console.log(`   Publisher: ${task.publisher}`);
    console.log(`   Status: ${task.status}`);
    console.log(`   Deadline: ${new Date(Number(task.deadline) * 1000).toLocaleString()}`);
    console.log(`   Miners Registered: ${task.miners.length}`);
    console.log(`   Verified Miners: ${task.miners.filter(m => m.proofVerified).length}`);

    // Check on-chain
    const provider = new JsonRpcProvider(RPC_URL);
    const escrowContract = new Contract(ESCROW_ADDRESS, escrowArtifact.abi, provider);

    try {
      const escrowBalance = await escrowContract.escrowBalance(taskID);
      const contractTask = await escrowContract.tasks(taskID);

      console.log('\n✅ On-Chain Status:');
      console.log(`   Escrow Balance: ${escrowBalance.toString()} Wei (${(Number(escrowBalance) / 1e18).toFixed(6)} ETH)`);
      
      if (contractTask.publisher === '0x0000000000000000000000000000000000000000') {
        console.log('   Task Status: ❌ NOT FOUND ON-CHAIN');
        console.log('\n⚠️  ISSUE: Task exists in backend but escrow was not locked on-chain');
        console.log('\n💡 Solution:');
        console.log('   1. The publisher needs to complete the escrow transaction');
        console.log('   2. Go to the task detail page and look for "Complete Escrow" button');
        console.log('   3. Or delete the task from backend and publish again');
        console.log('\n   Note: The escrow transaction (publishTask) was not completed.');
        console.log('   This happens when:');
        console.log('   - Transaction was rejected in wallet');
        console.log('   - Insufficient balance');
        console.log('   - Transaction failed for another reason');
      } else {
        console.log(`   Task Status: ✅ LOCKED`);
        console.log(`   Publisher: ${contractTask.publisher}`);
        console.log(`   Reward: ${contractTask.reward.toString()} Wei (${(Number(contractTask.reward) / 1e18).toFixed(6)} ETH)`);
        
        if (escrowBalance.toString() === '0') {
          console.log('\n⚠️  WARNING: Escrow balance is 0 but task exists on-chain');
          console.log('   This might indicate the escrow was already released or refunded');
        } else if (escrowBalance.toString() !== contractTask.reward.toString()) {
          console.log('\n⚠️  WARNING: Escrow balance does not match reward amount');
          console.log(`   Escrow: ${escrowBalance.toString()}`);
          console.log(`   Reward: ${contractTask.reward.toString()}`);
        } else {
          console.log('\n✅ Escrow is properly locked on-chain');
        }
      }
    } catch (error) {
      console.log('\n❌ Error checking on-chain status:');
      console.log(`   ${error.message}`);
      console.log('\n   Possible causes:');
      console.log('   - Contract not deployed at', ESCROW_ADDRESS);
      console.log('   - RPC URL not accessible:', RPC_URL);
      console.log('   - Network mismatch');
    }

  } catch (error) {
    console.error('Error:', error);
  } finally {
    await prisma.$disconnect();
  }
}

const taskID = process.argv[2] || 'task_009';

checkTaskEscrow(taskID);

