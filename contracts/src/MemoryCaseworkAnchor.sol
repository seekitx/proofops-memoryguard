// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @notice Audit-only digest attestations. Not payment or policy authorization.
/// @dev Separate contract from v1: never overwrite a historical deployment address.
contract MemoryCaseworkAnchor {
    error WrongChain();
    error EmptyProofRoot();
    error EmptyMemoryVersion();
    error ConflictingVersion();

    struct Anchor {
        uint64 memoryVersion;
        uint64 anchoredAt;
    }
    // An unrelated wallet cannot squat another attester's proof-root key.
    mapping(address => mapping(bytes32 => Anchor)) public anchors;
    event MemoryProofAnchored(bytes32 indexed proofRoot, address indexed attester,
                              uint64 memoryVersion, uint64 anchoredAt);

    constructor() {
        if (block.chainid != 8453 && block.chainid != 84532 && block.chainid != 31337)
            revert WrongChain();
    }
    function anchor(bytes32 proofRoot, uint64 memoryVersion) external {
        if (proofRoot == bytes32(0)) revert EmptyProofRoot();
        if (memoryVersion == 0) revert EmptyMemoryVersion();
        Anchor storage record = anchors[msg.sender][proofRoot];
        if (record.memoryVersion != 0) {
            if (record.memoryVersion != memoryVersion) revert ConflictingVersion();
            emit MemoryProofAnchored(proofRoot, msg.sender, memoryVersion, record.anchoredAt);
            return;
        }
        record.memoryVersion = memoryVersion;
        record.anchoredAt = uint64(block.timestamp);
        emit MemoryProofAnchored(proofRoot, msg.sender, memoryVersion, record.anchoredAt);
    }
}
