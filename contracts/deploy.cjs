const fs = require("node:fs");
const path = require("node:path");
const hre = require("hardhat");

async function main() {
  const network = await hre.ethers.provider.getNetwork();
  const chainId = Number(network.chainId);
  if (![8453, 84532].includes(chainId)) {
    throw new Error("MemoryProofAnchor deployment is restricted to Base chains");
  }
  if (chainId === 8453 && process.env.ALLOW_BASE_MAINNET_DEPLOYMENT !== "true") {
    throw new Error("Set ALLOW_BASE_MAINNET_DEPLOYMENT=true after an explicit mainnet review");
  }
  const [deployer] = await hre.ethers.getSigners();
  if (!deployer) throw new Error("BASE_DEPLOYER_PRIVATE_KEY is not configured");

  const factory = await hre.ethers.getContractFactory("MemoryProofAnchor");
  const contract = await factory.deploy();
  await contract.waitForDeployment();
  const deployment = contract.deploymentTransaction();
  if (!deployment) throw new Error("deployment transaction is missing");
  const receipt = await deployment.wait();
  if (!receipt || receipt.status !== 1) throw new Error("deployment failed");

  const networkName = chainId === 8453 ? "base-mainnet" : "base-sepolia";
  const output = path.resolve(__dirname, "..", "deployments", `${networkName}.json`);
  if (fs.existsSync(output) && process.env.OVERWRITE_DEPLOYMENT !== "true") {
    throw new Error(`Refusing to overwrite ${output}`);
  }
  const record = {
    schema_version: "1.0",
    status: "deployed_unverified_by_submission_gate",
    network: networkName,
    chain_id: chainId,
    contract: "MemoryProofAnchor",
    address: await contract.getAddress(),
    deployment_tx_hash: deployment.hash,
    block_number: receipt.blockNumber,
    deployed_at: new Date().toISOString(),
  };
  fs.mkdirSync(path.dirname(output), { recursive: true });
  fs.writeFileSync(output, `${JSON.stringify(record, null, 2)}\n`, { mode: 0o600 });
  process.stdout.write(`${output}\n`);
}

main().catch((error) => {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
});
