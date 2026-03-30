import { defineConfig } from 'hardhat/config';
import '@nomicfoundation/hardhat-ethers';

export default defineConfig({
  solidity: {
    version: '0.8.28',
    settings: {
      optimizer: { enabled: true, runs: 200 },
      viaIR: true,
      evmVersion: 'london',
    },
  },
  paths: {
    sources: './src',
    tests: './test',
    cache: './cache',
    artifacts: './artifacts',
  },
});
