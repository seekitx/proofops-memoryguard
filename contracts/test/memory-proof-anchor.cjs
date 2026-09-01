const { expect } = require("chai");
const { ethers } = require("hardhat");
const { anyValue } = require("@nomicfoundation/hardhat-chai-matchers/withArgs");

describe("MemoryProofAnchor", function () {
  it("anchors one non-empty proof root with its attester and memory version", async function () {
    const [attester] = await ethers.getSigners();
    const anchor = await (await ethers.getContractFactory("MemoryProofAnchor")).deploy();
    const proofRoot = ethers.id("proofops-memoryguard-test-root");

    await expect(anchor.anchor(proofRoot, 3))
      .to.emit(anchor, "MemoryProofAnchored")
      .withArgs(proofRoot, attester.address, 3, anyValue);

    const stored = await anchor.anchors(proofRoot);
    expect(stored.attester).to.equal(attester.address);
    expect(stored.memoryVersion).to.equal(3);
  });

  it("rejects empty and duplicate roots", async function () {
    const anchor = await (await ethers.getContractFactory("MemoryProofAnchor")).deploy();
    await expect(anchor.anchor(ethers.ZeroHash, 1)).to.be.revertedWithCustomError(
      anchor,
      "EmptyProofRoot"
    );
    const root = ethers.id("one-time-root");
    await anchor.anchor(root, 1);
    await expect(anchor.anchor(root, 2)).to.be.revertedWithCustomError(
      anchor,
      "ProofAlreadyAnchored"
    );
  });
});
