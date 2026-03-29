import { ethers } from "ethers";
import fs from "fs/promises";
import path from "path";

const LOCAL_RPC_URL = process.env.RPC_URL || "http://127.0.0.1:7545";

function updateEnvVar(content, key, value) {
  const escaped = key.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const re = new RegExp(`^\\s*${escaped}=.*$`, "m");
  if (re.test(content)) {
    return content.replace(re, `${key}=${value}`);
  }
  return `${content.trimEnd()}\n${key}=${value}\n`;
}

async function readArtifact(name, cwd) {
  const p = path.join(cwd, "artifacts", "src", `${name}.sol`, `${name}.json`);
  return JSON.parse(await fs.readFile(p, "utf8"));
}

async function pickWallet(provider) {
  if (process.env.DEPLOYER_PRIVATE_KEY) {
    return new ethers.Wallet(process.env.DEPLOYER_PRIVATE_KEY, provider);
  }

  const defaults = [
    "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
    "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d",
    "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a",
  ];
  for (const key of defaults) {
    const w = new ethers.Wallet(key, provider);
    const bal = await provider.getBalance(await w.getAddress());
    if (bal > 0n) {
      return w;
    }
  }

  const accounts = await provider.send("eth_accounts", []);
  if (Array.isArray(accounts) && accounts.length > 0) {
    return await provider.getSigner(accounts[0]);
  }

  throw new Error("No funded deployer found. Set DEPLOYER_PRIVATE_KEY.");
}

async function main() {
  console.log("Deploying strict M7 stack to localhost...");
  const provider = new ethers.JsonRpcProvider(LOCAL_RPC_URL);
  const wallet = await pickWallet(provider);
  const deployer = await wallet.getAddress();
  const balance = await provider.getBalance(deployer);
  console.log(`Deployer: ${deployer}`);
  console.log(`Balance: ${ethers.formatEther(balance)} ETH`);

  const scoreRevealWindowSec = Number(process.env.REWARD_SCORE_REVEAL_WINDOW_SEC || 86400);
  const disputeGraceSec = Number(process.env.REWARD_DISPUTE_GRACE_SEC || 86400);
  const aggregatorShareBps = Number(process.env.REWARD_AGGREGATOR_SHARE_BPS || 1000);

  const cwd = process.cwd();
  const escrowArtifact = await readArtifact("HealChainEscrow", cwd);
  const rewardArtifact = await readArtifact("RewardDistribution", cwd);
  const blockPublisherArtifact = await readArtifact("BlockPublisher", cwd);

  let stakeRegistryArtifact = null;
  try {
    stakeRegistryArtifact = await readArtifact("StakeRegistry", cwd);
  } catch {
    console.log("StakeRegistry artifact not found; skipping StakeRegistry deploy.");
  }

  const EscrowFactory = new ethers.ContractFactory(
    escrowArtifact.abi,
    escrowArtifact.bytecode,
    wallet
  );
  const BlockPublisherFactory = new ethers.ContractFactory(
    blockPublisherArtifact.abi,
    blockPublisherArtifact.bytecode,
    wallet
  );
  const RewardFactory = new ethers.ContractFactory(
    rewardArtifact.abi,
    rewardArtifact.bytecode,
    wallet
  );

  console.log("Deploying HealChainEscrow...");
  const escrow = await EscrowFactory.deploy(deployer);
  await escrow.waitForDeployment();
  const escrowAddress = await escrow.getAddress();
  console.log(`HealChainEscrow: ${escrowAddress}`);

  console.log("Deploying BlockPublisher...");
  const blockPublisher = await BlockPublisherFactory.deploy(deployer);
  await blockPublisher.waitForDeployment();
  const blockPublisherAddress = await blockPublisher.getAddress();
  console.log(`BlockPublisher: ${blockPublisherAddress}`);

  console.log("Deploying RewardDistribution...");
  const reward = await RewardFactory.deploy(
    escrowAddress,
    blockPublisherAddress,
    scoreRevealWindowSec,
    disputeGraceSec,
    aggregatorShareBps
  );
  await reward.waitForDeployment();
  const rewardAddress = await reward.getAddress();
  console.log(`RewardDistribution: ${rewardAddress}`);

  console.log("Wiring reward distributor permissions...");
  await (await escrow.setRewardDistributor(rewardAddress)).wait();
  await (await blockPublisher.setRewardDistributor(rewardAddress)).wait();
  console.log("Reward distributor wiring complete.");

  let stakeRegistryAddress = null;
  if (stakeRegistryArtifact) {
    const StakeRegistryFactory = new ethers.ContractFactory(
      stakeRegistryArtifact.abi,
      stakeRegistryArtifact.bytecode,
      wallet
    );
    console.log("Deploying StakeRegistry...");
    const stakeRegistry = await StakeRegistryFactory.deploy(deployer);
    await stakeRegistry.waitForDeployment();
    stakeRegistryAddress = await stakeRegistry.getAddress();
    console.log(`StakeRegistry: ${stakeRegistryAddress}`);
  }

  const frontendEnvPath = path.join(cwd, "..", "frontend", ".env.local");
  const backendEnvPath = path.join(cwd, "..", "backend", ".env.development");

  let frontendEnv = "";
  try {
    frontendEnv = await fs.readFile(frontendEnvPath, "utf8");
  } catch {
    frontendEnv = "NEXT_PUBLIC_BACKEND_URL=http://localhost:3000\n";
  }
  frontendEnv = updateEnvVar(frontendEnv, "NEXT_PUBLIC_ESCROW_ADDRESS", escrowAddress);
  frontendEnv = updateEnvVar(frontendEnv, "NEXT_PUBLIC_REWARD_ADDRESS", rewardAddress);
  frontendEnv = updateEnvVar(
    frontendEnv,
    "NEXT_PUBLIC_BLOCK_PUBLISHER_ADDRESS",
    blockPublisherAddress
  );
  if (stakeRegistryAddress) {
    frontendEnv = updateEnvVar(
      frontendEnv,
      "NEXT_PUBLIC_STAKE_REGISTRY_ADDRESS",
      stakeRegistryAddress
    );
  }
  await fs.writeFile(frontendEnvPath, frontendEnv, "utf8");
  console.log("Updated frontend/.env.local");

  let backendEnv = "";
  try {
    backendEnv = await fs.readFile(backendEnvPath, "utf8");
  } catch {
    backendEnv = "";
  }
  backendEnv = updateEnvVar(backendEnv, "ESCROW_ADDRESS", escrowAddress);
  backendEnv = updateEnvVar(backendEnv, "ESCROW_CONTRACT_ADDRESS", escrowAddress);
  backendEnv = updateEnvVar(backendEnv, "BLOCK_PUBLISHER_ADDRESS", blockPublisherAddress);
  backendEnv = updateEnvVar(backendEnv, "REWARD_CONTRACT_ADDRESS", rewardAddress);
  if (stakeRegistryAddress) {
    backendEnv = updateEnvVar(backendEnv, "STAKE_REGISTRY_ADDRESS", stakeRegistryAddress);
  }
  await fs.writeFile(backendEnvPath, backendEnv, "utf8");
  console.log("Updated backend/.env.development");

  console.log("\nDeployment complete.");
  console.log("Restart backend and frontend to pick up new contract addresses.");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
