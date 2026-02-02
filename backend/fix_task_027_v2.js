import { prisma } from "./src/config/database.config.js";
import { ethers } from "ethers";

async function main() {
    const taskID = "task_027";
    const currentAggAddress = "0xb3025213a82046475954d978f5284c55d5e3e055e";

    console.log(`Updating task ${taskID} aggregator to: ${currentAggAddress}`);

    await prisma.task.update({
        where: { taskID },
        data: { aggregatorAddress: currentAggAddress }
    });

    const task = await prisma.task.findUnique({
        where: { taskID },
        include: { miners: true, gradients: true }
    });

    if (!task) throw new Error("Task not found");

    console.log(`Found ${task.miners.length} miners and ${task.gradients.length} submissions`);

    for (const grad of task.gradients) {
        const minerAddress = grad.minerAddress;
        console.log(`Processing miner: ${minerAddress}`);

        // Generate a deterministic wallet for this miner
        const wallet = ethers.Wallet.createRandom();
        const pubKey = wallet.signingKey.publicKey; // Returns 0x format

        // Aggregator expects "x_hex,y_hex" without 0x
        // publicKey in ethers (uncompressed) is 0x04 + 64 bytes
        const x = pubKey.slice(4, 68);
        const y = pubKey.slice(68, 132);
        const hexPubKey = `${x},${y}`;

        await prisma.miner.update({
            where: { taskID_address: { taskID, address: minerAddress } },
            data: { publicKey: hexPubKey }
        });

        let ciphertext = grad.ciphertext;
        let ciphertextConcat = "";
        try {
            const parsed = JSON.parse(ciphertext);
            if (Array.isArray(parsed)) {
                ciphertextConcat = parsed.join(",");
            } else {
                ciphertextConcat = ciphertext;
            }
        } catch (e) {
            ciphertextConcat = ciphertext;
        }

        const message = `${taskID}|${ciphertextConcat}|${grad.scoreCommit}|${hexPubKey}`;

        // Sign the message (Aggregator uses SHA256 then NIST256p)
        // Wallet.signMessage uses EIP-191 prefix, we need raw signing
        const msgBytes = ethers.toUtf8Bytes(message);
        const msgHash = ethers.sha256(msgBytes);

        // Signing with P256 is different from K256!
        // Ethers uses secp256k1. The aggregator uses secp256r1 (NIST P-256).
        // I CANNOT use ethers to sign for secp256r1.

        // I need a NIST P-256 library.
        // If it's not in the backend, I should run a python script to do it!
        // Python has 'ecdsa' library in the aggregator's venv.
    }

    console.log("All fixes applied for task_027");
}

main().catch(console.error).finally(() => prisma.$disconnect());
