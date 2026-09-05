// OPERATOR-ONLY testnet deployment. Never called by the API, CI or an LLM.
const fs=require("node:fs");
const path=require("node:path");
const {ethers}=require("hardhat");
async function main(){
  if(process.env.CASEWORK_DEPLOY_APPROVAL!=="base-sepolia-audit-only") throw new Error("Explicit operator approval required; no transaction sent.");
  const network=await ethers.provider.getNetwork();
  if(network.chainId!==84532n) throw new Error("This deployment script is Base Sepolia only.");
  const [operator]=await ethers.getSigners();
  if(!operator) throw new Error("Configure an operator-controlled testnet signer locally; never send secrets to the API.");
  const output=path.join(__dirname,"../deployments/casework-base-sepolia.json");
  if(fs.existsSync(output)) throw new Error("Deployment metadata already exists; inspect it before another deployment.");
  const contract=await(await ethers.getContractFactory("MemoryCaseworkAnchor",operator)).deploy({gasLimit:1000000});
  await contract.waitForDeployment();
  const tx=contract.deploymentTransaction();const receipt=await tx.wait(2);
  const data={chain_id:84532,contract:await contract.getAddress(),deployment_tx:tx.hash,
    block_number:receipt.blockNumber,operator:operator.address,build_commit:process.env.BUILD_COMMIT||null,
    partner_claimed:false,note:"Deployment alone is not an exercised product integration."};
  fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,JSON.stringify(data,null,2)+"\n");
  console.log(JSON.stringify(data,null,2));
}
main().catch(error=>{console.error(error.message);process.exitCode=1;});
