import { JsonRpcProvider, Contract, Wallet } from "ethers";
import { env } from "../config/env.js";

const provider = new JsonRpcProvider(env.RPC_URL);
const signer = new Wallet(env.BACKEND_PRIVATE_KEY, provider);

// Minimal ABI: we only need M7c entrypoints from backend.
const REWARD_DISTRIBUTION_ABI = [
  "function distribute(string taskID) external",
  "function distribute(string taskID, address[] miners) external",
  "function rewardsDistributed(string taskID) external view returns (bool)",
  "function minerReveals(string taskID, address miner) external view returns (uint256 score, bool revealed)",
];

export const rewardDistribution = env.REWARD_CONTRACT_ADDRESS
  ? new Contract(env.REWARD_CONTRACT_ADDRESS, REWARD_DISTRIBUTION_ABI, signer)
  : null;
