// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title MemoryProofAnchor
/// @notice Anchors only a MemoryGuard proof root and minimal public metadata.
/// @dev Raw memory, support-ticket text, wallet secrets and customer identifiers
///      must never be sent to this contract.
contract MemoryProofAnchor {
    error EmptyProofRoot();
    error ProofAlreadyAnchored();

    struct Anchor {
        address attester;
        uint64 memoryVersion;
        uint64 anchoredAt;
    }

    mapping(bytes32 proofRoot => Anchor anchorRecord) public anchors;

    event MemoryProofAnchored(
        bytes32 indexed proofRoot,
        address indexed attester,
        uint64 memoryVersion,
        uint64 anchoredAt
    );

    function anchor(bytes32 proofRoot, uint64 memoryVersion) external {
        if (proofRoot == bytes32(0)) revert EmptyProofRoot();
        if (anchors[proofRoot].attester != address(0)) revert ProofAlreadyAnchored();

        uint64 anchoredAt = uint64(block.timestamp);
        anchors[proofRoot] = Anchor({
            attester: msg.sender,
            memoryVersion: memoryVersion,
            anchoredAt: anchoredAt
        });
        emit MemoryProofAnchored(proofRoot, msg.sender, memoryVersion, anchoredAt);
    }
}
