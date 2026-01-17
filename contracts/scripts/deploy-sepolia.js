import dotenv from "dotenv";
dotenv.config();

import { ethers } from "ethers";

async function main() {
  console.log("🚀 Deploying to Sepolia");

  // Setup provider and wallet
  const rpcUrl = process.env.SEPOLIA_RPC_URL;
  const privateKey = process.env.DEPLOYER_PRIVATE_KEY;
  
  if (!rpcUrl || !privateKey) {
    console.error("❌ Missing SEPOLIA_RPC_URL or DEPLOYER_PRIVATE_KEY in environment");
    process.exit(1);
  }

  const provider = new ethers.JsonRpcProvider(rpcUrl);
  const wallet = new ethers.Wallet(privateKey, provider);
  
  console.log("Deployer:", wallet.address);
  const balance = await provider.getBalance(wallet.address);
  console.log("Balance:", ethers.formatEther(balance));

  // Read contract artifacts
  const fs = await import('fs/promises');
  const path = await import('path');
  
  // Read HealChainEscrow ABI
  const escrowArtifactPath = path.join(process.cwd(), 'artifacts', 'src', 'HealChainEscrow.sol', 'HealChainEscrow.json');
  const escrowArtifact = JSON.parse(await fs.readFile(escrowArtifactPath, 'utf8'));
  
  // Read RewardDistribution ABI
  const rewardArtifactPath = path.join(process.cwd(), 'artifacts', 'src', 'RewardDistribution.sol', 'RewardDistribution.json');
  const rewardArtifact = JSON.parse(await fs.readFile(rewardArtifactPath, 'utf8'));
  
  // Read StakeRegistry ABI (optional - may not be compiled)
  const stakeRegistryArtifactPath = path.join(process.cwd(), 'artifacts', 'src', 'StakeRegistry.sol', 'StakeRegistry.json');
  let stakeRegistryArtifact;
  try {
    stakeRegistryArtifact = JSON.parse(await fs.readFile(stakeRegistryArtifactPath, 'utf8'));
  } catch (error) {
    console.log("⚠️  StakeRegistry artifact not found. Skipping StakeRegistry deployment.");
    stakeRegistryArtifact = null;
  }

  // Deploy HealChainEscrow
  const EscrowFactory = new ethers.ContractFactory(
    escrowArtifact.abi,
    escrowArtifact.bytecode,
    wallet
  );
  
  console.log("Deploying HealChainEscrow...");
  const escrow = await EscrowFactory.deploy(wallet.address);
  await escrow.waitForDeployment();
  const escrowAddress = await escrow.getAddress();
  console.log("HealChainEscrow deployed to:", escrowAddress);

  // Deploy RewardDistribution
  const RewardFactory = new ethers.ContractFactory(
    rewardArtifact.abi,
    rewardArtifact.bytecode,
    wallet
  );
  
  console.log("Deploying RewardDistribution...");
  const reward = await RewardFactory.deploy(escrowAddress);
  await reward.waitForDeployment();
  const rewardAddress = await reward.getAddress();
  console.log("RewardDistribution deployed to:", rewardAddress);

  // Deploy StakeRegistry (if artifact exists)
  let stakeRegistryAddress = null;
  if (stakeRegistryArtifact) {
    const StakeRegistryFactory = new ethers.ContractFactory(
      stakeRegistryArtifact.abi,
      stakeRegistryArtifact.bytecode,
      wallet
    );
    
    console.log("Deploying StakeRegistry...");
    const stakeRegistry = await StakeRegistryFactory.deploy(wallet.address);
    await stakeRegistry.waitForDeployment();
    stakeRegistryAddress = await stakeRegistry.getAddress();
    console.log("StakeRegistry deployed to:", stakeRegistryAddress);
    
    // Verify deployment
    const minStake = await stakeRegistry.MIN_STAKE();
    console.log("   Minimum Stake:", ethers.formatEther(minStake), "ETH");
  } else {
    console.log("⚠️  Skipping StakeRegistry deployment (contract not compiled)");
  }

  // Note: Contract verification would need to be implemented separately
  // using Etherscan API directly since hardhat verification isn't working

  // Automatically update environment files
  console.log("\n📝 Updating environment files...");
  
  const projectRoot = process.cwd();
  const frontendEnvPath = path.join(projectRoot, '..', 'frontend', '.env.local');
  const backendEnvPath = path.join(projectRoot, '..', 'backend', '.env.production');
  
  // Helper function to update or add env variable
  const updateEnvVar = (content, varName, value) => {
    const regex = new RegExp(`^[#\\s]*${varName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}=.*$`, 'm');
    if (regex.test(content)) {
      return content.replace(regex, `${varName}=${value}`);
    } else {
      const sepoliaSection = /# Contract Addresses - Sepolia.*?(?=\n#|$)/s;
      if (sepoliaSection.test(content)) {
        return content.replace(sepoliaSection, (match) => {
          if (match.includes('NEXT_PUBLIC_BLOCK_PUBLISHER_ADDRESS_SEPOLIA=')) {
            return match.replace(/NEXT_PUBLIC_BLOCK_PUBLISHER_ADDRESS_SEPOLIA=.*/, `$&\n${varName}=${value}`);
          } else if (match.includes('NEXT_PUBLIC_REWARD_ADDRESS_SEPOLIA=')) {
            return match.replace(/NEXT_PUBLIC_REWARD_ADDRESS_SEPOLIA=.*/, `$&\n${varName}=${value}`);
          } else {
            return match + `\n${varName}=${value}`;
          }
        });
      } else {
        return content + `\n${varName}=${value}`;
      }
    }
  };
  
  // Update frontend .env.local (Sepolia addresses)
  try {
    let frontendEnv = '';
    try {
      frontendEnv = await fs.readFile(frontendEnvPath, 'utf8');
    } catch {
      console.log(`   ⚠️  frontend/.env.local not found, skipping...`);
    }
    
    if (frontendEnv) {
      frontendEnv = updateEnvVar(frontendEnv, 'NEXT_PUBLIC_ESCROW_ADDRESS_SEPOLIA', escrowAddress);
      frontendEnv = updateEnvVar(frontendEnv, 'NEXT_PUBLIC_REWARD_ADDRESS_SEPOLIA', rewardAddress);
      if (stakeRegistryAddress) {
        frontendEnv = updateEnvVar(frontendEnv, 'NEXT_PUBLIC_STAKE_REGISTRY_ADDRESS_SEPOLIA', stakeRegistryAddress);
      }
      
      // Update timestamp
      if (frontendEnv.includes('# Last updated:')) {
        frontendEnv = frontendEnv.replace(
          /# Last updated:.*/,
          `# Last updated: ${new Date().toISOString()}`
        );
      }
      
      await fs.writeFile(frontendEnvPath, frontendEnv, 'utf8');
      console.log(`   ✅ Updated frontend/.env.local (Sepolia addresses)`);
    }
  } catch (frontendError) {
    console.log(`   ⚠️  Could not update frontend/.env.local: ${frontendError.message}`);
  }
  
  // Update backend .env.production
  try {
    let backendEnv = '';
    try {
      backendEnv = await fs.readFile(backendEnvPath, 'utf8');
    } catch {
      // File doesn't exist, create it
      backendEnv = `# HealChain Backend - Production Environment Variables
# Auto-generated by deployment script
# Last updated: ${new Date().toISOString()}

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/healchain

# RPC Configuration
RPC_URL=https://sepolia.infura.io/v3/YOUR_PROJECT_ID

# Contract Addresses (Sepolia)
ESCROW_ADDRESS=
ESCROW_CONTRACT_ADDRESS=
REWARD_CONTRACT_ADDRESS=
STAKE_REGISTRY_ADDRESS=

# Backend Wallet
BACKEND_PRIVATE_KEY=your_private_key_here
`;
    }
    
    const updateBackendVar = (content, varName, value) => {
      const regex = new RegExp(`^[#\\s]*${varName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}=.*$`, 'm');
      if (regex.test(content)) {
        return content.replace(regex, `${varName}=${value}`);
      } else {
        const contractSection = /# Contract Addresses.*?(?=\n#|$)/s;
        if (contractSection.test(content)) {
          return content.replace(contractSection, (match) => match + `\n${varName}=${value}`);
        } else {
          return content + `\n${varName}=${value}`;
        }
      }
    };
    
    backendEnv = updateBackendVar(backendEnv, 'ESCROW_ADDRESS', escrowAddress);
    backendEnv = updateBackendVar(backendEnv, 'ESCROW_CONTRACT_ADDRESS', escrowAddress);
    backendEnv = updateBackendVar(backendEnv, 'REWARD_CONTRACT_ADDRESS', rewardAddress);
    if (stakeRegistryAddress) {
      backendEnv = updateBackendVar(backendEnv, 'STAKE_REGISTRY_ADDRESS', stakeRegistryAddress);
    }
    
    // Update timestamp
    if (backendEnv.includes('# Last updated:')) {
      backendEnv = backendEnv.replace(
        /# Last updated:.*/,
        `# Last updated: ${new Date().toISOString()}`
      );
    }
    
    await fs.writeFile(backendEnvPath, backendEnv, 'utf8');
    console.log(`   ✅ Updated backend/.env.production`);
  } catch (backendError) {
    console.log(`   ⚠️  Could not update backend/.env.production: ${backendError.message}`);
    console.log(`   📋 Manually add to backend/.env.production:`);
    console.log(`      ESCROW_ADDRESS=${escrowAddress}`);
    console.log(`      ESCROW_CONTRACT_ADDRESS=${escrowAddress}`);
    console.log(`      REWARD_CONTRACT_ADDRESS=${rewardAddress}`);
    if (stakeRegistryAddress) {
      console.log(`      STAKE_REGISTRY_ADDRESS=${stakeRegistryAddress}`);
    }
  }
  
  console.log("\n💡 Restart your frontend and backend to pick up the new contract addresses.");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
