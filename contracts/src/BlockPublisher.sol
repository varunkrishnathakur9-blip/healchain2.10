// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/access/Ownable.sol";

contract BlockPublisher is Ownable {

    // 🔹 Correct OZ v5 Ownable constructor
    constructor(address initialOwner) Ownable(initialOwner) {}

    // 🔹 Struct must be OUTSIDE of constructor
    struct BlockRecord {
        string taskID;
        bytes32 modelHash;           
        uint256 accuracy;
        address aggregator;
        bytes32[] scoreCommits;      
        uint256 timestamp;
    }

    mapping(string => BlockRecord) public publishedBlocks;

    event BlockPublished(
        string indexed taskID,
        bytes32 modelHash,
        uint256 accuracy,
        address aggregator
    );

    // M6: Publish aggregated model block
    function publishBlock(
        string calldata taskID,
        bytes32 modelHash,
        uint256 accuracy,
        bytes32[] calldata scoreCommits
    ) external {

        require(publishedBlocks[taskID].timestamp == 0, "Block exists");

        publishedBlocks[taskID] = BlockRecord({
            taskID: taskID,
            modelHash: modelHash,
            accuracy: accuracy,
            aggregator: msg.sender,
            scoreCommits: scoreCommits,
            timestamp: block.timestamp
        });

        emit BlockPublished(taskID, modelHash, accuracy, msg.sender);
    }

    function getScoreCommits(string calldata taskID)
        external
        view
        returns (bytes32[] memory)
    {
        return publishedBlocks[taskID].scoreCommits;
    }
}
