/*
  Warnings:

  - You are about to drop the `interviewscreenshots` table. If the table is not empty, all the data it contains will be lost.

*/
-- DropForeignKey
ALTER TABLE "interviewscreenshots" DROP CONSTRAINT "interviewscreenshots_interviewId_fkey";

-- DropTable
DROP TABLE "interviewscreenshots";

-- CreateTable
CREATE TABLE "interviewscreenshot" (
    "id" TEXT NOT NULL,
    "interviewId" TEXT NOT NULL,
    "imageUrl" TEXT NOT NULL,
    "faceVerified" BOOLEAN,
    "multiFace" BOOLEAN,
    "note" TEXT,
    "capturedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "interviewscreenshot_pkey" PRIMARY KEY ("id")
);

-- AddForeignKey
ALTER TABLE "interviewscreenshot" ADD CONSTRAINT "interviewscreenshot_interviewId_fkey" FOREIGN KEY ("interviewId") REFERENCES "interviews"("id") ON DELETE CASCADE ON UPDATE CASCADE;
