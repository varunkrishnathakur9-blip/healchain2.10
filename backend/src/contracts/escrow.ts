// src/contracts/escrow.ts
import { JsonRpcProvider, Contract, Wallet } from "ethers";
import { env } from "../config/env.js";
// adjust the path if needed

import escrowArtifact from "../../../contracts/artifacts/src/HealChainEscrow.sol/HealChainEscrow.json" with { type: "json" };

const provider = new JsonRpcProvider(env.RPC_URL);
const signer = new Wallet(env.BACKEND_PRIVATE_KEY, provider);

const ESCROW_ADDRESS = env.ESCROW_ADDRESS; // put this in .env.development / .env.production

export const escrow = new Contract(
  ESCROW_ADDRESS,
  escrowArtifact.abi,
  signer
);