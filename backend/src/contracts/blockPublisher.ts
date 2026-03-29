import { JsonRpcProvider, Contract, Wallet } from "ethers";
import { env } from "../config/env.js";

const provider = new JsonRpcProvider(env.RPC_URL);
const signer = new Wallet(env.BACKEND_PRIVATE_KEY, provider);

const BLOCK_PUBLISHER_ABI = [
  "function publishBlock(string taskID, bytes32 modelHash, uint256 accuracy, address[] participants, bytes32[] scoreCommits) external",
  "function getBlockMeta(string taskID) view returns (bytes32 modelHash, uint256 accuracy, address aggregator, uint256 timestamp, uint256 revealDeadline, bool distributed)",
  "function getParticipants(string taskID) view returns (address[] participants)",
  "function getScoreCommits(string taskID) view returns (bytes32[] scoreCommits)",
];

export const blockPublisher = env.BLOCK_PUBLISHER_ADDRESS
  ? new Contract(env.BLOCK_PUBLISHER_ADDRESS, BLOCK_PUBLISHER_ABI, signer)
  : null;
