import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { JsonRpcProvider } from "ethers";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const contractsRoot = path.resolve(__dirname, "..");
const repoRoot = path.resolve(contractsRoot, "..");

const hardhatArtifactsRoot = path.join(contractsRoot, "artifacts", "src");
const truffleBuildDir = path.join(
  contractsRoot,
  "ganache-truffle",
  "build",
  "contracts"
);
const backendEnvPath = path.join(repoRoot, "backend", ".env.development");
const contractsSrcDir = path.join(contractsRoot, "src");

function parseDotEnv(filePath) {
  const map = new Map();
  if (!fs.existsSync(filePath)) return map;
  const raw = fs.readFileSync(filePath, "utf8");
  for (const lineRaw of raw.split(/\r?\n/)) {
    const line = lineRaw.trim();
    if (!line || line.startsWith("#")) continue;
    const eq = line.indexOf("=");
    if (eq <= 0) continue;
    const key = line.slice(0, eq).trim();
    const value = line.slice(eq + 1).trim();
    map.set(key, value);
  }
  return map;
}

function walkJsonFiles(root) {
  const out = [];
  const stack = [root];
  while (stack.length > 0) {
    const curr = stack.pop();
    if (!curr || !fs.existsSync(curr)) continue;
    for (const ent of fs.readdirSync(curr, { withFileTypes: true })) {
      const full = path.join(curr, ent.name);
      if (ent.isDirectory()) {
        stack.push(full);
      } else if (ent.isFile() && ent.name.endsWith(".json") && ent.name !== "artifacts.d.ts") {
        out.push(full);
      }
    }
  }
  return out;
}

function normalizeAddress(raw) {
  const v = String(raw ?? "").trim();
  if (!/^0x[0-9a-fA-F]{40}$/.test(v)) return null;
  return v;
}

function maybeAddressForContract(contractName, envMap) {
  switch (contractName) {
    case "HealChainEscrow":
      return normalizeAddress(envMap.get("ESCROW_ADDRESS") || envMap.get("ESCROW_CONTRACT_ADDRESS"));
    case "BlockPublisher":
      return normalizeAddress(envMap.get("BLOCK_PUBLISHER_ADDRESS"));
    case "RewardDistribution":
      return normalizeAddress(envMap.get("REWARD_CONTRACT_ADDRESS"));
    case "StakeRegistry":
      return normalizeAddress(envMap.get("STAKE_REGISTRY_ADDRESS"));
    default:
      return null;
  }
}

function tryReadSource(sourceName) {
  if (!sourceName || typeof sourceName !== "string") return { source: "", sourcePath: "" };
  const localSourcePath = path.join(contractsRoot, sourceName.replaceAll("/", path.sep));
  if (fs.existsSync(localSourcePath)) {
    return {
      source: fs.readFileSync(localSourcePath, "utf8"),
      sourcePath: localSourcePath,
    };
  }

  // Fallback for src/... paths
  const shortName = sourceName.startsWith("src/") ? sourceName.slice(4) : sourceName;
  const fallback = path.join(contractsSrcDir, shortName.replaceAll("/", path.sep));
  if (fs.existsSync(fallback)) {
    return {
      source: fs.readFileSync(fallback, "utf8"),
      sourcePath: fallback,
    };
  }

  return { source: "", sourcePath: "" };
}

function asTruffleArtifact(hhArtifact, addressOrNull, deploymentTxHashOrNull) {
  const contractName = String(hhArtifact.contractName || "");
  const sourceName = String(hhArtifact.sourceName || "");
  const { source, sourcePath } = tryReadSource(sourceName);
  const out = {
    contractName,
    abi: Array.isArray(hhArtifact.abi) ? hhArtifact.abi : [],
    metadata: String(hhArtifact.metadata || ""),
    bytecode: String(hhArtifact.bytecode || "0x"),
    deployedBytecode: String(hhArtifact.deployedBytecode || "0x"),
    sourceMap: String(hhArtifact.sourceMap || ""),
    deployedSourceMap: String(hhArtifact.deployedSourceMap || ""),
    source,
    sourcePath,
    ast: hhArtifact.ast || {},
    legacyAST: hhArtifact.legacyAST || {},
    compiler:
      hhArtifact.compiler || {
        name: "solc",
        version: "0.8.19",
      },
    devdoc: hhArtifact.devdoc || {},
    userdoc: hhArtifact.userdoc || {},
    immutableReferences: hhArtifact.immutableReferences || {},
    networks: {},
    schemaVersion: "3.4.16",
    updatedAt: new Date().toISOString(),
    networkType: "ethereum",
  };

  if (addressOrNull) {
    out.networks["1337"] = {
      address: addressOrNull,
      transactionHash: deploymentTxHashOrNull || undefined,
      links: {},
      events: {},
    };
  }

  return out;
}

async function findDeploymentTxByAddress(provider, address, latestBlock) {
  const target = String(address || "").toLowerCase();
  if (!target) return null;

  for (let i = latestBlock; i >= 0; i--) {
    const block = await provider.getBlock(i, true);
    if (!block || !Array.isArray(block.transactions)) continue;
    for (const tx of block.transactions) {
      const receipt = await provider.getTransactionReceipt(tx.hash);
      const created = String(receipt?.contractAddress || "").toLowerCase();
      if (created && created === target) {
        return tx.hash;
      }
    }
  }
  return null;
}

async function main() {
  if (!fs.existsSync(hardhatArtifactsRoot)) {
    throw new Error(`Hardhat artifacts directory not found: ${hardhatArtifactsRoot}`);
  }

  const envMap = parseDotEnv(backendEnvPath);
  const rpcUrl = String(envMap.get("RPC_URL") || "http://127.0.0.1:7545").trim();
  const provider = new JsonRpcProvider(rpcUrl);
  const latestBlock = Number(await provider.getBlockNumber());

  fs.mkdirSync(truffleBuildDir, { recursive: true });

  const files = walkJsonFiles(hardhatArtifactsRoot);
  let converted = 0;
  let withAddress = 0;
  let withTx = 0;

  for (const file of files) {
    const parsed = JSON.parse(fs.readFileSync(file, "utf8"));
    const contractName = String(parsed.contractName || "");
    if (!contractName) continue;

    // Skip interface-only artifacts.
    if (
      contractName.startsWith("I") &&
      (!parsed.bytecode || parsed.bytecode === "0x")
    ) {
      continue;
    }

    const address = maybeAddressForContract(contractName, envMap);
    const deployTxHash =
      address !== null ? await findDeploymentTxByAddress(provider, address, latestBlock) : null;
    if (deployTxHash) withTx += 1;

    const truffleArtifact = asTruffleArtifact(parsed, address, deployTxHash);
    if (address) withAddress += 1;

    const outPath = path.join(truffleBuildDir, `${contractName}.json`);
    fs.writeFileSync(outPath, JSON.stringify(truffleArtifact, null, 2), "utf8");
    converted += 1;
  }

  console.log(
    `[Ganache-Truffle] Export complete: ${converted} artifacts, ${withAddress} with network(1337) addresses, ${withTx} with deployment tx hashes`
  );
  console.log(`[Ganache-Truffle] Output: ${truffleBuildDir}`);
}

await main();
