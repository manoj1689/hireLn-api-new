/*
  Warnings:

  - You are about to drop the column `resumeId` on the `candidates` table. All the data in the column will be lost.
  - You are about to drop the column `resumeName` on the `candidates` table. All the data in the column will be lost.

*/
-- AlterTable
ALTER TABLE "candidates" DROP COLUMN "resumeId",
DROP COLUMN "resumeName";
