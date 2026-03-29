import dotenv from "dotenv";
dotenv.config();

import { ethers } from "ethers";
import fs from "fs/promises";
import path from "path";

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

async function main() {
  const rpcUrl = process.env.SEPOLIA_RPC_URL;
  const privateKey = process.env.DEPLOYER_PRIVATE_KEY;
  if (!rpcUrl || !privateKey) {
    throw new Error("Missing SEPOLIA_RPC_URL or DEPLOYER_PRIVATE_KEY");
  }

  const provider = new ethers.JsonRpcProvider(rpcUrl);
  const wallet = new ethers.Wallet(privateKey, provider);
  const deployer = await wallet.getAddress();
  const bal = await provider.getBalance(deployer);
  console.log(`Deploying strict M7 stack to Sepolia as ${deployer} (${ethers.formatEther(bal)} ETH)`);

  const scoreRevealWindowSec = Number(process.env.REWARD_SCORE_REVEAL_WINDOW_SEC || 86400);
  const disputeGraceSec = Number(process.env.REWARD_DISPUTE_GRACE_SEC || 86400);
  const aggregatorShareBps = Number(process.env.REWARD_AGGREGATOR_SHARE_BPS || 1000);

  const cwd = process.cwd();
  const escrowArtifact = await readArtifact("HealChainEscrow", cwd);
  const rewardArtifact = await readArtifact("RewardDistribution", cwd);
  const blockPublisherArtifact = await readArtifact("BlockPublisher", cwd);

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

  const frontendEnvPath = path.join(cwd, "..", "frontend", ".env.local");
  const backendEnvPath = path.join(cwd, "..", "backend", ".env.production");

  let frontendEnv = "";
  try {
    frontendEnv = await fs.readFile(frontendEnvPath, "utf8");
  } catch {
    frontendEnv = "";
  }
  frontendEnv = updateEnvVar(frontendEnv, "NEXT_PUBLIC_ESCROW_ADDRESS_SEPOLIA", escrowAddress);
  frontendEnv = updateEnvVar(frontendEnv, "NEXT_PUBLIC_REWARD_ADDRESS_SEPOLIA", rewardAddress);
  frontendEnv = updateEnvVar(
    frontendEnv,
    "NEXT_PUBLIC_BLOCK_PUBLISHER_ADDRESS_SEPOLIA",
    blockPublisherAddress
  );
  await fs.writeFile(frontendEnvPath, frontendEnv, "utf8");
  console.log("Updated frontend/.env.local (Sepolia addresses)");

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
  await fs.writeFile(backendEnvPath, backendEnv, "utf8");
  console.log("Updated backend/.env.production");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
