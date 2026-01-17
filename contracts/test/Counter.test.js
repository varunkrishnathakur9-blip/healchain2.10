const { expect } = require("chai");
const hre = require("hardhat");
const { ethers } = hre;
const { randomBytes, keccak256, solidityPacked, parseEther } = require("ethers");

describe("Counter", function () {
  it("Should emit the Increment event when calling inc()", async function () {
    const Counter = await ethers.getContractFactory("Counter");
    const counter = await Counter.deploy();
    await counter.waitForDeployment();

    await expect(counter.inc())
      .to.emit(counter, "Increment")
      .withArgs(1n);
  });

  it("Sum of Increment events should match current value", async function () {
    const Counter = await ethers.getContractFactory("Counter");
    const counter = await Counter.deploy();
    await counter.waitForDeployment();

    const deploymentBlock = await ethers.provider.getBlockNumber();

    for (let i = 1; i <= 10; i++) {
      await counter.incBy(i);
    }

    const events = await counter.queryFilter(
      counter.filters.Increment(),
      deploymentBlock,
      "latest"
    );

    let total = 0n;
    for (const ev of events) {
      total += ev.args.by;
    }

    expect(await counter.x()).to.equal(total);
  });
});
