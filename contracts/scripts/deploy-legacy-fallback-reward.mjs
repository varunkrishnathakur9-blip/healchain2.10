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

  const envKeys = [
    process.env.BACKEND_PRIVATE_KEY,
    process.env.MINER_PRIVATE_KEY,
  ].filter(Boolean);

  for (const key of envKeys) {
    try {
      const wallet = new ethers.Wallet(key, provider);
      const balance = await provider.getBalance(await wallet.getAddress());
      if (balance > 0n) return wallet;
    } catch {
      // ignore invalid key
    }
  }

  const accounts = await provider.send("eth_accounts", []);
  if (Array.isArray(accounts) && accounts.length > 0) {
    return await provider.getSigner(accounts[0]);
  }

  throw new Error("No funded deployer found. Set DEPLOYER_PRIVATE_KEY.");
}

async function main() {
  console.log("Deploying legacy-compatible fallback RewardDistribution...");
  const provider = new ethers.JsonRpcProvider(LOCAL_RPC_URL);
  const wallet = await pickWallet(provider);
  const deployer = await wallet.getAddress();
  console.log(`Deployer: ${deployer}`);

  const cwd = process.cwd();
  const backendEnvDevPath = path.join(cwd, "..", "backend", ".env.development");
  const backendEnvPath = path.join(cwd, "..", "backend", ".env");
  const frontendEnvPath = path.join(cwd, "..", "frontend", ".env.local");

  const backendEnvDev = await fs.readFile(backendEnvDevPath, "utf8");
  const escrowAddress =
    process.env.ESCROW_ADDRESS ||
    parseEnvValue(backendEnvDev, "ESCROW_ADDRESS") ||
    parseEnvValue(backendEnvDev, "ESCROW_CONTRACT_ADDRESS");

  if (!isAddress(escrowAddress)) {
    throw new Error(
      `ESCROW_ADDRESS is missing/invalid (${escrowAddress}). ` +
        "Set it in backend/.env.development or export ESCROW_ADDRESS."
    );
  }
  console.log(`Using existing Escrow: ${escrowAddress}`);

  const rewardArtifact = await readArtifact("RewardDistributionLegacyFallback", cwd);

  const RewardFactory = new ethers.ContractFactory(
    rewardArtifact.abi,
    rewardArtifact.bytecode,
    wallet
  );

  const reward = await RewardFactory.deploy(escrowAddress);
  await reward.waitForDeployment();
  const rewardAddress = await reward.getAddress();
  console.log(`RewardDistributionLegacyFallback: ${rewardAddress}`);

  let frontendEnv = "";
  try {
    frontendEnv = await fs.readFile(frontendEnvPath, "utf8");
  } catch {
    frontendEnv = "NEXT_PUBLIC_BACKEND_URL=http://localhost:3000\n";
  }
  frontendEnv = updateEnvVar(frontendEnv, "NEXT_PUBLIC_REWARD_ADDRESS", rewardAddress);
  await fs.writeFile(frontendEnvPath, frontendEnv, "utf8");
  console.log("Updated frontend/.env.local");

  let backendEnvUpdated = backendEnvDev;
  backendEnvUpdated = updateEnvVar(
    backendEnvUpdated,
    "REWARD_CONTRACT_ADDRESS",
    rewardAddress
  );
  await fs.writeFile(backendEnvDevPath, backendEnvUpdated, "utf8");
  console.log("Updated backend/.env.development");

  try {
    const backendEnv = await fs.readFile(backendEnvPath, "utf8");
    const backendEnvProdUpdated = updateEnvVar(
      backendEnv,
      "REWARD_CONTRACT_ADDRESS",
      rewardAddress
    );
    await fs.writeFile(backendEnvPath, backendEnvProdUpdated, "utf8");
    console.log("Updated backend/.env");
  } catch {
    // non-fatal
  }

  console.log("\nDone.");
  console.log("Restart backend + frontend.");
  console.log("For task_037 on this new reward contract, run M7a reveal once, then M7c.");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});

