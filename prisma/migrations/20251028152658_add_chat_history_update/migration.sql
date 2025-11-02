/*
  Warnings:

  - You are about to drop the column `userId` on the `chat_history` table. All the data in the column will be lost.

*/
-- DropForeignKey
ALTER TABLE "chat_history" DROP CONSTRAINT "chat_history_userId_fkey";

-- AlterTable
ALTER TABLE "chat_history" DROP COLUMN "userId";

-- AddForeignKey
ALTER TABLE "chat_history" ADD CONSTRAINT "chat_history_interviewId_fkey" FOREIGN KEY ("interviewId") REFERENCES "interviews"("id") ON DELETE CASCADE ON UPDATE CASCADE;
