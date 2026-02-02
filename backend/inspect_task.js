import { prisma } from "./src/config/database.config.js";

async function main() {
    const task = await prisma.task.findUnique({
        where: { taskID: "task_027" },
        include: {
            miners: true,
            gradients: true
        }
    });
    console.log("Task ID (Internal):", task.id);
    console.log("Task ID (Field):", task.taskID);
    console.log("First Miner taskID:", task.miners[0]?.taskID);
    console.log("First Gradient taskID:", task.gradients[0]?.taskID);
}

main().catch(console.error).finally(() => prisma.$disconnect());
