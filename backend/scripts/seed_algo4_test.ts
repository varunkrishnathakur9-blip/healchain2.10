import { prisma } from "../src/config/database.config.js";
import { TaskStatus, GradientStatus } from "@prisma/client";

async function seed() {
    const taskID = "test_task_ALGO4";

    console.log(`Seeding realistic test data for ${taskID}...`);

    // Realistic data generated from scripts/gen_realistic_test_data.py
    const testData = [
        {
            "miner_address": "0xMiner1",
            "miner_pk": "0xb6e435ce7d743b5b6ce6c9b1314c8dc34144203c4bb635a6897718128d38c6d0,0x1cc4557193ebebab96a5ae552f0fafcdf2584e1af65256371246cf784d86fedd",
            "score_commit": "0xCommit_1",
            "signature": "5acf33b3221d72243eaefc51025c2c46a4cc7e971e412f32449c0d17a833ea62ddcf1a86179be180fb74eb20fe3ebe6a8e6783f81ca3e34bd2228998cf3596ed",
            "ciphertext": ["12345,67890", "23456,78901"]
        },
        {
            "miner_address": "0xMiner2",
            "miner_pk": "0x06c19f94cc315b19005ae8ed7afa2093013a7a929e80763145a025d4480ca0b3,0x51034a11e49dc6c23a1fc7f2a471fb0bffc36b899f64eff9b86d5f6391956803",
            "score_commit": "0xCommit_2",
            "signature": "e27f19c414cf8b99a16bf604e6512833a566e4cdb404d37f5fb54e642cc2cbb4c7706aa3ff61792818fad8d4c1ef6b4f9e456cfb5dc3716245547e249b8673e2",
            "ciphertext": ["12345,67890", "23456,78901"]
        },
        {
            "miner_address": "0xMiner3",
            "miner_pk": "0x12acc5f11755e2f83f702e78b3ce903983e2b29483394d950c8038dc8479d3bf,0x780d3152e0dad757b87bcc22d13fa9de988807c4ffe283c6b0cab4afa4ea9928",
            "score_commit": "0xCommit_3",
            "signature": "b3824ed8e0ecb11c1fff134bb1cf33dca8cef147093fb7773ecbc7f02301a467c852ea4dabea3989fb328519c208f0ddb3e2d3ba3208cdc3c29f8e76f97a12f8",
            "ciphertext": ["12345,67890", "23456,78901"]
        }
    ];

    // 1. Create Task
    await prisma.task.upsert({
        where: { taskID },
        update: {
            status: TaskStatus.OPEN,
            aggregatorAddress: "0xAggregator".toLowerCase()
        },
        create: {
            taskID,
            publisher: "0xPublisherAddress".toLowerCase(),
            commitHash: "0xCommitHash",
            nonceTP: "test_nonce",
            deadline: BigInt(Math.floor(Date.now() / 1000) + 3600),
            status: TaskStatus.OPEN,
            aggregatorAddress: "0xAggregator".toLowerCase(),
            dataset: "chestxray"
        }
    });

    // 2. Create Miners & Gradients
    for (const item of testData) {
        const addr = item.miner_address.toLowerCase();

        await prisma.miner.upsert({
            where: { taskID_address: { taskID, address: addr } },
            update: {
                proofVerified: true,
                publicKey: item.miner_pk
            },
            create: {
                taskID,
                address: addr,
                publicKey: item.miner_pk,
                proof: "ipfs://test_proof",
                proofVerified: true,
            }
        });

        // Submissions
        const existing = await prisma.gradient.findFirst({
            where: { taskID, minerAddress: addr }
        });

        const gradData = {
            taskID,
            minerAddress: addr,
            scoreCommit: item.score_commit,
            encryptedHash: "test_hash",
            ciphertext: JSON.stringify(item.ciphertext),
            signature: item.signature,
            status: GradientStatus.COMMITTED
        };

        if (!existing) {
            await prisma.gradient.create({ data: gradData });
        } else {
            await prisma.gradient.update({
                where: { id: existing.id },
                data: gradData
            });
        }
    }

    console.log("Realistic seeding complete!");
}

seed()
    .catch((e) => {
        console.error(e);
        process.exit(1);
    })
    .finally(async () => {
        await prisma.$disconnect();
    });
