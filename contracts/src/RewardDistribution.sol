// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

interface IEscrow {
    function escrowBalance(string calldata taskID) external view returns (uint256);
}

contract RewardDistribution is ReentrancyGuard {

    IEscrow public escrow;

    struct Reveal {
        uint256 score;
        bool revealed;
    }

    mapping(string => mapping(address => Reveal)) public minerReveals;
    mapping(string => uint256) public totalScore;
    mapping(string => bool) public accuracyRevealed;
    mapping(string => bool) public rewardsDistributed; // ✅ Fix 3

    event AccuracyRevealed(string indexed taskID, uint256 accuracy);
    event ScoreRevealed(string indexed taskID, address miner, uint256 score);
    event RewardsPaid(string indexed taskID);

    constructor(address escrowAddr) {
        escrow = IEscrow(escrowAddr);
    }

    // =============================================================
    // M7a: Publisher reveals true accuracy (Commit–Reveal)
    // =============================================================
    function revealAccuracy(
        string calldata taskID,
        uint256 accuracy,
        bytes32 nonce,
        bytes32 commitHash
    ) external {

        // ✅ Fix 1: Task must still have active escrow (M6 completed)
        require(
            escrow.escrowBalance(taskID) > 0,
            "Task not active or escrow empty"
        );

        require(
            keccak256(abi.encodePacked(accuracy, nonce)) == commitHash,
            "Invalid accuracy reveal"
        );

        accuracyRevealed[taskID] = true;
        emit AccuracyRevealed(taskID, accuracy);
    }

    // =============================================================
    // M7b: Miner reveals contribution score
    // =============================================================
    function revealScore(
        string calldata taskID,
        uint256 score,
        bytes32 nonce,
        bytes32 scoreCommit
    ) external {

        require(accuracyRevealed[taskID], "TP not revealed");
        require(!minerReveals[taskID][msg.sender].revealed, "Already revealed");

        bytes32 expected =
            keccak256(abi.encodePacked(score, nonce, taskID, msg.sender));

        require(expected == scoreCommit, "Invalid score reveal");

        /*
         * IMPORTANT:
         * The inclusion of scoreCommit in the published block
         * is verified off-chain by the backend (M5 consensus).
         * On-chain verification is intentionally omitted to
         * avoid gas-expensive loops.
         */

        minerReveals[taskID][msg.sender] = Reveal(score, true);
        totalScore[taskID] += score;

        emit ScoreRevealed(taskID, msg.sender, score);
    }

    // =============================================================
    // M7c: Proportional reward distribution
    // =============================================================
    function distribute(
        string calldata taskID,
        address[] calldata miners
    ) external nonReentrant {

        require(!rewardsDistributed[taskID], "Rewards already distributed"); // ✅ Fix 3
        require(accuracyRevealed[taskID], "Accuracy not revealed");

        uint256 rewardPool = escrow.escrowBalance(taskID);
        require(rewardPool > 0, "No reward");
        require(totalScore[taskID] > 0, "No scores");

        uint256 length = miners.length;

        for (uint256 i = 0; i < length; ) {
            Reveal memory r = minerReveals[taskID][miners[i]];
            if (r.revealed && r.score > 0) {
                uint256 share =
                    (rewardPool * r.score) / totalScore[taskID];

                (bool ok, ) = payable(miners[i]).call{value: share}("");
                require(ok, "Transfer failed");
            }
            unchecked { ++i; }
        }

        rewardsDistributed[taskID] = true; // ✅ Fix 3
        emit RewardsPaid(taskID);
    }
}
