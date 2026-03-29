// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/access/Ownable.sol";

contract BlockPublisher is Ownable {

    // 🔹 Correct OZ v5 Ownable constructor
    constructor(address initialOwner) Ownable(initialOwner) {}

    uint256 public constant PUBLISHER_REVEAL_WINDOW = 1 days;
    address public rewardDistributor;

    modifier onlyRewardDistributor() {
        require(msg.sender == rewardDistributor, "Only reward distributor");
        _;
    }

    // 🔹 Struct must be OUTSIDE of constructor
    struct BlockRecord {
        string taskID;
        bytes32 modelHash;           
        uint256 accuracy;
        address aggregator;
        address[] participants;
        bytes32[] scoreCommits;      
        uint256 timestamp;
        uint256 revealDeadline;
        bool distributed;
    }

    mapping(string => BlockRecord) public publishedBlocks;

    event BlockPublished(
        string indexed taskID,
        bytes32 modelHash,
        uint256 accuracy,
        address aggregator,
        uint256 revealDeadline
    );
    event RewardDistributorUpdated(address indexed rewardDistributor);
    event BlockDistributionMarked(string indexed taskID);

    function setRewardDistributor(address distributor) external onlyOwner {
        require(distributor != address(0), "Invalid distributor");
        rewardDistributor = distributor;
        emit RewardDistributorUpdated(distributor);
    }

    // M6: Publish aggregated model block
    function publishBlock(
        string calldata taskID,
        bytes32 modelHash,
        uint256 accuracy,
        address[] calldata participants,
        bytes32[] calldata scoreCommits
    ) external {

        require(publishedBlocks[taskID].timestamp == 0, "Block exists");
        require(modelHash != bytes32(0), "Invalid model hash");
        require(participants.length > 0, "No participants");
        require(
            scoreCommits.length == participants.length,
            "Participants/scoreCommits length mismatch"
        );

        publishedBlocks[taskID] = BlockRecord({
            taskID: taskID,
            modelHash: modelHash,
            accuracy: accuracy,
            aggregator: msg.sender,
            participants: participants,
            scoreCommits: scoreCommits,
            timestamp: block.timestamp,
            revealDeadline: block.timestamp + PUBLISHER_REVEAL_WINDOW,
            distributed: false
        });

        emit BlockPublished(
            taskID,
            modelHash,
            accuracy,
            msg.sender,
            block.timestamp + PUBLISHER_REVEAL_WINDOW
        );
    }

    function getScoreCommits(string calldata taskID)
        external
        view
        returns (bytes32[] memory)
    {
        return publishedBlocks[taskID].scoreCommits;
    }

    function getParticipants(string calldata taskID)
        external
        view
        returns (address[] memory)
    {
        return publishedBlocks[taskID].participants;
    }

    function getBlockMeta(string calldata taskID)
        external
        view
        returns (
            bytes32 modelHash,
            uint256 accuracy,
            address aggregator,
            uint256 timestamp,
            uint256 revealDeadline,
            bool distributed
        )
    {
        BlockRecord storage b = publishedBlocks[taskID];
        return (
            b.modelHash,
            b.accuracy,
            b.aggregator,
            b.timestamp,
            b.revealDeadline,
            b.distributed
        );
    }

    function markDistributed(string calldata taskID) external onlyRewardDistributor {
        BlockRecord storage b = publishedBlocks[taskID];
        require(b.timestamp != 0, "Block missing");
        require(!b.distributed, "Already distributed");
        b.distributed = true;
        emit BlockDistributionMarked(taskID);
    }
}
