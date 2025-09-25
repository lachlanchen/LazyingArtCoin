require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config();

const {
  MAINNET_RPC_URL,
  SEPOLIA_RPC_URL,
  DEPLOYER_PRIVATE_KEY,
  ETHERSCAN_API_KEY
} = process.env;

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  solidity: {
    version: "0.8.24",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200
      }
    }
  },
  networks: {
    hardhat: {
      chainId: 31337
    },
    mainnet: {
      url: MAINNET_RPC_URL || "https://mainnet.infura.io/v3/YOUR_KEY",
      accounts: DEPLOYER_PRIVATE_KEY ? [DEPLOYER_PRIVATE_KEY] : [],
      chainId: 1
    },
    sepolia: {
      url: SEPOLIA_RPC_URL || "https://sepolia.infura.io/v3/YOUR_KEY",
      accounts: DEPLOYER_PRIVATE_KEY ? [DEPLOYER_PRIVATE_KEY] : [],
      chainId: 11155111
    }
  },
  etherscan: {
    apiKey: ETHERSCAN_API_KEY || ""
  }
};
