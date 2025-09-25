const hre = require("hardhat");

async function main() {
  const [deployer] = await hre.ethers.getSigners();

  const ownerAddress = process.env.OWNER_ADDRESS || deployer.address;
  const treasuryAddress = process.env.TREASURY_ADDRESS || ownerAddress;
  const initialSupplyInput = process.env.INITIAL_SUPPLY || "1000000"; // whole tokens

  if (!hre.ethers.isAddress(ownerAddress)) {
    throw new Error("OWNER_ADDRESS is not a valid address");
  }

  if (!hre.ethers.isAddress(treasuryAddress)) {
    throw new Error("TREASURY_ADDRESS is not a valid address");
  }

  const initialSupply = BigInt(initialSupplyInput);

  console.log("\n🚀 Deploying LazyArtCoin with:");
  console.log("   Deployer:", deployer.address);
  console.log("   Owner:", ownerAddress);
  console.log("   Treasury:", treasuryAddress);
  console.log("   Initial supply (whole LAC):", initialSupply.toString());

  const LazyArtCoin = await hre.ethers.getContractFactory("LazyArtCoin");
  const token = await LazyArtCoin.deploy(ownerAddress, treasuryAddress, initialSupply);

  await token.waitForDeployment();

  const address = await token.getAddress();
  console.log("\n✅ LazyArtCoin deployed to:", address);
  console.log("   View on Etherscan once confirmed: https://etherscan.io/address/" + address);

  console.log("\nℹ️ Remember to:");
  console.log("  1. Transfer ownership to a multisig (if desired). Call transferOwnership(newOwner).");
  console.log("  2. Verify the contract: npx hardhat verify --network <network>", address, ownerAddress, treasuryAddress, initialSupply.toString());
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
