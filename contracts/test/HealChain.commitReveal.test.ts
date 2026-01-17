import { expect } from "chai";
import hre from "hardhat";
const { ethers } = hre as any;
import { randomBytes, keccak256, solidityPacked, parseEther } from "ethers";

describe("HealChain Commit–Reveal Flow", function () {
  let escrow: any;
  let reward: any;
  let owner: any;
  let publisher: any;
  let miner1: any;
  let miner2: any;

  const taskID = "TASK-001";
  const accuracy = 92;
  const rewardETH = parseEther("1");

  beforeEach(async () => {
    [owner, publisher, miner1, miner2] = await ethers.getSigners();

    const Escrow = await ethers.getContractFactory("HealChainEscrow");
    escrow = await Escrow.deploy(owner.address);
    await escrow.waitForDeployment();

    const Reward = await ethers.getContractFactory("RewardDistribution");
    reward = await Reward.deploy(await escrow.getAddress());
    await reward.waitForDeployment();
  });

  it("should publish task with escrow", async () => {
    const nonce = randomBytes(32);
    const commit = keccak256(
      solidityPacked(["uint256", "bytes32"], [accuracy, nonce])
    );

    await escrow.connect(publisher).publishTask(
      taskID,
      commit,
      Math.floor(Date.now() / 1000) + 3600,
      { value: rewardETH }
    );

    const task = await escrow.tasks(taskID);
    expect(task.publisher).to.equal(publisher.address);
    expect(task.reward).to.equal(rewardETH);
  });

  it("should allow valid accuracy reveal", async () => {
    const nonce = randomBytes(32);
    const commit = keccak256(
      solidityPacked(["uint256", "bytes32"], [accuracy, nonce])
    );

    await escrow.connect(publisher).publishTask(
      taskID,
      commit,
      Math.floor(Date.now() / 1000) + 3600,
      { value: rewardETH }
    );

    await reward.connect(publisher).revealAccuracy(
      taskID,
      accuracy,
      nonce,
      commit
    );

    const revealed = await reward.revealedAccuracy(taskID);
    expect(revealed).to.equal(accuracy);
  });

  it("should reject incorrect accuracy reveal", async () => {
    const nonce = randomBytes(32);
    const commit = keccak256(
      solidityPacked(["uint256", "bytes32"], [accuracy, nonce])
    );

    await escrow.connect(publisher).publishTask(
      taskID,
      commit,
      Math.floor(Date.now() / 1000) + 3600,
      { value: rewardETH }
    );

    await expect(
      reward.connect(publisher).revealAccuracy(
        taskID,
        accuracy + 1,
        nonce,
        commit
      )
    ).to.be.reverted;
  });

  it("should allow miners to reveal scores and distribute rewards", async () => {
    const nonceTP = randomBytes(32);
    const commitTP = keccak256(
      solidityPacked(["uint256", "bytes32"], [accuracy, nonceTP])
    );

    await escrow.connect(publisher).publishTask(
      taskID,
      commitTP,
      Math.floor(Date.now() / 1000) + 3600,
      { value: rewardETH }
    );

    await reward.connect(publisher).revealAccuracy(
      taskID,
      accuracy,
      nonceTP,
      commitTP
    );

    const score1 = 60;
    const nonce1 = randomBytes(32);
    const commit1 = keccak256(
      solidityPacked(
        ["uint256", "bytes32", "string", "address"],
        [score1, nonce1, taskID, miner1.address]
      )
    );

    const score2 = 40;
    const nonce2 = randomBytes(32);
    const commit2 = keccak256(
      solidityPacked(
        ["uint256", "bytes32", "string", "address"],
        [score2, nonce2, taskID, miner2.address]
      )
    );

    await reward.connect(miner1).revealScore(taskID, score1, nonce1, commit1);
    await reward.connect(miner2).revealScore(taskID, score2, nonce2, commit2);

    // 🔥 FUND reward contract BEFORE distribute
    await owner.sendTransaction({
      to: await reward.getAddress(),
      value: rewardETH,
    });

    await reward.distribute(taskID, [
      miner1.address,
      miner2.address,
    ]);
  });
});
