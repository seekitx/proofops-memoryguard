const { expect } = require("chai");
const { ethers } = require("hardhat");
describe("MemoryCaseworkAnchor audit-only boundaries", function () {
  it("isolates attesters and permits exact retries, not conflicting versions", async function () {
    const [alice,bob] = await ethers.getSigners();
    const anchor = await (await ethers.getContractFactory("MemoryCaseworkAnchor")).deploy();
    const root = ethers.id("casework-digest");
    await anchor.connect(bob).anchor(root,7);
    await anchor.connect(alice).anchor(root,2);
    expect((await anchor.anchors(alice.address,root)).memoryVersion).to.equal(2);
    expect((await anchor.anchors(bob.address,root)).memoryVersion).to.equal(7);
    await expect(anchor.connect(alice).anchor(root,2)).to.emit(anchor,"MemoryProofAnchored");
    await expect(anchor.connect(alice).anchor(root,3)).to.be.revertedWithCustomError(anchor,"ConflictingVersion");
  });
  it("rejects empty roots, zero versions, and value transfers", async function () {
    const anchor=await(await ethers.getContractFactory("MemoryCaseworkAnchor")).deploy();
    await expect(anchor.anchor(ethers.ZeroHash,1)).to.be.revertedWithCustomError(anchor,"EmptyProofRoot");
    await expect(anchor.anchor(ethers.id("x"),0)).to.be.revertedWithCustomError(anchor,"EmptyMemoryVersion");
    await expect(anchor.anchor(ethers.id("x"),1,{value:1})).to.be.reverted;
  });
});
