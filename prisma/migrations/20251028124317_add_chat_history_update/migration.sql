/*
  Warnings:

  - A unique constraint covering the columns `[interviewId]` on the table `chat_history` will be added. If there are existing duplicate values, this will fail.
  - Added the required column `interviewId` to the `chat_history` table without a default value. This is not possible if the table is not empty.

*/
-- AlterTable
ALTER TABLE "chat_history" ADD COLUMN     "interviewId" TEXT NOT NULL;

-- CreateIndex
CREATE UNIQUE INDEX "chat_history_interviewId_key" ON "chat_history"("interviewId");
