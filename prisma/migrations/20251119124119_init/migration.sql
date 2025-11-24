/*
  Warnings:

  - You are about to drop the `interview_screenshots` table. If the table is not empty, all the data it contains will be lost.

*/
-- DropForeignKey
ALTER TABLE "interview_screenshots" DROP CONSTRAINT "interview_screenshots_interviewId_fkey";

-- DropTable
DROP TABLE "interview_screenshots";

-- CreateTable
CREATE TABLE "interviewscreenshots" (
    "id" TEXT NOT NULL,
    "interviewId" TEXT NOT NULL,
    "imageUrl" TEXT NOT NULL,
    "faceVerified" BOOLEAN,
    "multiFace" BOOLEAN,
    "note" TEXT,
    "capturedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "interviewscreenshots_pkey" PRIMARY KEY ("id")
);

-- AddForeignKey
ALTER TABLE "interviewscreenshots" ADD CONSTRAINT "interviewscreenshots_interviewId_fkey" FOREIGN KEY ("interviewId") REFERENCES "interviews"("id") ON DELETE CASCADE ON UPDATE CASCADE;
