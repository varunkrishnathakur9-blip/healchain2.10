// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

interface IEscrow {
    function escrowBalance(string calldata taskID) external view returns (uint256);
    function taskPublisher(string calldata taskID) external view returns (address);
    function taskAccuracyCommit(string calldata taskID) external view returns (bytes32);
    function releaseReward(string calldata taskID, address recipient, uint256 amount) external;
}

interface IBlockPublisher {
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
        );

    function getParticipants(string calldata taskID) external view returns (address[] memory);
    function getScoreCommits(string calldata taskID) external view returns (bytes32[] memory);
    function markDistributed(string calldata taskID) external;
}

contract RewardDistribution is ReentrancyGuard {
    IEscrow public escrow;
    IBlockPublisher public blockPublisher;

    // Algorithm-7 runtime knobs
    uint256 public immutable SCORE_REVEAL_WINDOW;
    uint256 public immutable DISPUTE_GRACE;
    uint16 public immutable AGGREGATOR_SHARE_BPS;

    struct Reveal {
        uint256 score;
        bool revealed;
    }

    mapping(string => mapping(address => Reveal)) public minerReveals;
    mapping(string => uint256) public totalScore;
    mapping(string => bool) public accuracyRevealed;
    mapping(string => bool) public rewardsDistributed;
    mapping(string => uint256) public minersRevealDeadline;
    mapping(string => uint256) public revealedAccuracy;

    event AccuracyRevealed(string indexed taskID, uint256 accuracy);
    event ScoreRevealed(string indexed taskID, address miner, uint256 score);
    event RewardsDistributed(string indexed taskID, uint256 totalReward, uint256 aggregatorReward);
    event RewardsPaid(string indexed taskID);

    constructor(
        address escrowAddr,
        address blockPublisherAddr,
        uint256 scoreRevealWindowSec,
        uint256 disputeGraceSec,
        uint16 aggregatorShareBps
    ) {
        require(escrowAddr != address(0), "Invalid escrow");
        require(blockPublisherAddr != address(0), "Invalid block publisher");
        require(aggregatorShareBps <= 10_000, "Invalid aggregator share");

        escrow = IEscrow(escrowAddr);
        blockPublisher = IBlockPublisher(blockPublisherAddr);
        SCORE_REVEAL_WINDOW = scoreRevealWindowSec == 0 ? 1 days : scoreRevealWindowSec;
        DISPUTE_GRACE = disputeGraceSec == 0 ? 1 days : disputeGraceSec;
        AGGREGATOR_SHARE_BPS = aggregatorShareBps;
    }

    // =============================================================
    // M7a: Publisher reveals true accuracy (Commit-Reveal)
    // =============================================================
    function revealAccuracy(
        string calldata taskID,
        uint256 accuracy,
        bytes32 nonce,
        bytes32 commitHash // kept for frontend compatibility; checked against stored commit when provided
    ) external {
        (
            bytes32 modelHash,
            ,
            ,
            ,
            uint256 revealDeadline,
            bool distributed
        ) = blockPublisher.getBlockMeta(taskID);

        require(modelHash != bytes32(0), "No published block");
        require(!distributed, "Block already distributed");
        require(block.timestamp < revealDeadline, "Publisher reveal window closed");

        address publisher = escrow.taskPublisher(taskID);
        require(publisher != address(0), "Unknown task");
        require(msg.sender == publisher, "Only publisher");

        bytes32 expectedCommit = escrow.taskAccuracyCommit(taskID);
        require(expectedCommit != bytes32(0), "Missing task commit");

        bytes32 computedCommit = keccak256(abi.encodePacked(accuracy, nonce));
        require(computedCommit == expectedCommit, "Invalid accuracy reveal");
        if (commitHash != bytes32(0)) {
            require(commitHash == expectedCommit, "Commit mismatch");
        }

        accuracyRevealed[taskID] = true;
        revealedAccuracy[taskID] = accuracy;
        minersRevealDeadline[taskID] = block.timestamp + SCORE_REVEAL_WINDOW;

        emit AccuracyRevealed(taskID, accuracy);
    }

    // =============================================================
    // M7b: Miner reveals contribution score
    // =============================================================
    function revealScore(
        string calldata taskID,
        uint256 score,
        bytes32 nonce,
        bytes32 scoreCommit // kept for frontend compatibility; strict check is against on-chain block commit
    ) external {
        (bytes32 modelHash, , , , , bool distributed) = blockPublisher.getBlockMeta(taskID);
        require(modelHash != bytes32(0), "No published block");
        require(!distributed, "Block already distributed");
        require(accuracyRevealed[taskID], "Publisher not revealed");
        require(
            block.timestamp < minersRevealDeadline[taskID],
            "Miner reveal window closed"
        );
        require(!minerReveals[taskID][msg.sender].revealed, "Already revealed");

        bytes32 expected = keccak256(abi.encodePacked(score, nonce, taskID, msg.sender));
        if (scoreCommit != bytes32(0)) {
            require(scoreCommit == expected, "scoreCommit arg mismatch");
        }

        address[] memory participants = blockPublisher.getParticipants(taskID);
        bytes32[] memory commits = blockPublisher.getScoreCommits(taskID);
        require(participants.length > 0, "No participants");
        require(participants.length == commits.length, "Block commits mismatch");

        uint256 idx = _participantIndex(participants, msg.sender);
        require(expected == commits[idx], "Invalid score reveal");

        minerReveals[taskID][msg.sender] = Reveal(score, true);
        totalScore[taskID] += score;

        emit ScoreRevealed(taskID, msg.sender, score);
    }

    // =============================================================
    // M7c: Proportional reward distribution
    // =============================================================
    function distribute(string calldata taskID) external nonReentrant {
        _distribute(taskID);
    }

    // Backward-compatible overload used by existing frontend calls.
    function distribute(
        string calldata taskID,
        address[] calldata /*miners*/
    ) external nonReentrant {
        _distribute(taskID);
    }

    function _distribute(string calldata taskID) internal {
        (
            bytes32 modelHash,
            ,
            address aggregator,
            ,
            uint256 revealDeadline,
            bool blockDistributed
        ) = blockPublisher.getBlockMeta(taskID);

        require(modelHash != bytes32(0), "No published block");
        require(!blockDistributed, "Block already distributed");
        require(!rewardsDistributed[taskID], "Rewards already distributed");
        require(accuracyRevealed[taskID], "Accuracy not revealed");
        require(
            block.timestamp > revealDeadline + DISPUTE_GRACE,
            "Dispute grace not elapsed"
        );

        uint256 rewardPool = escrow.escrowBalance(taskID);
        require(rewardPool > 0, "No reward");

        address[] memory participants = blockPublisher.getParticipants(taskID);
        require(participants.length > 0, "No participants");

        uint256 revealedTotal = 0;
        for (uint256 i = 0; i < participants.length; ) {
            Reveal memory r = minerReveals[taskID][participants[i]];
            if (r.revealed && r.score > 0) {
                revealedTotal += r.score;
            }
            unchecked {
                ++i;
            }
        }

        uint256 aggregatorReward = (rewardPool * AGGREGATOR_SHARE_BPS) / 10_000;
        uint256 remaining = rewardPool - aggregatorReward;
        uint256 paidToParticipants = revealedTotal == 0
            ? _distributeFallbackEqual(taskID, participants, remaining)
            : _distributeProportional(taskID, participants, remaining, revealedTotal);

        // Carry rounding residue + configured aggregator cut to aggregator.
        uint256 participantResidue = remaining - paidToParticipants;
        uint256 finalAggregatorReward = aggregatorReward + participantResidue;
        if (finalAggregatorReward > 0) {
            require(aggregator != address(0), "Invalid aggregator");
            escrow.releaseReward(taskID, aggregator, finalAggregatorReward);
        }

        rewardsDistributed[taskID] = true;
        blockPublisher.markDistributed(taskID);

        emit RewardsDistributed(taskID, rewardPool, finalAggregatorReward);
        emit RewardsPaid(taskID);
    }

    function _distributeFallbackEqual(
        string calldata taskID,
        address[] memory participants,
        uint256 remaining
    ) internal returns (uint256 paidToParticipants) {
        // Fallback distribution (Algorithm 7): equal split among participants.
        uint256 equalShare = remaining / participants.length;
        if (equalShare == 0) {
            return 0;
        }

        for (uint256 i = 0; i < participants.length; ) {
            escrow.releaseReward(taskID, participants[i], equalShare);
            paidToParticipants += equalShare;
            unchecked {
                ++i;
            }
        }
    }

    function _distributeProportional(
        string calldata taskID,
        address[] memory participants,
        uint256 remaining,
        uint256 revealedTotal
    ) internal returns (uint256 paidToParticipants) {
        for (uint256 i = 0; i < participants.length; ) {
            Reveal memory r = minerReveals[taskID][participants[i]];
            if (r.revealed && r.score > 0) {
                uint256 share = (remaining * r.score) / revealedTotal;
                if (share > 0) {
                    escrow.releaseReward(taskID, participants[i], share);
                    paidToParticipants += share;
                }
            }
            unchecked {
                ++i;
            }
        }
    }

    function _participantIndex(address[] memory participants, address miner)
        internal
        pure
        returns (uint256)
    {
        for (uint256 i = 0; i < participants.length; ) {
            if (participants[i] == miner) {
                return i;
            }
            unchecked {
                ++i;
            }
        }
        revert("Miner not in participants");
    }
}
