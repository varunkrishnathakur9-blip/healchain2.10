-- AlterTable
ALTER TABLE "Miner" ADD COLUMN     "proof" TEXT,
ADD COLUMN     "proofVerified" BOOLEAN NOT NULL DEFAULT false;
