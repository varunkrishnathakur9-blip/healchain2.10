// src/config/blockchain.ts
import { JsonRpcProvider, Wallet } from "ethers";
import { env } from "./env.js";

export const provider = new JsonRpcProvider(env.RPC_URL, {
  chainId: 1337,
  name: "ganache",
});

export const signer = new Wallet(env.BACKEND_PRIVATE_KEY, provider);
