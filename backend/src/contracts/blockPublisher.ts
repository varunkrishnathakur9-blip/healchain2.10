import { JsonRpcProvider, Contract, Wallet } from "ethers";
import { env } from "../config/env.js";
import blockPublisherArtifact from "../../../contracts/artifacts/src/BlockPublisher.sol/BlockPublisher.json" with { type: "json" };

const provider = new JsonRpcProvider(env.RPC_URL);
const signer = new Wallet(env.BACKEND_PRIVATE_KEY, provider);

export const blockPublisher = env.BLOCK_PUBLISHER_ADDRESS
  ? new Contract(env.BLOCK_PUBLISHER_ADDRESS, blockPublisherArtifact.abi, signer)
  : null;

