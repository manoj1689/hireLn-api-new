/*
  Warnings:

  - You are about to drop the `chat_history` table. If the table is not empty, all the data it contains will be lost.
  - You are about to drop the `interview_results` table. If the table is not empty, all the data it contains will be lost.

*/
-- DropForeignKey
ALTER TABLE "chat_history" DROP CONSTRAINT "chat_history_userId_fkey";

-- DropForeignKey
ALTER TABLE "interview_results" DROP CONSTRAINT "interview_results_applicationId_fkey";

-- DropForeignKey
ALTER TABLE "interview_results" DROP CONSTRAINT "interview_results_interviewId_fkey";

-- DropTable
DROP TABLE "chat_history";

-- DropTable
DROP TABLE "interview_results";

-- CreateTable
CREATE TABLE "interviewResults" (
    "id" TEXT NOT NULL,
    "interviewId" TEXT NOT NULL,
    "candidateId" TEXT NOT NULL,
    "applicationId" TEXT NOT NULL,
    "jobId" TEXT NOT NULL,
    "evaluatedCount" INTEGER NOT NULL,
    "totalQuestions" INTEGER NOT NULL,
    "averageFactualAccuracy" DOUBLE PRECISION NOT NULL,
    "averageCompleteness" DOUBLE PRECISION NOT NULL,
    "averageRelevance" DOUBLE PRECISION NOT NULL,
    "averageCoherence" DOUBLE PRECISION NOT NULL,
    "averageScore" DOUBLE PRECISION NOT NULL,
    "passStatus" TEXT NOT NULL,
    "summaryResult" TEXT NOT NULL,
    "knowledgeLevel" TEXT NOT NULL,
    "recommendations" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "interviewResults_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "chathistory" (
    "id" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "candidateId" TEXT,
    "applicationId" TEXT,
    "question" TEXT NOT NULL,
    "answer" TEXT,
    "score" INTEGER,
    "level" INTEGER NOT NULL DEFAULT 1,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "chathistory_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "interviewResults_interviewId_key" ON "interviewResults"("interviewId");

-- CreateIndex
CREATE UNIQUE INDEX "interviewResults_applicationId_key" ON "interviewResults"("applicationId");

-- AddForeignKey
ALTER TABLE "interviewResults" ADD CONSTRAINT "interviewResults_interviewId_fkey" FOREIGN KEY ("interviewId") REFERENCES "interviews"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "interviewResults" ADD CONSTRAINT "interviewResults_applicationId_fkey" FOREIGN KEY ("applicationId") REFERENCES "applications"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "chathistory" ADD CONSTRAINT "chathistory_userId_fkey" FOREIGN KEY ("userId") REFERENCES "users"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
