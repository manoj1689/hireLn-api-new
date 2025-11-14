-- CreateTable
CREATE TABLE "skill_suggestions" (
    "id" TEXT NOT NULL,
    "department" TEXT NOT NULL,
    "suggestions" TEXT[],
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "skill_suggestions_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "_JobSkillSuggestions" (
    "A" TEXT NOT NULL,
    "B" TEXT NOT NULL
);

-- CreateTable
CREATE TABLE "_CandidateSkillSuggestions" (
    "A" TEXT NOT NULL,
    "B" TEXT NOT NULL
);

-- CreateIndex
CREATE UNIQUE INDEX "_JobSkillSuggestions_AB_unique" ON "_JobSkillSuggestions"("A", "B");

-- CreateIndex
CREATE INDEX "_JobSkillSuggestions_B_index" ON "_JobSkillSuggestions"("B");

-- CreateIndex
CREATE UNIQUE INDEX "_CandidateSkillSuggestions_AB_unique" ON "_CandidateSkillSuggestions"("A", "B");

-- CreateIndex
CREATE INDEX "_CandidateSkillSuggestions_B_index" ON "_CandidateSkillSuggestions"("B");

-- AddForeignKey
ALTER TABLE "_JobSkillSuggestions" ADD CONSTRAINT "_JobSkillSuggestions_A_fkey" FOREIGN KEY ("A") REFERENCES "jobs"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "_JobSkillSuggestions" ADD CONSTRAINT "_JobSkillSuggestions_B_fkey" FOREIGN KEY ("B") REFERENCES "skill_suggestions"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "_CandidateSkillSuggestions" ADD CONSTRAINT "_CandidateSkillSuggestions_A_fkey" FOREIGN KEY ("A") REFERENCES "candidates"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "_CandidateSkillSuggestions" ADD CONSTRAINT "_CandidateSkillSuggestions_B_fkey" FOREIGN KEY ("B") REFERENCES "skill_suggestions"("id") ON DELETE CASCADE ON UPDATE CASCADE;
