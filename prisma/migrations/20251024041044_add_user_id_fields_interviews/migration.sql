/*
  Warnings:

  - Added the required column `userId` to the `interviews` table without a default value. This is not possible if the table is not empty.

*/
-- AlterTable
ALTER TABLE "interviews" ADD COLUMN     "userId" TEXT NOT NULL;
