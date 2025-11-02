/*
  Warnings:

  - The values [NO_SHOW] on the enum `InterviewStatus` will be removed. If these variants are still used in the database, this will fail.
  - The `applicationStatus` column on the `candidates` table would be dropped and recreated. This will lead to data loss if there is data in the column.
  - The `interviewStatus` column on the `candidates` table would be dropped and recreated. This will lead to data loss if there is data in the column.

*/
-- AlterEnum
ALTER TYPE "ApplicationStatus" ADD VALUE 'NEW';

-- AlterEnum
BEGIN;
CREATE TYPE "InterviewStatus_new" AS ENUM ('SCHEDULED', 'CONFIRMED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED', 'NOT_SCHEDULED', 'RESCHEDULED', 'INVITED', 'JOINED');
ALTER TABLE "interviews" ALTER COLUMN "status" DROP DEFAULT;
ALTER TABLE "candidates" ALTER COLUMN "interviewStatus" TYPE "InterviewStatus_new" USING ("interviewStatus"::text::"InterviewStatus_new");
ALTER TABLE "interviews" ALTER COLUMN "status" TYPE "InterviewStatus_new" USING ("status"::text::"InterviewStatus_new");
ALTER TYPE "InterviewStatus" RENAME TO "InterviewStatus_old";
ALTER TYPE "InterviewStatus_new" RENAME TO "InterviewStatus";
DROP TYPE "InterviewStatus_old";
ALTER TABLE "interviews" ALTER COLUMN "status" SET DEFAULT 'SCHEDULED';
COMMIT;

-- AlterTable
ALTER TABLE "candidates" DROP COLUMN "applicationStatus",
ADD COLUMN     "applicationStatus" "ApplicationStatus" NOT NULL DEFAULT 'NEW',
DROP COLUMN "interviewStatus",
ADD COLUMN     "interviewStatus" "InterviewStatus" NOT NULL DEFAULT 'NOT_SCHEDULED';
