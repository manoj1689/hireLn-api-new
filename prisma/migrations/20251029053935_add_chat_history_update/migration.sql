/*
  Warnings:

  - You are about to drop the column `userId` on the `evaluations` table. All the data in the column will be lost.
  - Added the required column `interviewId` to the `evaluations` table without a default value. This is not possible if the table is not empty.

*/
-- AlterTable
ALTER TABLE "evaluations" DROP COLUMN "userId",
ADD COLUMN     "interviewId" TEXT NOT NULL;

-- AddForeignKey
ALTER TABLE "evaluations" ADD CONSTRAINT "evaluations_interviewId_fkey" FOREIGN KEY ("interviewId") REFERENCES "interviews"("id") ON DELETE CASCADE ON UPDATE CASCADE;
