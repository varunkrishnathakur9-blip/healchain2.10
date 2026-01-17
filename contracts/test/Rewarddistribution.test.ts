import { expect } from "chai";
import hre from "hardhat";

// 👇 this is the correct and accepted fix
const ethers = (hre as any).ethers;
import { randomBytes, keccak256, solidityPacked, parseEther } from "ethers";

describe("RewardDistribution", function () {
  let escrow: any;
  let reward: any;
  let owner: any;
  let publisher: any;
  let miner1: any;
  let miner2: any;
  let miner3: any;

  const taskID = "TASK-001";
  const accuracy = 92;
  const rewardETH = parseEther("1");

  beforeEach(async function () {
    [owner, publisher, miner1, miner2, miner3] = await ethers.getSigners();

    // Deploy Escrow
    const Escrow = await ethers.getContractFactory("HealChainEscrow");
    escrow = await Escrow.deploy(owner.address);
    await escrow.waitForDeployment();

    // Deploy RewardDistribution
    const Reward = await ethers.getContractFactory("RewardDistribution");
    reward = await Reward.deploy(await escrow.getAddress());
    await reward.waitForDeployment();

    // Publish and lock task
    const nonce = randomBytes(32);
    const commit = keccak256(
      solidityPacked(["uint256", "bytes32"], [accuracy, nonce])
    );
    const deadline = Math.floor(Date.now() / 1000) + 3600;

    await escrow.connect(publisher).publishTask(taskID, commit, deadline, {
      value: rewardETH,
    });
    await escrow.connect(owner).lockTask(taskID);
  });

  describe("Deployment", function () {
    it("Should set the escrow address", async function () {
      expect(await reward.escrow()).to.equal(await escrow.getAddress());
    });
  });

  describe("Accuracy Reveal", function () {
    it("Should allow valid accuracy reveal", async function () {
      const nonce = randomBytes(32);
      const commit = keccak256(
        solidityPacked(["uint256", "bytes32"], [accuracy, nonce])
      );

      await expect(
        reward.connect(owner).revealAccuracy(taskID, accuracy, nonce, commit)
      )
        .to.emit(reward, "AccuracyRevealed")
        .withArgs(taskID, accuracy);

      const revealData = await reward.accuracyReveals(taskID);
      expect(revealData.accuracy).to.equal(accuracy);
      expect(revealData.nonce).to.equal(keccak256(nonce));
      expect(revealData.revealed).to.be.true;
    });

    it("Should reject invalid accuracy reveal", async function () {
      const nonce = randomBytes(32);
      const commit = keccak256(
        solidityPacked(["uint256", "bytes32"], [accuracy, nonce])
      );

      await expect(
        reward.connect(owner).revealAccuracy(taskID, accuracy + 1, nonce, commit)
      ).to.be.revertedWith("Invalid accuracy reveal");
    });

    it("Should reject duplicate accuracy reveal", async function () {
      const nonce = randomBytes(32);
      const commit = keccak256(
        solidityPacked(["uint256", "bytes32"], [accuracy, nonce])
      );

      // First reveal
      await reward.connect(owner).revealAccuracy(taskID, accuracy, nonce, commit);

      // Second reveal should fail
      await expect(
        reward.connect(owner).revealAccuracy(taskID, accuracy, nonce, commit)
      ).to.be.revertedWith("Accuracy already revealed");
    });
  });

  describe("Score Reveal", function () {
    beforeEach(async function () {
      const nonce = randomBytes(32);
      const commit = keccak256(
        solidityPacked(["uint256", "bytes32"], [accuracy, nonce])
      );

      await reward.connect(owner).revealAccuracy(taskID, accuracy, nonce, commit);
    });

    it("Should allow valid score reveal", async function () {
      const score = 85;
      const nonce = randomBytes(32);
      const commit = keccak256(
        solidityPacked(
          ["uint256", "bytes32", "string", "address"],
          [score, nonce, taskID, miner1.address]
        )
      );

      await expect(
        reward.connect(miner1).revealScore(taskID, score, nonce, commit)
      )
        .to.emit(reward, "ScoreRevealed")
        .withArgs(taskID, miner1.address, score);

      const scoreData = await reward.scoreReveals(taskID, miner1.address);
      expect(scoreData.score).to.equal(score);
      expect(scoreData.nonce).to.equal(keccak256(nonce));
      expect(scoreData.revealed).to.be.true;
    });

    it("Should reject invalid score reveal", async function () {
      const score = 85;
      const nonce = randomBytes(32);
      const commit = keccak256(
        solidityPacked(
          ["uint256", "bytes32", "string", "address"],
          [score, nonce, taskID, miner1.address]
        )
      );

      await expect(
        reward.connect(miner1).revealScore(taskID, score + 1, nonce, commit)
      ).to.be.revertedWith("Invalid score reveal");
    });

    it("Should reject score reveal before accuracy reveal", async function () {
      const newTaskID = "TASK-002";
      const nonce = randomBytes(32);
      const commit = keccak256(
        solidityPacked(["uint256", "bytes32"], [accuracy, nonce])
      );
      const deadline = Math.floor(Date.now() / 1000) + 3600;

      // Create new task without accuracy reveal
      await escrow.connect(publisher).publishTask(newTaskID, commit, deadline, {
        value: rewardETH,
      });
      await escrow.connect(owner).lockTask(newTaskID);

      const score = 85;
      const scoreNonce = randomBytes(32);
      const scoreCommit = keccak256(
        solidityPacked(
          ["uint256", "bytes32", "string", "address"],
          [score, scoreNonce, newTaskID, miner1.address]
        )
      );

      await expect(
        reward.connect(miner1).revealScore(newTaskID, score, scoreNonce, scoreCommit)
      ).to.be.revertedWith("Accuracy must be revealed first");
    });
  });

  describe("Reward Distribution", function () {
    beforeEach(async function () {
      const nonce = randomBytes(32);
      const commit = keccak256(
        solidityPacked(["uint256", "bytes32"], [accuracy, nonce])
      );

      await reward.connect(owner).revealAccuracy(taskID, accuracy, nonce, commit);

      // Miner 1 score
      const score1 = 90;
      const nonce1 = randomBytes(32);
      const commit1 = keccak256(
        solidityPacked(
          ["uint256", "bytes32", "string", "address"],
          [score1, nonce1, taskID, miner1.address]
        )
      );
      await reward.connect(miner1).revealScore(taskID, score1, nonce1, commit1);

      // Miner 2 score
      const score2 = 80;
      const nonce2 = randomBytes(32);
      const commit2 = keccak256(
        solidityPacked(
          ["uint256", "bytes32", "string", "address"],
          [score2, nonce2, taskID, miner2.address]
        )
      );
      await reward.connect(miner2).revealScore(taskID, score2, nonce2, commit2);

      // Miner 3 score (lower)
      const score3 = 70;
      const nonce3 = randomBytes(32);
      const commit3 = keccak256(
        solidityPacked(
          ["uint256", "bytes32", "string", "address"],
          [score3, nonce3, taskID, miner3.address]
        )
      );
      await reward.connect(miner3).revealScore(taskID, score3, nonce3, commit3);
    });

    it("Should distribute rewards to top performers", async function () {
      const initialBalance1 = await ethers.provider.getBalance(miner1.address);
      const initialBalance2 = await ethers.provider.getBalance(miner2.address);

      await expect(
        reward.connect(owner).distribute(taskID, [
          miner1.address,
          miner2.address,
        ])
      )
        .to.emit(reward, "RewardsPaid")
        .withArgs(taskID, [miner1.address, miner2.address]);

      // Check rewards (90% to top performer, 10% to second)
      const finalBalance1 = await ethers.provider.getBalance(miner1.address);
      const finalBalance2 = await ethers.provider.getBalance(miner2.address);

      const reward1 = finalBalance1 - initialBalance1;
      const reward2 = finalBalance2 - initialBalance2;

    
    const tolerance = parseEther("0.01");

const expected1 = rewardETH * 90n / 100n;
const expected2 = rewardETH * 10n / 100n;

expect(reward1 >= expected1 - tolerance).to.equal(true);
expect(reward1 <= expected1 + tolerance).to.equal(true);

expect(reward2 >= expected2 - tolerance).to.equal(true);
expect(reward2 <= expected2 + tolerance).to.equal(true);
});

    it("Should reject distribution by non-owner", async function () {
      await expect(
        reward.connect(publisher).distribute(taskID, [
          miner1.address,
          miner2.address,
        ])
      ).to.be.revertedWith("Only owner can distribute rewards");
    });

    it("Should reject distribution without accuracy reveal", async function () {
      const newTaskID = "TASK-003";
      const nonce = randomBytes(32);
      const commit = keccak256(
        solidityPacked(["uint256", "bytes32"], [accuracy, nonce])
      );
      const deadline = Math.floor(Date.now() / 1000) + 3600;

      await escrow.connect(publisher).publishTask(newTaskID, commit, deadline, {
        value: rewardETH,
      });
      await escrow.connect(owner).lockTask(newTaskID);

      await expect(
        reward.connect(owner).distribute(newTaskID, [miner1.address])
      ).to.be.revertedWith("Accuracy must be revealed first");
    });
  });
});