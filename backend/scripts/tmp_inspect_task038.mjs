import { prisma } from "../dist/config/database.config.js";

async function main() {
  const taskID = "task_038";

  const task = await prisma.task.findUnique({
    where: { taskID },
    include: {
      block: true,
      miners: {
        select: {
          address: true,
          publicKey: true,
          proofVerified: true,
        },
      },
      gradients: {
        select: {
          minerAddress: true,
          scoreCommit: true,
          createdAt: true,
        },
      },
      verifications: {
        select: {
          minerAddress: true,
          candidateHash: true,
          verdict: true,
          reason: true,
          message: true,
          signature: true,
          createdAt: true,
        },
      },
    },
  });

  if (!task) {
    console.log("Task not found");
    return;
  }

  console.log(
    JSON.stringify(
      {
        task: {
          taskID: task.taskID,
          status: task.status,
          currentRound: task.currentRound,
          initialModelLink: task.initialModelLink,
          aggregatorAddress: task.aggregatorAddress,
          targetAccuracy: task.targetAccuracy,
          blockExists: !!task.block,
        },
        block: task.block,
        counts: {
          miners: task.miners.length,
          gradients: task.gradients.length,
          verifications: task.verifications.length,
        },
        uniqueVerificationCandidateHashes: Array.from(
          new Set(task.verifications.map((v) => v.candidateHash).filter(Boolean))
        ),
        sampleVerification: task.verifications[0] ?? null,
      },
      null,
      2
    )
  );
}

main()
  .catch((e) => {
    console.error(e);
    process.exitCode = 1;
  })
  .finally(async () => {
    await prisma.$disconnect();
  });

