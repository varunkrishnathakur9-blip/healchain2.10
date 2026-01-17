// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title IHealChain
 * @notice Canonical interface defining on-chain interactions
 *         for the HealChain privacy-preserving federated learning framework.
 *
 * @dev This interface reflects the algorithms defined in
 *      Chapter 4 (Proposed System Framework).
 */
interface IHealChain {

    /*//////////////////////////////////////////////////////////////
                                ENUMS
    //////////////////////////////////////////////////////////////*/

    enum TaskStatus {
        CREATED,
        LOCKED,
        PUBLISHED,
        AWAITING_REVEAL,
        COMPLETED,
        FAILED
    }

    /*//////////////////////////////////////////////////////////////
                                STRUCTS
    //////////////////////////////////////////////////////////////*/

    struct Task {
        string taskID;
        address publisher;
        uint256 reward;
        bytes32 accuracyCommit;     // Commit(accuracy || nonceTP)
        uint256 deadline;
        TaskStatus status;
    }

    struct BlockRecord {
        string taskID;
        bytes32 modelHash;          // IPFS / Merkle hash
        uint256 accuracy;
        address aggregator;
        bytes32[] scoreCommits;     // Commit(score_i || nonce_i)
        uint256 timestamp;
    }

    /*//////////////////////////////////////////////////////////////
                            TASK PUBLISHING (M1)
    //////////////////////////////////////////////////////////////*/

    function publishTask(
        string calldata taskID,
        bytes32 accuracyCommit,
        uint256 deadline
    ) external payable;

    function getTask(string calldata taskID)
        external
        view
        returns (Task memory);

    /*//////////////////////////////////////////////////////////////
                        BLOCK PUBLISHING (M6)
    //////////////////////////////////////////////////////////////*/

    function publishBlock(
        string calldata taskID,
        bytes32 modelHash,
        uint256 accuracy,
        bytes32[] calldata scoreCommits
    ) external;

    function getBlock(string calldata taskID)
        external
        view
        returns (BlockRecord memory);

    /*//////////////////////////////////////////////////////////////
                        COMMIT–REVEAL (M7)
    //////////////////////////////////////////////////////////////*/

    function revealAccuracy(
        string calldata taskID,
        uint256 accuracy,
        bytes32 nonce,
        bytes32 commitHash
    ) external;

    function revealScore(
        string calldata taskID,
        uint256 score,
        bytes32 nonce,
        bytes32 scoreCommit
    ) external;

    /*//////////////////////////////////////////////////////////////
                        REWARD DISTRIBUTION (M7)
    //////////////////////////////////////////////////////////////*/

    function distributeRewards(
        string calldata taskID,
        address[] calldata miners
    ) external;

    /*//////////////////////////////////////////////////////////////
                        FAILSAFE / REFUND
    //////////////////////////////////////////////////////////////*/

    function refundPublisher(string calldata taskID) external;

    /*//////////////////////////////////////////////////////////////
                        STAKE MANAGEMENT (M2)
    //////////////////////////////////////////////////////////////*/

    function depositStake() external payable;
    
    function getAvailableStake(address miner) external view returns (uint256);
    
    function isEligible(address miner) external view returns (bool);
    
    function getStakes(address[] calldata miners) 
        external 
        view 
        returns (uint256[] memory stakes, uint256 totalTotalStake);
}

/**
 * @title IStakeRegistry
 * @notice Interface for StakeRegistry contract
 */
interface IStakeRegistry {
    function depositStake() external payable;
    function requestWithdrawal(uint256 amount) external;
    function withdrawStake() external;
    function getAvailableStake(address miner) external view returns (uint256);
    function getStake(address miner) external view returns (
        uint256 availableStake,
        uint256 totalStake,
        uint256 pendingWithdrawal,
        uint256 unlockTime
    );
    function isEligible(address miner) external view returns (bool);
    function getStakes(address[] calldata miners) 
        external 
        view 
        returns (uint256[] memory stakes, uint256 totalTotalStake);
    function MIN_STAKE() external view returns (uint256);
    function slashStake(address miner, uint256 amount, string calldata reason) external;
}
