import "dotenv/config";
import "@nomicfoundation/hardhat-ethers";

/** @type {import("hardhat/config").HardhatUserConfig} */
const config = {
  // --------------------------------------------------
  // Default network
  // --------------------------------------------------
  defaultNetwork: "hardhat",

  // --------------------------------------------------
  // Project structure
  // --------------------------------------------------
  paths: {
    sources: "./src",
    tests: "./test",
    cache: "./cache",
    artifacts: "./artifacts",
  },

  // --------------------------------------------------
  // Solidity compiler
  // --------------------------------------------------
  solidity: {
    version: "0.8.28",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200,
      },
      evmVersion: "london", // Use London EVM version for Ganache compatibility
    },
  },

  // --------------------------------------------------
  // Networks (Hardhat v3 REQUIRED format)
  // --------------------------------------------------
  networks: {
    hardhat: {
      type: "edr-simulated",
      chainId: 31337,
      // Hardhat network automatically provides accounts
      // Note: To run 'npx hardhat node' on a different port, use: npx hardhat node --port 7545
      // However, if using Ganache, you don't need to run 'npx hardhat node' at all
    },

    localhost: {
      type: "http",
      url: "http://127.0.0.1:7545",
      chainId: 1337,
      // Add accounts for localhost network
      accounts: process.env.DEPLOYER_PRIVATE_KEY
        ? [process.env.DEPLOYER_PRIVATE_KEY]
        : [
            // Default development accounts (replace with your own)
            "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
            "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690",
            "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a",
          ],
    },

    sepolia: {
      type: "http",
      url: process.env.SEPOLIA_RPC_URL ?? "",
      chainId: 11155111,
      accounts: process.env.DEPLOYER_PRIVATE_KEY
        ? [process.env.DEPLOYER_PRIVATE_KEY]
        : [],
    },
  },
};

export default config;