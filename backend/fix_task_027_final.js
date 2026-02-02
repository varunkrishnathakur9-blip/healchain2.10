import { prisma } from "./src/config/database.config.js";
import * as fs from "fs";
import * as path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function main() {
    const taskID = "task_027";
    const dataPath = path.resolve(__dirname, "realistic_task_027_data_v2.json");
    const data = JSON.parse(fs.readFileSync(dataPath, "utf-8"));

    // Use the identity of the running aggregator service
    const currentAggregator = "0xb3025213a82046475954d978f5284c55d5e3e055e";

    console.log(`Step 1: Updating task ${taskID} aggregator identity to ${currentAggregator}...`);
    await prisma.task.update({
        where: { taskID },
        data: {
            aggregatorAddress: currentAggregator,
            status: "OPEN" // Reset to OPEN so it can be triggered
        }
    });

    // Fetch task with miners and gradients first
    const taskRecord = await prisma.task.findUnique({
        where: { taskID },
        include: { miners: true, gradients: true }
    });

    if (!taskRecord) {
        console.error(`Task ${taskID} not found!`);
        return;
    }

    const minersInDB = taskRecord.miners;
    const gradsInDB = taskRecord.gradients;
    function cleanAddr(addr) {
        return String(addr).toLowerCase().replace(/[^a-f0-9x]/g, '');
    }

    console.log(`Found ${minersInDB.length} miners and ${gradsInDB.length} gradients in DB.`);
    console.log("Miners in DB addresses:", minersInDB.map(m => `"${m.address}"`));
    console.log("Cleaned DB addresses:", minersInDB.map(m => cleanAddr(m.address)));

    for (const entry of data) {
        const { minerAddress, publicKey, signature, ciphertext, scoreCommit } = entry;
        const targetAddr = cleanAddr(minerAddress);
        console.log(`Attempting to update miner: "${minerAddress}" (Clean: ${targetAddr})`);

        // Find miner (case-insensitive + clean)
        let miner = null;
        for (const m of minersInDB) {
            const dbAddr = cleanAddr(m.address);
            const match = dbAddr === targetAddr;
            console.log(`  Comparing DB[${dbAddr.length}] "${dbAddr}" with Target[${targetAddr.length}] "${targetAddr}" -> Match: ${match}`);
            if (match) {
                miner = m;
                break;
            }
        }

        if (!miner) {
            console.warn(`⚠️ Miner ${minerAddress} not found in DB list, skipping...`);
            continue;
        }

        console.log(`Updating miner ${miner.address} (ID: ${miner.id})...`);
        await prisma.miner.update({
            where: { id: miner.id },
            data: { publicKey }
        });

        // Update gradient for this miner
        // Note: Gradient also has taskID and minerAddress fields
        const grad = gradsInDB.find(g => g.minerAddress.toLowerCase() === minerAddress.toLowerCase());

        if (grad) {
            console.log(`Updating gradient for ${miner.address} (ID: ${grad.id})...`);
            await prisma.gradient.update({
                where: { id: grad.id },
                data: {
                    signature,
                    ciphertext,
                    scoreCommit,
                    encryptedHash: "0xupdatedhash"
                }
            });
        } else {
            console.warn(`⚠️ No gradient found for ${minerAddress} in DB list`);
        }
    }

    console.log("✅ All task_027 fixes applied successfully!");
}

main().catch(console.error).finally(() => prisma.$disconnect());
