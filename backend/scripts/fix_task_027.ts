import { prisma } from "../src/config/database.config.js";
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function fix() {
    const dataPath = path.resolve(__dirname, "../../aggregator/realistic_task_027_data.json");
    const data = JSON.parse(fs.readFileSync(dataPath, 'utf8'));
    const taskID = "task_027";

    console.log(`Fixing data for ${taskID}...`);

    for (const item of data) {
        const minerAddress = item.miner_address.toLowerCase();
        console.log(`Updating ${minerAddress}...`);

        await prisma.miner.update({
            where: { taskID_address: { taskID, address: minerAddress } },
            data: { publicKey: item.miner_pk }
        });

        const grad = await prisma.gradient.findFirst({
            where: { taskID, minerAddress }
        });

        if (grad) {
            await prisma.gradient.update({
                where: { id: grad.id },
                data: {
                    signature: item.signature,
                    ciphertext: JSON.stringify(item.ciphertext),
                    scoreCommit: item.score_commit
                }
            });
        }
    }
    console.log("Done!");
}

fix().catch(console.error).finally(() => prisma.$disconnect());
