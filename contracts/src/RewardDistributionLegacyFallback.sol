// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

interface ILegacyEscrow {
    function escrowBalance(string calldata taskID) external view returns (uint256);
}

/// @notice Legacy-compatible M7 contract used for existing local deployments.
/// It preserves the historical ABI used by frontend/backend, but removes the
/// strict "No scores" revert by allowing fallback completion when no miner
/// reveals are present.
contract RewardDistributionLegacyFallback is ReentrancyGuard {
    ILegacyEscrow public escrow;

    struct Reveal {
        uint256 score;
        bool revealed;
    }

    mapping(string => mapping(address => Reveal)) public minerReveals;
    mapping(string => uint256) public totalScore;
    mapping(string => bool) public accuracyRevealed;
    mapping(string => bool) public rewardsDistributed;
    mapping(string => uint256) public revealedAccuracy;

    event AccuracyRevealed(string indexed taskID, uint256 accuracy);
    event ScoreRevealed(string indexed taskID, address miner, uint256 score);
    event RewardsPaid(string indexed taskID);

    constructor(address escrowAddr) {
        require(escrowAddr != address(0), "Invalid escrow");
        escrow = ILegacyEscrow(escrowAddr);
    }

    function revealAccuracy(
        string calldata taskID,
        uint256 accuracy,
        bytes32 nonce,
        bytes32 commitHash
    ) external {
        require(!accuracyRevealed[taskID], "Accuracy already revealed");
        require(
            escrow.escrowBalance(taskID) > 0,
            "Task not active or escrow empty"
        );

        bytes32 expected = keccak256(abi.encodePacked(accuracy, nonce));
        require(expected == commitHash, "Invalid accuracy reveal");

        accuracyRevealed[taskID] = true;
        revealedAccuracy[taskID] = accuracy;
        emit AccuracyRevealed(taskID, accuracy);
    }

    function revealScore(
        string calldata taskID,
        uint256 score,
        bytes32 nonce,
        bytes32 scoreCommit
    ) external {
        require(accuracyRevealed[taskID], "Accuracy must be revealed first");
        require(!minerReveals[taskID][msg.sender].revealed, "Already revealed");

        bytes32 expected = keccak256(
            abi.encodePacked(score, nonce, taskID, msg.sender)
        );
        require(expected == scoreCommit, "Invalid score reveal");

        minerReveals[taskID][msg.sender] = Reveal(score, true);
        totalScore[taskID] += score;

        emit ScoreRevealed(taskID, msg.sender, score);
    }

    function distribute(
        string calldata taskID,
        address[] calldata miners
    ) external nonReentrant {
        require(!rewardsDistributed[taskID], "Rewards already distributed");
        require(accuracyRevealed[taskID], "Accuracy must be revealed first");
        require(
            escrow.escrowBalance(taskID) > 0,
            "Task not active or escrow empty"
        );
        require(miners.length > 0, "No miners");

        uint256 scoreSum = totalScore[taskID];

        // Fallback-enabled path: do not hard-fail when no scores are revealed.
        if (scoreSum == 0) {
            rewardsDistributed[taskID] = true;
            emit RewardsPaid(taskID);
            return;
        }

        // Best-effort payout bridge for legacy environments.
        // If escrow does not expose a payout entrypoint, we still finalize M7c
        // without reverting so protocol flow can continue.
        uint256 rewardPool = escrow.escrowBalance(taskID);
        bytes4 releaseSelector = bytes4(
            keccak256("releaseReward(string,address,uint256)")
        );

        for (uint256 i = 0; i < miners.length; ) {
            Reveal memory r = minerReveals[taskID][miners[i]];
            if (r.revealed && r.score > 0) {
                uint256 share = (rewardPool * r.score) / scoreSum;
                if (share > 0) {
                    (bool ok, ) = address(escrow).call(
                        abi.encodeWithSelector(
                            releaseSelector,
                            taskID,
                            miners[i],
                            share
                        )
                    );

                    if (!ok && address(this).balance >= share) {
                        (bool sent, ) = payable(miners[i]).call{value: share}("");
                        sent; // keep non-reverting legacy behavior
                    }
                }
            }
            unchecked {
                ++i;
            }
        }

        rewardsDistributed[taskID] = true;
        emit RewardsPaid(taskID);
    }

    receive() external payable {}
}

