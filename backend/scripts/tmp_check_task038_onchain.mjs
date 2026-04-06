import { Contract, JsonRpcProvider } from "ethers";
import { prisma } from "../dist/config/database.config.js";

const provider = new JsonRpcProvider("http://127.0.0.1:7545");
const abi = [
  "function getBlockMeta(string taskID) view returns (bytes32 modelHash, uint256 accuracy, address aggregator, uint256 timestamp, uint256 revealDeadline, bool distributed)",
  "function getParticipants(string taskID) view returns (address[] participants)",
  "function getScoreCommits(string taskID) view returns (bytes32[] scoreCommits)",
];
const blockPublisher = new Contract("0xe85e41c27D00bFec396b9E5Ae18D8AadF888D817", abi, provider);

const taskID = "task_038";
const meta = await blockPublisher.getBlockMeta(taskID);
const participants = await blockPublisher.getParticipants(taskID);
const commits = await blockPublisher.getScoreCommits(taskID);

const task = await prisma.task.findUnique({ where: { taskID }, select: { status: true, publishTx: true, aggregatorAddress: true } });
const block = await prisma.block.findUnique({ where: { taskID }, select: { modelHash: true, accuracy: true, candidateHash: true, round: true } });

console.log(JSON.stringify({
  onChain: {
    modelHash: String(meta[0]),
    accuracy: meta[1].toString(),
    aggregator: String(meta[2]),
    timestamp: meta[3].toString(),
    revealDeadline: meta[4].toString(),
    distributed: Boolean(meta[5]),
    participants: participants.map((p) => String(p)),
    scoreCommitsCount: commits.length,
  },
  backend: {
    task,
    block: block ? { ...block, accuracy: block.accuracy?.toString?.() ?? block.accuracy } : null,
  },
}, null, 2));

await prisma.$disconnect();
