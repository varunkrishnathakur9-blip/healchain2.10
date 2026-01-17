import { expect } from "chai";
import hre from "hardhat";

// Hardhat v2 + ethers v6 safe access
const ethers = (hre as any).ethers;

import { randomBytes, keccak256, solidityPacked, parseEther } from "ethers";

describe("HealChain Integration", function () {
  let escrow: any;
  let reward: any;
  let owner: any;
  let publisher: any;
  let miners: any[];

  const taskID = "TASK-INTEGRATION-001";
  const accuracy = 95;
  const rewardETH = parseEther("2");
  const tolerance = parseEther("0.01");

  beforeEach(async function () {
    const signers = await ethers.getSigners();
    [owner, publisher, ...miners] = signers;

    const Escrow = await ethers.getContractFactory("HealChainEscrow");
    escrow = await Escrow.deploy(owner.address);
    await escrow.waitForDeployment();

    const Reward = await ethers.getContractFactory("RewardDistribution");
    reward = await Reward.deploy(await escrow.getAddress());
    await reward.waitForDeployment();
  });

  it("Should complete full commit–reveal workflow", async function () {
    // 1. Publisher creates task
    const nonceTP = randomBytes(32);
    const commitTP = keccak256(
      solidityPacked(["uint256", "bytes32"], [accuracy, nonceTP])
    );
    const deadline = Math.floor(Date.now() / 1000) + 3600;

    await expect(
      escrow.connect(publisher).publishTask(taskID, commitTP, deadline, {
        value: rewardETH,
      })
    )
      .to.emit(escrow, "TaskPublished")
      .withArgs(taskID, publisher.address, rewardETH, commitTP, deadline);

    // 2. Lock task
    await escrow.connect(owner).lockTask(taskID);

    // 3. Publish accuracy commit
    await escrow.connect(owner).publishAccuracy(taskID, commitTP);

    // 4. Reveal accuracy
    await expect(
      reward.connect(owner).revealAccuracy(taskID, accuracy, nonceTP, commitTP)
    )
      .to.emit(reward, "AccuracyRevealed")
      .withArgs(taskID, accuracy);

    // 5. Miners reveal scores
    const scores = [90, 85, 92, 88, 87];

    for (let i = 0; i < 5; i++) {
      const nonce = randomBytes(32);
      const commit = keccak256(
        solidityPacked(
          ["uint256", "bytes32", "string", "address"],
          [scores[i], nonce, taskID, miners[i].address]
        )
      );

      await expect(
        reward.connect(miners[i]).revealScore(taskID, scores[i], nonce, commit)
      )
        .to.emit(reward, "ScoreRevealed")
        .withArgs(taskID, miners[i].address, scores[i]);
    }

    // 6. Distribute rewards
    const topMiners = [miners[2], miners[0], miners[1]]; // 92, 90, 85
    const initialBalances = await Promise.all(
      topMiners.map(m => ethers.provider.getBalance(m.address))
    );

    await expect(
      reward.connect(owner).distribute(taskID, topMiners.map(m => m.address))
    )
      .to.emit(reward, "RewardsPaid")
      .withArgs(taskID, topMiners.map(m => m.address));

    // 7. Verify rewards (BigInt-safe)
    const finalBalances = await Promise.all(
      topMiners.map(m => ethers.provider.getBalance(m.address))
    );

    const rewards = finalBalances.map(
      (b, i) => b - initialBalances[i]
    );

    const expected = [
      rewardETH * 70n / 100n,
      rewardETH * 20n / 100n,
      rewardETH * 10n / 100n,
    ];

    for (let i = 0; i < rewards.length; i++) {
      expect(rewards[i] >= expected[i] - tolerance).to.equal(true);
      expect(rewards[i] <= expected[i] + tolerance).to.equal(true);
    }
  });

  it("Should handle single-miner edge case", async function () {
    const singleTaskID = "TASK-SINGLE-001";
    const nonceTP = randomBytes(32);
    const commitTP = keccak256(
      solidityPacked(["uint256", "bytes32"], [accuracy, nonceTP])
    );
    const deadline = Math.floor(Date.now() / 1000) + 3600;

    await escrow.connect(publisher).publishTask(singleTaskID, commitTP, deadline, {
      value: rewardETH,
    });

    await escrow.connect(owner).lockTask(singleTaskID);
    await escrow.connect(owner).publishAccuracy(singleTaskID, commitTP);
    await reward.connect(owner).revealAccuracy(singleTaskID, accuracy, nonceTP, commitTP);

    const score = 95;
    const nonce = randomBytes(32);
    const commit = keccak256(
      solidityPacked(
        ["uint256", "bytes32", "string", "address"],
        [score, nonce, singleTaskID, miners[0].address]
      )
    );

    await reward.connect(miners[0]).revealScore(singleTaskID, score, nonce, commit);

    const before = await ethers.provider.getBalance(miners[0].address);
    await reward.connect(owner).distribute(singleTaskID, [miners[0].address]);
    const after = await ethers.provider.getBalance(miners[0].address);

    const received = after - before;

    expect(received >= rewardETH - tolerance).to.equal(true);
    expect(received <= rewardETH + tolerance).to.equal(true);
  });
});
