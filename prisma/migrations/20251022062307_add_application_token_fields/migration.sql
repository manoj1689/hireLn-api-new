-- AlterTable
ALTER TABLE "applications" ADD COLUMN     "joinToken" TEXT,
ADD COLUMN     "tokenExpiry" TIMESTAMP(3);
