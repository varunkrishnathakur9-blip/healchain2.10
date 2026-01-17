import { expect } from "chai";
import hre from "hardhat";

const { ethers } = hre;

describe("HealChain — Full End-to-End Flow", function () {
  let escrow: any;
  let reward: any;

  let owner: any;
  let publisher: any;
  let miner1: any;
  let miner2: any;
  let miner3: any;

  const TASK_ID = "TASK-001";
  const TARGET_ACCURACY = 92;
  const REWARD_AMOUNT = ethers.parseEther("1");

  beforeEach(async function () {
    [owner, publisher, miner1, miner2, miner3] =
      await ethers.getSigners();

    // Deploy Escrow
    const Escrow = await ethers.getContractFactory("HealChainEscrow");
    escrow = await Escrow.deploy(owner.address);
    await escrow.waitForDeployment();

    // Deploy RewardDistribution
    const Reward = await ethers.getContractFactory("RewardDistribution");
    reward = await Reward.deploy(await escrow.getAddress());
    await reward.waitForDeployment();
  });

  /* --------------------------------------------------
     ESCROW TEST
  -------------------------------------------------- */
  it("publishes task and locks escrow", async function () {
    await escrow
      .connect(publisher)
      .publishTask(TASK_ID, TARGET_ACCURACY, {
        value: REWARD_AMOUNT,
      });

    const balance = await escrow.escrowBalance(TASK_ID);
    expect(balance).to.equal(REWARD_AMOUNT);
  });

  /* --------------------------------------------------
     COMMIT–REVEAL + DISTRIBUTION
  -------------------------------------------------- */
  it("handles commit–reveal and distributes rewards", async function () {
    await escrow
      .connect(publisher)
      .publishTask(TASK_ID, TARGET_ACCURACY, {
        value: REWARD_AMOUNT,
      });

    const score1 = 95;
    const score2 = 90;
    const score3 = 92;

    const nonce1 = ethers.randomBytes(32);
    const nonce2 = ethers.randomBytes(32);
    const nonce3 = ethers.randomBytes(32);

    const commit1 = ethers.keccak256(
      ethers.solidityPacked(["uint256", "bytes32"], [score1, nonce1])
    );
    const commit2 = ethers.keccak256(
      ethers.solidityPacked(["uint256", "bytes32"], [score2, nonce2])
    );
    const commit3 = ethers.keccak256(
      ethers.solidityPacked(["uint256", "bytes32"], [score3, nonce3])
    );

    // Commit phase
    await reward.connect(miner1).commitResult(TASK_ID, commit1);
    await reward.connect(miner2).commitResult(TASK_ID, commit2);
    await reward.connect(miner3).commitResult(TASK_ID, commit3);

    // Reveal phase
    await reward.connect(miner1).revealResult(TASK_ID, score1, nonce1);
    await reward.connect(miner2).revealResult(TASK_ID, score2, nonce2);
    await reward.connect(miner3).revealResult(TASK_ID, score3, nonce3);

    // Finalize
    await reward.finalizeTask(TASK_ID);

    const totalBalance =
      (await ethers.provider.getBalance(miner1.address)) +
      (await ethers.provider.getBalance(miner2.address)) +
      (await ethers.provider.getBalance(miner3.address));

    expect(totalBalance).to.be.greaterThan(
      ethers.parseEther("3")
    );
  });

  /* --------------------------------------------------
     FULL INTEGRATION FLOW
  -------------------------------------------------- */
  it("executes full HealChain flow end-to-end", async function () {
    await escrow
      .connect(publisher)
      .publishTask(TASK_ID, TARGET_ACCURACY, {
        value: REWARD_AMOUNT,
      });

    const accuracy = 94;
    const nonce = ethers.randomBytes(32);

    const commit = ethers.keccak256(
      ethers.solidityPacked(["uint256", "bytes32"], [accuracy, nonce])
    );

    await reward.connect(miner1).commitResult(TASK_ID, commit);
    await reward.connect(miner1).revealResult(TASK_ID, accuracy, nonce);

    await reward.finalizeTask(TASK_ID);

    const remaining = await escrow.escrowBalance(TASK_ID);
    expect(remaining).to.equal(0);
  });
});
