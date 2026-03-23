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

async function main() {
  const provider = new ethers.JsonRpcProvider("http://127.0.0.1:7545");

  // Prefer explicit deployer key, then fall back to known local keys.
  const candidateKeys = [];
  if (process.env.DEPLOYER_PRIVATE_KEY) {
    candidateKeys.push(process.env.DEPLOYER_PRIVATE_KEY);
  }
  candidateKeys.push(
    "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
    "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d",
    "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a"
  );

  let wallet = null;
  for (const key of candidateKeys) {
    try {
      const w = new ethers.Wallet(key, provider);
      const bal = await provider.getBalance(await w.getAddress());
      if (bal > 0n) {
        wallet = w;
        break;
      }
    } catch {
      // Continue probing.
    }
  }
  if (!wallet) {
    const rpcAccounts = await provider.send("eth_accounts", []);
    if (Array.isArray(rpcAccounts) && rpcAccounts.length > 0) {
      for (const addr of rpcAccounts) {
        try {
          const bal = await provider.getBalance(addr);
          if (bal > 0n) {
            wallet = await provider.getSigner(addr);
            break;
          }
        } catch {
          // Continue probing.
        }
      }
    }
  }

  if (!wallet) {
    throw new Error(
      "No funded deployer account found on localhost:7545. Set DEPLOYER_PRIVATE_KEY to a funded account."
    );
  }

  const deployer = await wallet.getAddress();

  const artifactPath = path.join(
    process.cwd(),
    "artifacts",
    "src",
    "BlockPublisher.sol",
    "BlockPublisher.json"
  );
  const artifact = JSON.parse(await fs.readFile(artifactPath, "utf8"));

  const factory = new ethers.ContractFactory(
    artifact.abi,
    artifact.bytecode,
    wallet
  );
  const contract = await factory.deploy(deployer, { gasLimit: 5_000_000 });
  await contract.waitForDeployment();
  const address = await contract.getAddress();

  console.log(`BlockPublisher deployed: ${address}`);

  const frontendEnvPath = path.join(
    process.cwd(),
    "..",
    "frontend",
    ".env.local"
  );
  let frontendEnv = "";
  try {
    frontendEnv = await fs.readFile(frontendEnvPath, "utf8");
  } catch {
    frontendEnv = "NEXT_PUBLIC_BACKEND_URL=http://localhost:3000\n";
  }
  frontendEnv = updateEnvVar(
    frontendEnv,
    "NEXT_PUBLIC_BLOCK_PUBLISHER_ADDRESS",
    address
  );
  await fs.writeFile(frontendEnvPath, frontendEnv, "utf8");
  console.log(`Updated frontend/.env.local with NEXT_PUBLIC_BLOCK_PUBLISHER_ADDRESS=${address}`);

  const backendEnvPath = path.join(
    process.cwd(),
    "..",
    "backend",
    ".env.development"
  );
  let backendEnv = "";
  try {
    backendEnv = await fs.readFile(backendEnvPath, "utf8");
  } catch {
    backendEnv = "";
  }
  backendEnv = updateEnvVar(
    backendEnv,
    "BLOCK_PUBLISHER_ADDRESS",
    address
  );
  await fs.writeFile(backendEnvPath, backendEnv, "utf8");
  console.log(`Updated backend/.env.development with BLOCK_PUBLISHER_ADDRESS=${address}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
