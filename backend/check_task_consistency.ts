import { prisma } from "./src/config/database.config.js";

async function main() {
    const taskID = "task_027";
    const task = await prisma.task.findUnique({
        where: { taskID },
        include: {
            miners: true
        }
    });

    if (!task) {
        console.log("Task not found");
        return;
    }

    console.log("Aggregator Address in Task:", task.aggregatorAddress);
    console.log("Miners registered for this task:");
    task.miners.forEach(m => {
        console.log(`- ${m.address} (Verified: ${m.proofVerified})`);
    });

    const isAggregatorMiner = task.miners.some(m => m.address.toLowerCase() === task.aggregatorAddress?.toLowerCase());
    console.log("\nIs Aggregator one of the miners?", isAggregatorMiner);
}

main().catch(console.error).finally(() => prisma.$disconnect());
