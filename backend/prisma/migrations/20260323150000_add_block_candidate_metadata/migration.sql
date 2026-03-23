-- Persist M4 candidate metadata for auditability and strict protocol replay.
ALTER TABLE "Block"
ADD COLUMN "modelLink" TEXT,
ADD COLUMN "candidateHash" TEXT,
ADD COLUMN "participants" TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
ADD COLUMN "scoreCommits" TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
ADD COLUMN "aggregatorPK" TEXT,
ADD COLUMN "signatureA" TEXT,
ADD COLUMN "artifactHash" TEXT,
ADD COLUMN "modelMetadata" JSONB,
ADD COLUMN "candidateTimestamp" BIGINT;
