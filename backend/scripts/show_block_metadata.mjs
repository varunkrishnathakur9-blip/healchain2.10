import path from "path";
import { fileURLToPath } from "url";

import dotenv from "dotenv";
import { Contract, JsonRpcProvider } from "ethers";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const backendRoot = path.resolve(__dirname, "..");

dotenv.config({ path: path.join(backendRoot, ".env.development"), override: true });
dotenv.config({ path: path.join(backendRoot, ".env"), override: false });

const taskID = String(process.argv[2] || "").trim();
if (!taskID) {
  console.error("Usage: node scripts/show_block_metadata.mjs <taskID>");
  process.exit(1);
}

const rpcUrl = String(process.env.RPC_URL || "http://127.0.0.1:7545").trim();
const blockPublisherAddress = String(process.env.BLOCK_PUBLISHER_ADDRESS || "").trim();
if (!blockPublisherAddress) {
  console.error("Missing BLOCK_PUBLISHER_ADDRESS in backend environment.");
  process.exit(1);
}

const abi = [
  "function getBlockMeta(string taskID) view returns (bytes32 modelHash, uint256 accuracy, address aggregator, uint256 timestamp, uint256 revealDeadline, bool distributed)",
  "function getParticipants(string taskID) view returns (address[] participants)",
  "function getScoreCommits(string taskID) view returns (bytes32[] scoreCommits)",
];

function toIsoMaybe(secondsLike) {
  const seconds = Number(secondsLike);
  if (!Number.isFinite(seconds) || seconds <= 0) return null;
  return new Date(seconds * 1000).toISOString();
}

async function main() {
  const provider = new JsonRpcProvider(rpcUrl);
  const blockPublisher = new Contract(blockPublisherAddress, abi, provider);

  try {
    const meta = await blockPublisher.getBlockMeta(taskID);
    const participants = await blockPublisher.getParticipants(taskID);
    const scoreCommits = await blockPublisher.getScoreCommits(taskID);

    const result = {
      taskID,
      network: {
        rpcUrl,
        blockPublisherAddress,
      },
      blockMeta: {
        modelHash: String(meta[0]),
        accuracyScaled: String(meta[1]),
        accuracyFloat: Number(meta[1]) / 1_000_000,
        aggregator: String(meta[2]),
        timestamp: String(meta[3]),
        timestampISO: toIsoMaybe(meta[3]),
        revealDeadline: String(meta[4]),
        revealDeadlineISO: toIsoMaybe(meta[4]),
        distributed: Boolean(meta[5]),
      },
      participants: participants.map((p) => String(p)),
      scoreCommits: scoreCommits.map((s) => String(s)),
    };

    console.log(JSON.stringify(result, null, 2));
  } catch (err) {
    const message = String(err?.shortMessage || err?.message || err);
    console.error(
      JSON.stringify(
        {
          taskID,
          network: {
            rpcUrl,
            blockPublisherAddress,
          },
          error: message,
          hint:
            "If this says execution reverted, block is likely not published for this task on this BlockPublisher address.",
        },
        null,
        2
      )
    );
    process.exit(2);
  }
}

await main();

