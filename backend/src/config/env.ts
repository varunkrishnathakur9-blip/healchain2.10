// src/config/env.ts
import dotenv from "dotenv";
import { isAddress, isHexString } from "ethers";

dotenv.config({
  path:
    process.env.NODE_ENV === "production"
      ? ".env.production"
      : ".env.development",
});

function requireEnv(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing required env var: ${name}`);
  }
  return value;
}

function requirePrivateKey(name: string): string {
  const value = requireEnv(name);
  if (!isHexString(value, 32)) {
    throw new Error(`Invalid private key for ${name}`);
  }
  return value;
}

function requireAddress(name: string): string {
  const value = requireEnv(name);
  if (!isAddress(value)) {
    throw new Error(`Invalid Ethereum address for ${name}`);
  }
  return value;
}

function optionalAddress(name: string): string | undefined {
  const value = process.env[name];
  if (!value) {
    return undefined;
  }
  if (!isAddress(value)) {
    throw new Error(`Invalid Ethereum address for ${name}`);
  }
  return value;
}

export const env = {
  NODE_ENV: process.env.NODE_ENV ?? "development",
  PORT: Number(process.env.PORT ?? 3000),

  DATABASE_URL: requireEnv("DATABASE_URL"),
  RPC_URL: requireEnv("RPC_URL"),

  BACKEND_PRIVATE_KEY: requirePrivateKey("BACKEND_PRIVATE_KEY"),
  ESCROW_ADDRESS: requireAddress("ESCROW_ADDRESS"),
  STAKE_REGISTRY_ADDRESS: optionalAddress("STAKE_REGISTRY_ADDRESS"), // Optional: can be undefined if not deployed yet
};
