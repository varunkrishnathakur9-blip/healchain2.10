-- Strict M5 feedback metadata and per-candidate uniqueness.
ALTER TABLE "Block"
ADD COLUMN "round" INTEGER;

ALTER TABLE "Verification"
ADD COLUMN "candidateHash" TEXT NOT NULL DEFAULT '',
ADD COLUMN "reason" TEXT NOT NULL DEFAULT '',
ADD COLUMN "message" TEXT;

-- Replace one-vote-per-task with one-vote-per-candidate.
DROP INDEX IF EXISTS "Verification_taskID_minerAddress_key";
CREATE UNIQUE INDEX "Verification_taskID_minerAddress_candidateHash_key"
ON "Verification"("taskID", "minerAddress", "candidateHash");
