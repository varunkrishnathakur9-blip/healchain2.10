import { prisma } from "../dist/config/database.config.js";
const task = await prisma.task.findUnique({ where: { taskID: "task_038" }, select: { taskID: true, status: true, publishTx: true, updatedAt: true } });
console.log(JSON.stringify(task, (_k,v)=> typeof v === 'bigint' ? v.toString() : v, 2));
await prisma.$disconnect();
