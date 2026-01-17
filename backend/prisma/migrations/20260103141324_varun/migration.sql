-- AlterTable
ALTER TABLE "Miner" ADD COLUMN     "publicKey" TEXT,
ADD COLUMN     "stake" BIGINT DEFAULT 0;

-- AlterTable
ALTER TABLE "Task" ADD COLUMN     "aggregatorAddress" TEXT;

-- CreateTable
CREATE TABLE "KeyDelivery" (
    "id" TEXT NOT NULL,
    "taskID" TEXT NOT NULL,
    "aggregatorAddress" TEXT NOT NULL,
    "encryptedKey" TEXT NOT NULL,
    "deliveredAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "KeyDelivery_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Verification" (
    "id" TEXT NOT NULL,
    "taskID" TEXT NOT NULL,
    "minerAddress" TEXT NOT NULL,
    "verdict" TEXT NOT NULL,
    "signature" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Verification_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Reward" (
    "id" TEXT NOT NULL,
    "taskID" TEXT NOT NULL,
    "minerAddress" TEXT NOT NULL,
    "score" BIGINT NOT NULL,
    "amountETH" TEXT NOT NULL,
    "txHash" TEXT,
    "status" TEXT NOT NULL DEFAULT 'CALCULATED',
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Reward_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "KeyDelivery_taskID_aggregatorAddress_key" ON "KeyDelivery"("taskID", "aggregatorAddress");

-- CreateIndex
CREATE UNIQUE INDEX "Verification_taskID_minerAddress_key" ON "Verification"("taskID", "minerAddress");

-- CreateIndex
CREATE INDEX "Reward_taskID_idx" ON "Reward"("taskID");

-- AddForeignKey
ALTER TABLE "KeyDelivery" ADD CONSTRAINT "KeyDelivery_taskID_fkey" FOREIGN KEY ("taskID") REFERENCES "Task"("taskID") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Verification" ADD CONSTRAINT "Verification_taskID_fkey" FOREIGN KEY ("taskID") REFERENCES "Task"("taskID") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Verification" ADD CONSTRAINT "Verification_taskID_minerAddress_fkey" FOREIGN KEY ("taskID", "minerAddress") REFERENCES "Miner"("taskID", "address") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Reward" ADD CONSTRAINT "Reward_taskID_fkey" FOREIGN KEY ("taskID") REFERENCES "Task"("taskID") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Reward" ADD CONSTRAINT "Reward_taskID_minerAddress_fkey" FOREIGN KEY ("taskID", "minerAddress") REFERENCES "Miner"("taskID", "address") ON DELETE RESTRICT ON UPDATE CASCADE;
