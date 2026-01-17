// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title StakeRegistry
 * @notice On-chain stake management for HealChain PoS aggregator selection
 * @dev Implements Algorithm 2.1 requirements from BTP Report Section 4.3
 * 
 * This contract manages miner stakes for Proof of Stake aggregator selection.
 * Miners must deposit and lock stakes to participate in aggregator selection.
 * Stakes can be slashed for misbehavior (malicious aggregator actions).
 */
contract StakeRegistry is ReentrancyGuard, Ownable {
    
    // ✔ Required OZ v5 Ownable constructor
    constructor(address initialOwner) Ownable(initialOwner) {
        MIN_STAKE = 1 ether; // Default minimum stake: 1 ETH
        UNLOCK_DELAY = 7 days; // 7 day unlock delay after withdrawal request
    }

    /*//////////////////////////////////////////////////////////////
                                EVENTS
    //////////////////////////////////////////////////////////////*/

    event StakeDeposited(
        address indexed miner,
        uint256 amount,
        uint256 totalStake
    );

    event StakeWithdrawalRequested(
        address indexed miner,
        uint256 amount,
        uint256 unlockTime
    );

    event StakeWithdrawn(
        address indexed miner,
        uint256 amount
    );

    event StakeSlashed(
        address indexed miner,
        uint256 amount,
        string reason
    );

    event MinStakeUpdated(uint256 newMinStake);
    event UnlockDelayUpdated(uint256 newUnlockDelay);

    /*//////////////////////////////////////////////////////////////
                                STRUCTS
    //////////////////////////////////////////////////////////////*/

    struct MinerStake {
        uint256 totalStake;           // Total locked stake
        uint256 pendingWithdrawal;     // Amount pending withdrawal
        uint256 unlockTime;           // When withdrawal becomes available
        uint256 slashedAmount;        // Total amount slashed (for tracking)
        bool exists;                  // Whether miner has ever staked
    }

    /*//////////////////////////////////////////////////////////////
                                STATE
    //////////////////////////////////////////////////////////////*/

    mapping(address => MinerStake) public minerStakes;
    
    // Minimum stake required to participate in aggregator selection
    uint256 public MIN_STAKE;
    
    // Delay before withdrawal can be completed after request
    uint256 public UNLOCK_DELAY;

    // Address authorized to slash stakes (typically aggregator verification service)
    address public slasher;

    /*//////////////////////////////////////////////////////////////
                            MODIFIERS
    //////////////////////////////////////////////////////////////*/

    modifier onlySlasher() {
        require(msg.sender == slasher || msg.sender == owner(), "Not authorized to slash");
        _;
    }

    /*//////////////////////////////////////////////////////////////
                        STAKE MANAGEMENT (M2)
    //////////////////////////////////////////////////////////////*/

    /**
     * @notice Internal function to handle stake deposit logic
     * @dev Used by both depositStake() and receive()
     */
    function _depositStake(address miner, uint256 amount) internal {
        require(amount > 0, "Stake must be > 0");
        
        MinerStake storage stake = minerStakes[miner];
        
        if (!stake.exists) {
            stake.exists = true;
            stake.totalStake = 0;
            stake.pendingWithdrawal = 0;
            stake.unlockTime = 0;
            stake.slashedAmount = 0;
        }
        
        stake.totalStake += amount;
        
        emit StakeDeposited(miner, amount, stake.totalStake);
    }

    /**
     * @notice Deposit stake to participate in PoS aggregator selection
     * @dev Miners must stake at least MIN_STAKE to be eligible
     * @dev Emits StakeDeposited event
     */
    function depositStake() external payable nonReentrant {
        _depositStake(msg.sender, msg.value);
    }

    /**
     * @notice Request withdrawal of stake
     * @dev Initiates unlock period. Stake cannot be withdrawn immediately to prevent gaming
     * @param amount Amount to withdraw (must be <= totalStake - pendingWithdrawal)
     */
    function requestWithdrawal(uint256 amount) external nonReentrant {
        MinerStake storage stake = minerStakes[msg.sender];
        require(stake.exists, "No stake found");
        require(amount > 0, "Amount must be > 0");
        require(amount <= stake.totalStake - stake.pendingWithdrawal, "Insufficient stake");
        
        stake.pendingWithdrawal += amount;
        stake.unlockTime = block.timestamp + UNLOCK_DELAY;
        
        emit StakeWithdrawalRequested(msg.sender, amount, stake.unlockTime);
    }

    /**
     * @notice Complete withdrawal after unlock period
     * @dev Can only be called after unlockTime has passed
     */
    function withdrawStake() external nonReentrant {
        MinerStake storage stake = minerStakes[msg.sender];
        require(stake.exists, "No stake found");
        require(stake.pendingWithdrawal > 0, "No pending withdrawal");
        require(block.timestamp >= stake.unlockTime, "Still locked");
        
        uint256 amount = stake.pendingWithdrawal;
        stake.totalStake -= amount;
        stake.pendingWithdrawal = 0;
        stake.unlockTime = 0;
        
        (bool success, ) = payable(msg.sender).call{value: amount}("");
        require(success, "Withdrawal failed");
        
        emit StakeWithdrawn(msg.sender, amount);
    }

    /**
     * @notice Get current stake for a miner
     * @param miner Address of miner
     * @return availableStake Available stake (totalStake - pendingWithdrawal)
     * @return totalStake Total stake (including pending withdrawal)
     * @return pendingWithdrawal Pending withdrawal amount
     * @return unlockTime Unlock time (0 if no pending withdrawal)
     */
    function getStake(address miner) external view returns (
        uint256 availableStake,
        uint256 totalStake,
        uint256 pendingWithdrawal,
        uint256 unlockTime
    ) {
        MinerStake memory stake = minerStakes[miner];
        return (
            stake.totalStake - stake.pendingWithdrawal,  // Available for PoS
            stake.totalStake,                            // Total locked
            stake.pendingWithdrawal,                     // Pending withdrawal
            stake.unlockTime                             // Unlock timestamp
        );
    }

    /**
     * @notice Get available stake for PoS selection (excludes pending withdrawals)
     * @dev This is the stake amount used for aggregator selection
     * @param miner Address of miner
     * @return Available stake amount (must be >= MIN_STAKE to be eligible)
     */
    function getAvailableStake(address miner) public view returns (uint256) {
        MinerStake memory stake = minerStakes[miner];
        if (!stake.exists) {
            return 0;
        }
        return stake.totalStake - stake.pendingWithdrawal;
    }

    /**
     * @notice Check if miner is eligible for aggregator selection
     * @param miner Address of miner
     * @return True if miner has at least MIN_STAKE available
     */
    function isEligible(address miner) public view returns (bool) {
        return getAvailableStake(miner) >= MIN_STAKE;
    }

    /**
     * @notice Slash stake for misbehavior (e.g., malicious aggregation)
     * @dev Only callable by authorized slasher or owner
     * @param miner Address of miner to slash
     * @param amount Amount to slash (cannot exceed available stake)
     * @param reason Reason for slashing (for event logging)
     */
    function slashStake(
        address miner,
        uint256 amount,
        string calldata reason
    ) external onlySlasher nonReentrant {
        MinerStake storage stake = minerStakes[miner];
        require(stake.exists, "No stake found");
        
        uint256 available = stake.totalStake - stake.pendingWithdrawal;
        require(amount > 0, "Slash amount must be > 0");
        require(amount <= available, "Cannot slash more than available stake");
        
        stake.totalStake -= amount;
        stake.slashedAmount += amount;
        
        // Send slashed funds to owner (can be burned or used for protocol)
        (bool success, ) = payable(owner()).call{value: amount}("");
        require(success, "Slash transfer failed");
        
        emit StakeSlashed(miner, amount, reason);
    }

    /**
     * @notice Get total stake for multiple miners (for PoS selection)
     * @param miners Array of miner addresses
     * @return stakes Array of available stake amounts in same order
     * @return totalTotalStake Sum of all available stakes
     */
    function getStakes(address[] calldata miners) 
        external 
        view 
        returns (uint256[] memory stakes, uint256 totalTotalStake) 
    {
        uint256 length = miners.length;
        stakes = new uint256[](length);
        uint256 total = 0;
        
        for (uint256 i = 0; i < length; ) {
            uint256 stake = getAvailableStake(miners[i]);
            stakes[i] = stake;
            total += stake;
            unchecked { ++i; }
        }
        
        return (stakes, total);
    }

    /*//////////////////////////////////////////////////////////////
                        ADMIN FUNCTIONS
    //////////////////////////////////////////////////////////////*/

    /**
     * @notice Set minimum stake required for aggregator selection
     * @dev Only owner can update
     * @param newMinStake New minimum stake amount
     */
    function setMinStake(uint256 newMinStake) external onlyOwner {
        require(newMinStake > 0, "Min stake must be > 0");
        MIN_STAKE = newMinStake;
        emit MinStakeUpdated(newMinStake);
    }

    /**
     * @notice Set unlock delay for withdrawals
     * @dev Only owner can update
     * @param newUnlockDelay New unlock delay in seconds
     */
    function setUnlockDelay(uint256 newUnlockDelay) external onlyOwner {
        UNLOCK_DELAY = newUnlockDelay;
        emit UnlockDelayUpdated(newUnlockDelay);
    }

    /**
     * @notice Set authorized slasher address
     * @dev Only owner can update
     * @param newSlasher Address authorized to slash stakes
     */
    function setSlasher(address newSlasher) external onlyOwner {
        slasher = newSlasher;
    }

    /**
     * @notice Get contract balance (total locked stakes)
     * @return Total ETH locked in contract
     */
    function getTotalLocked() external view returns (uint256) {
        return address(this).balance;
    }

    /*//////////////////////////////////////////////////////////////
                            RECEIVE
    //////////////////////////////////////////////////////////////*/

    receive() external payable {
        // Allow direct ETH transfers (deposits stake)
        // Use internal function to handle deposit logic
        _depositStake(msg.sender, msg.value);
    }
}
