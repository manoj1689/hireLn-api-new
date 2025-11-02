/*
  Warnings:

  - You are about to drop the `chathistory` table. If the table is not empty, all the data it contains will be lost.
  - You are about to drop the `interviewResults` table. If the table is not empty, all the data it contains will be lost.

*/
-- DropForeignKey
ALTER TABLE "chathistory" DROP CONSTRAINT "chathistory_userId_fkey";

-- DropForeignKey
ALTER TABLE "interviewResults" DROP CONSTRAINT "interviewResults_applicationId_fkey";

-- DropForeignKey
ALTER TABLE "interviewResults" DROP CONSTRAINT "interviewResults_interviewId_fkey";

-- DropTable
DROP TABLE "chathistory";

-- DropTable
DROP TABLE "interviewResults";

-- CreateTable
CREATE TABLE "interview_results" (
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

    CONSTRAINT "interview_results_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "chat_history" (
    "id" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "candidateId" TEXT,
    "applicationId" TEXT,
    "question" TEXT NOT NULL,
    "answer" TEXT,
    "score" INTEGER,
    "level" INTEGER NOT NULL DEFAULT 1,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "chat_history_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "interview_results_interviewId_key" ON "interview_results"("interviewId");

-- CreateIndex
CREATE UNIQUE INDEX "interview_results_applicationId_key" ON "interview_results"("applicationId");

-- AddForeignKey
ALTER TABLE "interview_results" ADD CONSTRAINT "interview_results_interviewId_fkey" FOREIGN KEY ("interviewId") REFERENCES "interviews"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "interview_results" ADD CONSTRAINT "interview_results_applicationId_fkey" FOREIGN KEY ("applicationId") REFERENCES "applications"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "chat_history" ADD CONSTRAINT "chat_history_userId_fkey" FOREIGN KEY ("userId") REFERENCES "users"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
