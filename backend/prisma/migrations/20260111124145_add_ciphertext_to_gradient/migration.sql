/*
  Warnings:

  - Added the required column `ciphertext` to the `Gradient` table without a default value. This is not possible if the table is not empty.

*/
-- AlterTable
ALTER TABLE "Gradient" ADD COLUMN     "ciphertext" TEXT,
ADD COLUMN     "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
ADD COLUMN     "signature" TEXT;
