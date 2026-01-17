/**
 * Verify contract deployment and check if it has the expected functions
 * 
 * Usage:
 *   node scripts/verify_contract.js <contractAddress> [taskID]
 * 
 * Example:
 *   node scripts/verify_contract.js 0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512 task_009
 */

import { Contract, JsonRpcProvider } from 'ethers';
import escrowArtifact from '../../contracts/artifacts/src/HealChainEscrow.sol/HealChainEscrow.json' with { type: 'json' };
import dotenv from 'dotenv';

dotenv.config();

const RPC_URL = process.env.RPC_URL || 'http://localhost:8545';
const contractAddress = process.argv[2];
const taskID = process.argv[3];

if (!contractAddress) {
  console.error('Usage: node scripts/verify_contract.js <contractAddress> [taskID]');
  process.exit(1);
}

async function verifyContract() {
  try {
    console.log(`\nVerifying contract at: ${contractAddress}`);
    console.log('='.repeat(60));

    const provider = new JsonRpcProvider(RPC_URL);

    // Check if address has code
    const code = await provider.getCode(contractAddress);
    
    if (code === '0x' || code === '0x0') {
      console.error('\n❌ No contract code found at this address!');
      console.error('   This address does not have a contract deployed.');
      console.error('\n💡 Solutions:');
      console.error('   1. Deploy the contract using: node contracts/scripts/deploy-final-working.mjs');
      console.error('   2. Update NEXT_PUBLIC_ESCROW_ADDRESS in frontend/.env.local with the deployed address');
      process.exit(1);
    }

    console.log(`\n✅ Contract code found (${code.length / 2 - 1} bytes)`);

    // Try to create contract instance
    const contract = new Contract(contractAddress, escrowArtifact.abi, provider);

    // Check if contract has expected functions
    console.log('\n🔍 Checking contract functions...');
    
    try {
      // Try to call a simple function to verify it's the right contract
      // Check if it has the owner (Ownable contract)
      const owner = await contract.owner();
      console.log(`   ✅ Owner: ${owner}`);
    } catch (err) {
      console.log(`   ⚠️  Could not get owner: ${err.message}`);
    }

    // Check escrowBalance function
    if (taskID) {
      try {
        const balance = await contract.escrowBalance(taskID);
        console.log(`\n✅ escrowBalance function works!`);
        console.log(`   Task ID: ${taskID}`);
        console.log(`   Escrow Balance: ${balance.toString()} Wei (${(Number(balance) / 1e18).toFixed(6)} ETH)`);
      } catch (err) {
        console.error(`\n❌ escrowBalance function failed:`);
        console.error(`   ${err.message}`);
        console.error('\n💡 This means:');
        console.error('   - The contract might not have the escrowBalance function');
        console.error('   - Or the contract was deployed with different code');
      }
    } else {
      console.log('\nℹ️  No taskID provided, skipping escrowBalance check');
      console.log('   To check escrow balance, provide taskID as second argument');
    }

    // Try to check tasks function
    if (taskID) {
      try {
        const task = await contract.tasks(taskID);
        if (task && task[1] !== '0x0000000000000000000000000000000000000000') {
          console.log(`\n✅ Task found on-chain:`);
          console.log(`   Publisher: ${task[1]}`);
          console.log(`   Reward: ${task[2].toString()} Wei (${(Number(task[2]) / 1e18).toFixed(6)} ETH)`);
          console.log(`   Status: ${task[5]}`);
        } else {
          console.log(`\nℹ️  Task "${taskID}" not found on-chain`);
        }
      } catch (err) {
        console.error(`\n❌ tasks function failed: ${err.message}`);
      }
    }

    console.log('\n✅ Contract verification complete!');
    console.log('\n💡 If escrowBalance failed, the contract might need to be redeployed.');

  } catch (error) {
    console.error('\n❌ Verification failed:');
    console.error(`   ${error.message}`);
    process.exit(1);
  }
}

verifyContract();

