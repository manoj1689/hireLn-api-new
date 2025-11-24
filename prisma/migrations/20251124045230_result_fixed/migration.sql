/*
  Warnings:

  - You are about to drop the column `applicationId` on the `interview_results` table. All the data in the column will be lost.

*/
-- DropForeignKey
ALTER TABLE "interview_results" DROP CONSTRAINT "interview_results_applicationId_fkey";

-- DropIndex
DROP INDEX "interview_results_applicationId_key";

-- AlterTable
ALTER TABLE "interview_results" DROP COLUMN "applicationId";
