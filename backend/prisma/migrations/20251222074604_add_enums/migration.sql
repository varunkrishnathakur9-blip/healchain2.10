-- CreateEnum
CREATE TYPE "TaskStatus" AS ENUM ('CREATED', 'OPEN', 'COMMIT_CLOSED', 'REVEAL_OPEN', 'REVEAL_CLOSED', 'AGGREGATING', 'VERIFIED', 'REWARDED', 'CANCELLED');

-- CreateEnum
CREATE TYPE "GradientStatus" AS ENUM ('COMMITTED', 'REVEALED', 'VERIFIED', 'REJECTED');

-- CreateEnum
CREATE TYPE "BlockStatus" AS ENUM ('PENDING', 'FINALIZED');

-- CreateTable
CREATE TABLE "Task" (
    "id" TEXT NOT NULL,
    "taskID" TEXT NOT NULL,
    "publisher" TEXT NOT NULL,
    "commitHash" TEXT NOT NULL,
    "nonceTP" TEXT NOT NULL,
    "deadline" BIGINT NOT NULL,
    "status" "TaskStatus" NOT NULL DEFAULT 'CREATED',
    "publishTx" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "Task_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Miner" (
    "id" TEXT NOT NULL,
    "taskID" TEXT NOT NULL,
    "address" TEXT NOT NULL,

    CONSTRAINT "Miner_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Gradient" (
    "id" TEXT NOT NULL,
    "taskID" TEXT NOT NULL,
    "minerAddress" TEXT NOT NULL,
    "scoreCommit" TEXT NOT NULL,
    "encryptedHash" TEXT NOT NULL,
    "status" "GradientStatus" NOT NULL DEFAULT 'COMMITTED',

    CONSTRAINT "Gradient_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Block" (
    "id" TEXT NOT NULL,
    "taskID" TEXT NOT NULL,
    "modelHash" TEXT NOT NULL,
    "accuracy" BIGINT NOT NULL,
    "status" "BlockStatus" NOT NULL DEFAULT 'PENDING',

    CONSTRAINT "Block_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "Task_taskID_key" ON "Task"("taskID");

-- CreateIndex
CREATE UNIQUE INDEX "Miner_taskID_address_key" ON "Miner"("taskID", "address");

-- CreateIndex
CREATE INDEX "Gradient_taskID_minerAddress_idx" ON "Gradient"("taskID", "minerAddress");

-- CreateIndex
CREATE UNIQUE INDEX "Block_taskID_key" ON "Block"("taskID");

-- AddForeignKey
ALTER TABLE "Miner" ADD CONSTRAINT "Miner_taskID_fkey" FOREIGN KEY ("taskID") REFERENCES "Task"("taskID") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Gradient" ADD CONSTRAINT "Gradient_taskID_fkey" FOREIGN KEY ("taskID") REFERENCES "Task"("taskID") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Gradient" ADD CONSTRAINT "Gradient_taskID_minerAddress_fkey" FOREIGN KEY ("taskID", "minerAddress") REFERENCES "Miner"("taskID", "address") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Block" ADD CONSTRAINT "Block_taskID_fkey" FOREIGN KEY ("taskID") REFERENCES "Task"("taskID") ON DELETE RESTRICT ON UPDATE CASCADE;
