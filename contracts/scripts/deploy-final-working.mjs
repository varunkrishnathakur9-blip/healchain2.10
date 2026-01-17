import { ethers } from "ethers";

async function main() {
  console.log("🚀 Deploying to localhost (final working version)");

  // Setup provider
  const provider = new ethers.JsonRpcProvider("http://127.0.0.1:7545");
  
  // Get deployer wallet
  let privateKey = process.env.DEPLOYER_PRIVATE_KEY;
  let wallet;
  
  if (privateKey) {
    wallet = new ethers.Wallet(privateKey, provider);
    const balance = await provider.getBalance(wallet.address);
    console.log("Deployer:", wallet.address);
    console.log("Balance:", ethers.formatEther(balance));
    
    if (balance === 0n) {
      console.log("⚠️  Deployer account has 0 ETH. Trying to find a funded account from Ganache...");
      privateKey = null; // Will find a funded account below
    }
  }
  
  // If no private key or account has no funds, try Ganache's default accounts
  if (!privateKey || (wallet && (await provider.getBalance(wallet.address)) === 0n)) {
    console.log("🔍 Finding funded account from Ganache...");
    
    // Try Ganache's default account #0 (most common)
    // Ganache typically uses the same private keys as Hardhat for default accounts
    const ganacheDefaultKeys = [
      "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80", // Account #0
      "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d", // Account #1
      "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a", // Account #2
    ];
    
    let foundWallet = null;
    for (const key of ganacheDefaultKeys) {
      const testWallet = new ethers.Wallet(key, provider);
      const balance = await provider.getBalance(testWallet.address);
      if (balance > 0n) {
        console.log(`✅ Found funded account: ${testWallet.address} (${ethers.formatEther(balance)} ETH)`);
        foundWallet = testWallet;
        break;
      }
    }
    
    if (!foundWallet) {
      // Last resort: try to get accounts from Ganache and use the first one
      const accounts = await provider.send("eth_accounts", []);
      if (accounts && accounts.length > 0) {
        const firstAccount = accounts[0];
        const balance = await provider.getBalance(firstAccount);
        if (balance > 0n) {
          console.log(`✅ Using first Ganache account: ${firstAccount} (${ethers.formatEther(balance)} ETH)`);
          // Use provider.getSigner for unlocked accounts
          foundWallet = await provider.getSigner(firstAccount);
        }
      }
    }
    
    if (!foundWallet) {
      throw new Error("❌ No funded accounts found. Please ensure Ganache is running with at least one funded account.");
    }
    
    wallet = foundWallet;
  } else {
    wallet = new ethers.Wallet(privateKey, provider);
  }
  
  const deployerAddress = await wallet.getAddress();
  const finalBalance = await provider.getBalance(deployerAddress);
  console.log("\n📋 Deployment Configuration:");
  console.log("   Deployer:", deployerAddress);
  console.log("   Balance:", ethers.formatEther(finalBalance), "ETH");

  // Read contract artifacts
  const fs = await import('fs/promises');
  const path = await import('path');
  
  // Read HealChainEscrow ABI
  const escrowArtifactPath = path.join(process.cwd(), 'artifacts', 'src', 'HealChainEscrow.sol', 'HealChainEscrow.json');
  const escrowArtifact = JSON.parse(await fs.readFile(escrowArtifactPath, 'utf8'));
  
  // Read RewardDistribution ABI
  const rewardArtifactPath = path.join(process.cwd(), 'artifacts', 'src', 'RewardDistribution.sol', 'RewardDistribution.json');
  const rewardArtifact = JSON.parse(await fs.readFile(rewardArtifactPath, 'utf8'));
  
  // Read StakeRegistry ABI
  const stakeRegistryArtifactPath = path.join(process.cwd(), 'artifacts', 'src', 'StakeRegistry.sol', 'StakeRegistry.json');
  let stakeRegistryArtifact;
  try {
    stakeRegistryArtifact = JSON.parse(await fs.readFile(stakeRegistryArtifactPath, 'utf8'));
  } catch (error) {
    console.log("⚠️  StakeRegistry artifact not found. Make sure contract is compiled:");
    console.log("   cd contracts && npm run compile");
    stakeRegistryArtifact = null;
  }

  try {
    // Get current nonce
    const nonce = await provider.getTransactionCount(wallet.address, "pending");
    console.log("Current nonce:", nonce);
    
    // If nonce is very high, there might be stuck transactions
    if (nonce > 100) {
      console.log("⚠️  High nonce detected. This might cause issues.");
      console.log("💡 Consider resetting Ganache if deployment fails.");
    }

    // Deploy HealChainEscrow
    const EscrowFactory = new ethers.ContractFactory(
      escrowArtifact.abi,
      escrowArtifact.bytecode,
      wallet
    );
    
    console.log("Deploying HealChainEscrow...");
    const escrow = await EscrowFactory.deploy(await wallet.getAddress(), { 
      gasLimit: 5000000  // Increased gas limit
    });
    
    console.log("Transaction hash:", escrow.deploymentTransaction().hash);
    await escrow.waitForDeployment();
    const escrowAddress = await escrow.getAddress();
    console.log("✅ HealChainEscrow deployed to:", escrowAddress);

    // Deploy RewardDistribution with nonce+1
    const RewardFactory = new ethers.ContractFactory(
      rewardArtifact.abi,
      rewardArtifact.bytecode,
      wallet
    );
    
    console.log("Deploying RewardDistribution...");
    const reward = await RewardFactory.deploy(escrowAddress, { 
      gasLimit: 5000000  // Increased gas limit
    });
    
    console.log("Transaction hash:", reward.deploymentTransaction().hash);
    await reward.waitForDeployment();
    const rewardAddress = await reward.getAddress();
    console.log("✅ RewardDistribution deployed to:", rewardAddress);

    // Deploy StakeRegistry (if artifact exists)
    let stakeRegistryAddress = null;
    if (stakeRegistryArtifact) {
      const StakeRegistryFactory = new ethers.ContractFactory(
        stakeRegistryArtifact.abi,
        stakeRegistryArtifact.bytecode,
        wallet
      );
      
      console.log("Deploying StakeRegistry...");
      const stakeRegistry = await StakeRegistryFactory.deploy(deployerAddress, { 
        gasLimit: 5000000
      });
      
      console.log("Transaction hash:", stakeRegistry.deploymentTransaction().hash);
      await stakeRegistry.waitForDeployment();
      stakeRegistryAddress = await stakeRegistry.getAddress();
      console.log("✅ StakeRegistry deployed to:", stakeRegistryAddress);
      
      // Verify deployment
      const minStake = await stakeRegistry.MIN_STAKE();
      const unlockDelay = await stakeRegistry.UNLOCK_DELAY();
      console.log("   Minimum Stake:", ethers.formatEther(minStake), "ETH");
      console.log("   Unlock Delay:", Number(unlockDelay) / 86400, "days");
    } else {
      console.log("⚠️  Skipping StakeRegistry deployment (contract not compiled)");
    }

    // Output for backend
    console.log("\n🎉 DEPLOYMENT SUCCESSFUL!");
    
    // Automatically update environment files
    console.log("\n📝 Updating environment files...");
    
    const projectRoot = process.cwd();
    const frontendEnvPath = path.join(projectRoot, '..', 'frontend', '.env.local');
    const backendEnvPath = path.join(projectRoot, '..', 'backend', '.env.development');
    
    // Update frontend .env.local
    try {
      let frontendEnv = '';
      try {
        frontendEnv = await fs.readFile(frontendEnvPath, 'utf8');
      } catch {
        // File doesn't exist, create it
        frontendEnv = `# HealChain Frontend - Environment Variables
# Auto-generated by deployment script
# Last updated: ${new Date().toISOString()}

# Backend API
NEXT_PUBLIC_BACKEND_URL=http://localhost:3000

# Contract Addresses - Localhost (Ganache/Hardhat)
NEXT_PUBLIC_ESCROW_ADDRESS=
NEXT_PUBLIC_REWARD_ADDRESS=
NEXT_PUBLIC_BLOCK_PUBLISHER_ADDRESS=
NEXT_PUBLIC_STAKE_REGISTRY_ADDRESS=

# Contract Addresses - Sepolia Testnet
NEXT_PUBLIC_ESCROW_ADDRESS_SEPOLIA=
NEXT_PUBLIC_REWARD_ADDRESS_SEPOLIA=
NEXT_PUBLIC_BLOCK_PUBLISHER_ADDRESS_SEPOLIA=

# WalletConnect (Optional)
NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID=

# Development
NEXT_PUBLIC_DEBUG=false
`;
      }
      
      // Helper function to update or add env variable
      const updateEnvVar = (content, varName, value) => {
        // Match the variable even if it's commented out or has different formatting
        const regex = new RegExp(`^[#\\s]*${varName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}=.*$`, 'm');
        if (regex.test(content)) {
          return content.replace(regex, `${varName}=${value}`);
        } else {
          // Add it at the end of the localhost section or at the end of file
          const localhostSection = /# Contract Addresses - Localhost.*?(?=\n#|$)/s;
          if (localhostSection.test(content)) {
            return content.replace(localhostSection, (match) => {
              // Add after the last localhost variable or at the end of the section
              if (match.includes('NEXT_PUBLIC_BLOCK_PUBLISHER_ADDRESS=')) {
                return match.replace(/NEXT_PUBLIC_BLOCK_PUBLISHER_ADDRESS=.*/, `$&\n${varName}=${value}`);
              } else if (match.includes('NEXT_PUBLIC_REWARD_ADDRESS=')) {
                return match.replace(/NEXT_PUBLIC_REWARD_ADDRESS=.*/, `$&\n${varName}=${value}`);
              } else {
                return match + `\n${varName}=${value}`;
              }
            });
          } else {
            return content + `\n${varName}=${value}`;
          }
        }
      };
      
      // Update or add ESCROW_ADDRESS
      frontendEnv = updateEnvVar(frontendEnv, 'NEXT_PUBLIC_ESCROW_ADDRESS', escrowAddress);
      
      // Update or add REWARD_ADDRESS
      frontendEnv = updateEnvVar(frontendEnv, 'NEXT_PUBLIC_REWARD_ADDRESS', rewardAddress);
      
      // Update or add STAKE_REGISTRY_ADDRESS (if deployed)
      if (stakeRegistryAddress) {
        frontendEnv = updateEnvVar(frontendEnv, 'NEXT_PUBLIC_STAKE_REGISTRY_ADDRESS', stakeRegistryAddress);
      }
      
      // Add deployment timestamp comment
      if (!frontendEnv.includes('# Last updated:')) {
        frontendEnv = frontendEnv.replace(
          /# Auto-generated by deployment script/,
          `# Auto-generated by deployment script\n# Last updated: ${new Date().toISOString()}`
        );
      } else {
        frontendEnv = frontendEnv.replace(
          /# Last updated:.*/,
          `# Last updated: ${new Date().toISOString()}`
        );
      }
      
      await fs.writeFile(frontendEnvPath, frontendEnv, 'utf8');
      console.log(`   ✅ Updated frontend/.env.local`);
    } catch (frontendError) {
      console.log(`   ⚠️  Could not update frontend/.env.local: ${frontendError.message}`);
      console.log(`   📋 Manually add to frontend/.env.local:`);
      console.log(`      NEXT_PUBLIC_ESCROW_ADDRESS=${escrowAddress}`);
      console.log(`      NEXT_PUBLIC_REWARD_ADDRESS=${rewardAddress}`);
      if (stakeRegistryAddress) {
        console.log(`      NEXT_PUBLIC_STAKE_REGISTRY_ADDRESS=${stakeRegistryAddress}`);
      }
    }
    
    // Update backend .env.development
    try {
      let backendEnv = '';
      try {
        backendEnv = await fs.readFile(backendEnvPath, 'utf8');
      } catch {
        // File doesn't exist, create it
        backendEnv = `# HealChain Backend - Environment Variables
# Auto-generated by deployment script
# Last updated: ${new Date().toISOString()}

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/healchain

# RPC Configuration
RPC_URL=http://127.0.0.1:7545

# Contract Addresses
ESCROW_ADDRESS=
ESCROW_CONTRACT_ADDRESS=
REWARD_CONTRACT_ADDRESS=
STAKE_REGISTRY_ADDRESS=

# Backend Wallet
BACKEND_PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
`;
      }
      
      // Helper function to update or add env variable
      const updateEnvVar = (content, varName, value) => {
        // Match the variable even if it's commented out or has different formatting
        const regex = new RegExp(`^[#\\s]*${varName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}=.*$`, 'm');
        if (regex.test(content)) {
          return content.replace(regex, `${varName}=${value}`);
        } else {
          // Add it in the Contract Addresses section
          const contractSection = /# Contract Addresses.*?(?=\n#|$)/s;
          if (contractSection.test(content)) {
            return content.replace(contractSection, (match) => {
              return match + `\n${varName}=${value}`;
            });
          } else {
            return content + `\n${varName}=${value}`;
          }
        }
      };
      
      // Update or add ESCROW_ADDRESS
      backendEnv = updateEnvVar(backendEnv, 'ESCROW_ADDRESS', escrowAddress);
      
      // Update or add ESCROW_CONTRACT_ADDRESS
      backendEnv = updateEnvVar(backendEnv, 'ESCROW_CONTRACT_ADDRESS', escrowAddress);
      
      // Update or add REWARD_CONTRACT_ADDRESS
      backendEnv = updateEnvVar(backendEnv, 'REWARD_CONTRACT_ADDRESS', rewardAddress);
      
      // Update or add STAKE_REGISTRY_ADDRESS (if deployed)
      if (stakeRegistryAddress) {
        backendEnv = updateEnvVar(backendEnv, 'STAKE_REGISTRY_ADDRESS', stakeRegistryAddress);
      }
      
      // Update timestamp
      if (!backendEnv.includes('# Last updated:')) {
        backendEnv = backendEnv.replace(
          /# Auto-generated by deployment script/,
          `# Auto-generated by deployment script\n# Last updated: ${new Date().toISOString()}`
        );
      } else {
        backendEnv = backendEnv.replace(
          /# Last updated:.*/,
          `# Last updated: ${new Date().toISOString()}`
        );
      }
      
      await fs.writeFile(backendEnvPath, backendEnv, 'utf8');
      console.log(`   ✅ Updated backend/.env.development`);
    } catch (backendError) {
      console.log(`   ⚠️  Could not update backend/.env.development: ${backendError.message}`);
      console.log(`   📋 Manually add to backend/.env.development:`);
      console.log(`      ESCROW_ADDRESS=${escrowAddress}`);
      console.log(`      ESCROW_CONTRACT_ADDRESS=${escrowAddress}`);
      console.log(`      REWARD_CONTRACT_ADDRESS=${rewardAddress}`);
      if (stakeRegistryAddress) {
        console.log(`      STAKE_REGISTRY_ADDRESS=${stakeRegistryAddress}`);
      }
    }
    
    console.log("\n🔍 Verifying contracts...");
    try {
      const escrowCode = await provider.getCode(escrowAddress);
      const rewardCode = await provider.getCode(rewardAddress);
      let stakeRegistryCode = '0x';
      if (stakeRegistryAddress) {
        stakeRegistryCode = await provider.getCode(stakeRegistryAddress);
      }
      
      if (escrowCode.length > 2 && rewardCode.length > 2 && (!stakeRegistryAddress || stakeRegistryCode.length > 2)) {
        console.log("✅ Contracts verified on-chain");
      } else {
        console.log("❌ Contract verification failed");
      }
    } catch (verifyError) {
      console.log("⚠️ Could not verify contracts:", verifyError.message);
    }
    
    console.log("\n🚀 Ready for integration!");
    console.log("\n⚠️  IMPORTANT: You MUST restart your backend server for the changes to take effect!");
    console.log("   The backend reads contract addresses from .env.development on startup.");
    console.log("   If the backend is already running, stop it (Ctrl+C) and restart with: npm run dev");
    console.log("\n💡 Also restart your frontend to pick up the new contract addresses.");
    
  } catch (error) {
    console.error("❌ Deployment failed:", error.message);
    
    if (error.message.includes("insufficient funds")) {
      console.log("💡 Check wallet balance");
    } else if (error.message.includes("nonce")) {
      console.log("💡 Try restarting the node to reset nonces");
      console.log("💡 Or wait for pending transactions to clear");
    } else if (error.message.includes("gas")) {
      console.log("💡 Try increasing gas limit");
    } else {
      console.log("💡 Check contract artifacts and network connection");
    }
  }
}

main().catch((err) => {
  console.error("❌ Script failed:", err);
  process.exit(1);
});
