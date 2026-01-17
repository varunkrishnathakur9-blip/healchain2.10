// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract HealChainEscrow is ReentrancyGuard, Ownable {

    // ✔ Required OZ v5 Ownable constructor
    constructor(address initialOwner) Ownable(initialOwner) {}

    enum TaskStatus {
        CREATED,
        LOCKED,
        PUBLISHED,
        AWAITING_REVEAL,
        COMPLETED,
        FAILED
    }

    struct Task {
        string taskID;
        address publisher;
        uint256 reward;
        bytes32 accuracyCommit;
        uint256 deadline;
        TaskStatus status;
    }

    mapping(string => Task) public tasks;
    mapping(string => uint256) public escrowBalance;

    event TaskCreated(
        string indexed taskID,
        address indexed publisher,
        uint256 reward
    );

    event TaskLocked(string indexed taskID);
    event TaskFailed(string indexed taskID);

    // M1: Publish FL task with escrow
    function publishTask(
        string calldata taskID,
        bytes32 accuracyCommit,
        uint256 deadline
    ) external payable nonReentrant {

        require(msg.value > 0, "Reward must be > 0");
        require(tasks[taskID].publisher == address(0), "Task exists");
        require(deadline > block.timestamp, "Invalid deadline");

        tasks[taskID] = Task({
            taskID: taskID,
            publisher: msg.sender,
            reward: msg.value,
            accuracyCommit: accuracyCommit,
            deadline: deadline,
            status: TaskStatus.LOCKED
        });

        escrowBalance[taskID] = msg.value;

        emit TaskCreated(taskID, msg.sender, msg.value);
        emit TaskLocked(taskID);
    }

    // Safety: refund if task never completes
    function refundPublisher(string calldata taskID) external nonReentrant {
        Task storage task = tasks[taskID];

        require(msg.sender == task.publisher, "Only publisher");
        require(block.timestamp > task.deadline, "Too early");
        require(task.status != TaskStatus.COMPLETED, "Already completed");

        uint256 amount = escrowBalance[taskID];
        escrowBalance[taskID] = 0;
        task.status = TaskStatus.FAILED;

        (bool ok, ) = payable(msg.sender).call{value: amount}("");
        require(ok, "Refund failed");

        emit TaskFailed(taskID);
    }
}
