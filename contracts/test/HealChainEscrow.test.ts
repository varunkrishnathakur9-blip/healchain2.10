import { expect } from "chai";
import hre from "hardhat";

// 👇 this is the correct and accepted fix
const ethers = (hre as any).ethers;
import { randomBytes, keccak256, solidityPacked, parseEther } from "ethers";

describe("HealChainEscrow", function () {
  let escrow: any;
  let owner: any;
  let publisher: any;
  let miner1: any;
  let miner2: any;

  const taskID = "TASK-001";
  const accuracy = 92;
  const rewardETH = parseEther("1");

  beforeEach(async function () {
    [owner, publisher, miner1, miner2] = await ethers.getSigners();

    const Escrow = await ethers.getContractFactory("HealChainEscrow");
    escrow = await Escrow.deploy(owner.address);
    await escrow.waitForDeployment();
  });

  describe("Deployment", function () {
    it("Should set the right owner", async function () {
      expect(await escrow.owner()).to.equal(owner.address);
    });

    it("Should initialize with no tasks", async function () {
      expect(await escrow.taskCount()).to.equal(0);
    });
  });

  describe("Task Publishing", function () {
    it("Should publish a task with valid parameters", async function () {
      const nonce = randomBytes(32);
      const commit = keccak256(
        solidityPacked(["uint256", "bytes32"], [accuracy, nonce])
      );
      const deadline = Math.floor(Date.now() / 1000) + 3600;

      await expect(
        escrow.connect(publisher).publishTask(taskID, commit, deadline, {
          value: rewardETH,
        })
      )
        .to.emit(escrow, "TaskPublished")
        .withArgs(taskID, publisher.address, rewardETH, commit, deadline);

      const task = await escrow.tasks(taskID);
      expect(task.publisher).to.equal(publisher.address);
      expect(task.reward).to.equal(rewardETH);
      expect(task.commitHash).to.equal(commit);
      expect(task.deadline).to.equal(deadline);
      expect(task.status).to.equal(0); // CREATED
    });

    it("Should reject task with zero reward", async function () {
      const nonce = randomBytes(32);
      const commit = keccak256(
        solidityPacked(["uint256", "bytes32"], [accuracy, nonce])
      );
      const deadline = Math.floor(Date.now() / 1000) + 3600;

      await expect(
        escrow.connect(publisher).publishTask(taskID, commit, deadline, {
          value: 0,
        })
      ).to.be.revertedWith("Reward must be greater than 0");
    });

    it("Should reject task with past deadline", async function () {
      const nonce = randomBytes(32);
      const commit = keccak256(
        solidityPacked(["uint256", "bytes32"], [accuracy, nonce])
      );
      const pastDeadline = Math.floor(Date.now() / 1000) - 3600;

      await expect(
        escrow.connect(publisher).publishTask(taskID, commit, pastDeadline, {
          value: rewardETH,
        })
      ).to.be.revertedWith("Deadline must be in the future");
    });

    it("Should reject duplicate task ID", async function () {
      const nonce = randomBytes(32);
      const commit = keccak256(
        solidityPacked(["uint256", "bytes32"], [accuracy, nonce])
      );
      const deadline = Math.floor(Date.now() / 1000) + 3600;

      // First publish
      await escrow.connect(publisher).publishTask(taskID, commit, deadline, {
        value: rewardETH,
      });

      // Second publish should fail
      await expect(
        escrow.connect(publisher).publishTask(taskID, commit, deadline, {
          value: rewardETH,
        })
      ).to.be.revertedWith("Task already exists");
    });
  });

  describe("Task Management", function () {
    beforeEach(async function () {
      const nonce = randomBytes(32);
      const commit = keccak256(
        solidityPacked(["uint256", "bytes32"], [accuracy, nonce])
      );
      const deadline = Math.floor(Date.now() / 1000) + 3600;

      await escrow.connect(publisher).publishTask(taskID, commit, deadline, {
        value: rewardETH,
      });
    });

    it("Should lock task by owner", async function () {
      await expect(escrow.connect(owner).lockTask(taskID))
        .to.emit(escrow, "TaskLocked")
        .withArgs(taskID);

      const task = await escrow.tasks(taskID);
      expect(task.status).to.equal(1); // LOCKED
    });

    it("Should reject task lock by non-owner", async function () {
      await expect(
        escrow.connect(publisher).lockTask(taskID)
      ).to.be.revertedWith("Only owner can lock task");
    });

    it("Should publish locked task", async function () {
      // Lock first
      await escrow.connect(owner).lockTask(taskID);

      const nonce = randomBytes(32);
      const accuracyCommit = keccak256(
        solidityPacked(["uint256", "bytes32"], [accuracy, nonce])
      );

      await expect(escrow.connect(owner).publishAccuracy(taskID, accuracyCommit))
        .to.emit(escrow, "AccuracyPublished")
        .withArgs(taskID, accuracyCommit);

      const task = await escrow.tasks(taskID);
      expect(task.status).to.equal(2); // PUBLISHED
    });

    it("Should reject publish accuracy for non-locked task", async function () {
      const nonce = randomBytes(32);
      const accuracyCommit = keccak256(
        solidityPacked(["uint256", "bytes32"], [accuracy, nonce])
      );

      await expect(
        escrow.connect(owner).publishAccuracy(taskID, accuracyCommit)
      ).to.be.revertedWith("Task must be locked");
    });
  });
});