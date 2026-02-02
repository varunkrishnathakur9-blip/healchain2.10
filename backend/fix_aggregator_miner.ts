import { prisma } from "./src/config/database.config.js";

async function main() {
    const taskID = "task_027";
    const aggregatorAddress = "0xb3025213a82046475954d978f5284c55d5e3e055e";

    // Check if aggregator is already a miner
    const existing = await prisma.miner.findUnique({
        where: {
            taskID_address: {
                taskID,
                address: aggregatorAddress.toLowerCase()
            }
        }
    });

    if (existing) {
        console.log("Aggregator is already a miner.");
        return;
    }

    // Add aggregator as a miner
    await prisma.miner.create({
        data: {
            taskID,
            address: aggregatorAddress.toLowerCase(),
            publicKey: "87770495220837203321695625360794355455785545197250931308422473992229739304825,69603538462132394893786665503151716795520305556265604301311274886557175912909", // From aggregator .env
            proof: "aggregator-self-registration",
            proofVerified: true,
            stake: BigInt("1000000000000000000") // 1 ETH stake for PoS eligibility
        }
    });

    console.log(`Successfully added aggregator ${aggregatorAddress} as a miner for ${taskID}`);
}

main().catch(console.error).finally(() => prisma.$disconnect());
