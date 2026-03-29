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

function parseEnvValue(content, key) {
  const escaped = key.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const re = new RegExp(`^\\s*${escaped}=(.*)$`, "m");
  const m = content.match(re);
  if (!m) return "";
  return String(m[1] || "").trim();
}

function isAddress(v) {
  return /^0x[0-9a-fA-F]{40}$/.test(String(v || "").trim());
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
    if (bal > 0n) return w;
  }

  const accounts = await provider.send("eth_accounts", []);
  if (Array.isArray(accounts) && accounts.length > 0) {
    return await provider.getSigner(accounts[0]);
  }

  throw new Error("No funded deployer found. Set DEPLOYER_PRIVATE_KEY.");
}

async function main() {
  console.log("Redeploying M6/M7 contracts while keeping existing Escrow...");
  const provider = new ethers.JsonRpcProvider(LOCAL_RPC_URL);
  const wallet = await pickWallet(provider);
  const deployer = await wallet.getAddress();
  console.log(`Deployer: ${deployer}`);

  const cwd = process.cwd();
  const backendEnvPath = path.join(cwd, "..", "backend", ".env.development");
  const frontendEnvPath = path.join(cwd, "..", "frontend", ".env.local");

  const backendEnv = await fs.readFile(backendEnvPath, "utf8");
  const escrowAddress =
    process.env.ESCROW_ADDRESS ||
    parseEnvValue(backendEnv, "ESCROW_ADDRESS") ||
    parseEnvValue(backendEnv, "ESCROW_CONTRACT_ADDRESS");

  if (!isAddress(escrowAddress)) {
    throw new Error(
      `ESCROW_ADDRESS is missing/invalid (${escrowAddress}). ` +
      "Set it in backend/.env.development or export ESCROW_ADDRESS."
    );
  }
  console.log(`Using existing Escrow: ${escrowAddress}`);

  const scoreRevealWindowSec = Number(process.env.REWARD_SCORE_REVEAL_WINDOW_SEC || 86400);
  const disputeGraceSec = Number(process.env.REWARD_DISPUTE_GRACE_SEC || 86400);
  const aggregatorShareBps = Number(process.env.REWARD_AGGREGATOR_SHARE_BPS || 1000);

  const escrowArtifact = await readArtifact("HealChainEscrow", cwd);
  const blockPublisherArtifact = await readArtifact("BlockPublisher", cwd);
  const rewardArtifact = await readArtifact("RewardDistribution", cwd);

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

  console.log("Deploying new BlockPublisher...");
  const blockPublisher = await BlockPublisherFactory.deploy(deployer);
  await blockPublisher.waitForDeployment();
  const blockPublisherAddress = await blockPublisher.getAddress();
  console.log(`BlockPublisher: ${blockPublisherAddress}`);

  console.log("Deploying new RewardDistribution...");
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
  const escrow = new ethers.Contract(escrowAddress, escrowArtifact.abi, wallet);
  await (await escrow.setRewardDistributor(rewardAddress)).wait();
  await (await blockPublisher.setRewardDistributor(rewardAddress)).wait();
  console.log("Wiring complete.");

  let frontendEnv = "";
  try {
    frontendEnv = await fs.readFile(frontendEnvPath, "utf8");
  } catch {
    frontendEnv = "NEXT_PUBLIC_BACKEND_URL=http://localhost:3000\n";
  }
  frontendEnv = updateEnvVar(
    frontendEnv,
    "NEXT_PUBLIC_BLOCK_PUBLISHER_ADDRESS",
    blockPublisherAddress
  );
  frontendEnv = updateEnvVar(frontendEnv, "NEXT_PUBLIC_REWARD_ADDRESS", rewardAddress);
  await fs.writeFile(frontendEnvPath, frontendEnv, "utf8");
  console.log("Updated frontend/.env.local");

  let backendEnvUpdated = backendEnv;
  backendEnvUpdated = updateEnvVar(
    backendEnvUpdated,
    "BLOCK_PUBLISHER_ADDRESS",
    blockPublisherAddress
  );
  backendEnvUpdated = updateEnvVar(
    backendEnvUpdated,
    "REWARD_CONTRACT_ADDRESS",
    rewardAddress
  );
  await fs.writeFile(backendEnvPath, backendEnvUpdated, "utf8");
  console.log("Updated backend/.env.development");

  console.log("\nDone.");
  console.log("Restart backend + frontend + aggregator services.");
  console.log("Then re-run M6 publish for tasks that need corrected on-chain aggregator identity.");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});

