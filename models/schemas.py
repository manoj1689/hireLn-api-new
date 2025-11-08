from pydantic import BaseModel, EmailStr, Field
from typing import Any, Dict, Optional, List, Union
from datetime import datetime
from enum import Enum
from decimal import Decimal

# Enums
class UserRole(str, Enum):
    ADMIN = "ADMIN"
    RECRUITER = "RECRUITER"
    HIRING_MANAGER = "HIRING_MANAGER"
    GUEST = "GUEST"


class AccountType(str, Enum):
    LIMITED_ACCESS = "LIMITED_ACCESS"
    FREE_TRIAL = "FREE_TRIAL"
    MONTHLY = "MONTHLY"
    YEARLY = "YEARLY"


class EmploymentType(str, Enum):
    FULL_TIME = "FULL_TIME"
    PART_TIME = "PART_TIME"
    CONTRACT = "CONTRACT"
    TEMPORARY = "TEMPORARY"
    INTERNSHIP = "INTERNSHIP"

class JobStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    CLOSED = "CLOSED"

class SalaryPeriod(str, Enum):
    yearly = "yearly"
    monthly = "monthly"
    weekly = "weekly"
    hourly = "hourly"

class ApplicationStatus(str, Enum):
    INVITED ="INVITED"
    APPLIED = "APPLIED"
    SCREENING = "SCREENING"
    INTERVIEW = "INTERVIEW"
    OFFER = "OFFER"
    HIRED = "HIRED"
    REJECTED = "REJECTED"

class InterviewType(str, Enum):
    PHONE = "PHONE"
    VIDEO = "VIDEO"
    IN_PERSON = "IN_PERSON"
    TECHNICAL = "TECHNICAL"
    BEHAVIORAL = "BEHAVIORAL"
    PANEL = "PANEL"

class InterviewStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    CONFIRMED = "CONFIRMED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    NO_SHOW = "NO_SHOW"
    RESCHEDULED = "RESCHEDULED"
    INVITED = "INVITED"  # When invite is sent but not confirmed
    JOINED = "JOINED"    # When candidate clicks join link



# User schemas
class UserRequest(BaseModel):
    token: str                                 # JWT or Firebase token from client
    fcm_token: Optional[str] = None            # Push notification token
    role: str = "RECRUITER"                    # RECRUITER | ADMIN | GUEST
    accountType: Optional[str] = "FREE_TRIAL"  # LIMITED_ACCESS | FREE_TRIAL | MONTHLY | YEARLY
    subscriptionActive: Optional[bool] = False
    trialEndsAt: Optional[datetime] = None     # Only for FREE_TRIAL

class GuestRequest(BaseModel):
    role: str = "GUEST" 
    accountType: Optional[str] = "FREE_TRIAL"
    subscriptionActive: Optional[bool] = False
    trialEndsAt: Optional[datetime] = None

class UserResponse(BaseModel):
    id: str
    googleId: Optional[str] = None
    name: str
    email: EmailStr
    avatar: Optional[str] = None
    role: str = "RECRUITER"                    # RECRUITER | ADMIN | GUEST
    registered: bool                           # True if user exists in DB
    fcm_token: Optional[str] = None
    accountType: str = "FREE_TRIAL"        # LIMITED_ACCESS | FREE_TRIAL | MONTHLY | YEARLY
    subscriptionActive: bool = False
    trialEndsAt: Optional[datetime] = None
    createdAt: datetime
    updatedAt: datetime

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# Core Job Schemas
class JobBase(BaseModel):
    title: str
    description: str
    department: str
    location: str
    employmentType: EmploymentType
    salaryMin: Optional[int] = None
    salaryMax: Optional[int] = None
    salaryPeriod: SalaryPeriod = SalaryPeriod.yearly
    requirements: List[str] = []
    responsibilities: List[str] = []
    skills: List[str] = []
    experience: Optional[str] = None
    education: Optional[str] = None
    isRemote: bool = False
    isHybrid: bool = False
    certifications: List[str] = []
    languages: List[Dict[str, Union[str, None]]] = []
    softSkills: List[str] = []

class JobCreate(JobBase):
    internalJobBoard: bool = False
    externalJobBoards: bool = True
    socialMedia: bool = False
    applicationFormFields: Dict[str, Union[str, int, bool]] = {}

class JobUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    employmentType: Optional[EmploymentType] = None
    salaryMin: Optional[int] = None
    salaryMax: Optional[int] = None
    salaryPeriod: Optional[SalaryPeriod] = None
    requirements: Optional[List[str]] = None
    responsibilities: Optional[List[str]] = None
    skills: Optional[List[str]] = None
    experience: Optional[str] = None
    education: Optional[str] = None
    status: Optional[JobStatus] = None
    isRemote: Optional[bool] = None
    isHybrid: Optional[bool] = None
    certifications: Optional[List[str]] = None
    languages: Optional[List[Dict[str, Union[str, None]]]] = None
    softSkills: Optional[List[str]] = None
    internalJobBoard: Optional[bool] = None
    externalJobBoards: Optional[bool] = None
    socialMedia: Optional[bool] = None
    applicationFormFields: Optional[Dict[str, Union[str, int, bool]]] = None


# Step-by-step job creation schemas
class JobBasicInfo(BaseModel):
    jobTitle: str
    department: str
    location: str
    employmentType: EmploymentType
    salaryMin: Optional[int] = None
    salaryMax: Optional[int] = None
    salaryPeriod: SalaryPeriod = SalaryPeriod.yearly

class JobDetails(BaseModel):
    jobDescription: str
    keyResponsibilities: List[str] = []
    workMode: str  # remote | hybrid | onsite
    requiredExperience: Optional[str] = None
    teamSize: str
    reportingStructure: str

class JobRequirements(BaseModel):
    requiredSkills: List[str] = []
    educationLevel: Optional[str] = None
    certifications: List[str] = []
    requirements: List[str] = []
    languages: List[Dict[str, str]] = []  # e.g. [{"language": "English", "level": "fluent"}]
    softSkills: List[str] = []

class JobPublishOptions(BaseModel):
    internalJobBoard: bool = False
    externalJobBoards: bool = True
    socialMedia: bool = False
    applicationFormFields: Dict[str, Union[str, int, bool]] = {}

class JobStepperCreate(BaseModel):
    basicInfo: JobBasicInfo
    jobDetails: JobDetails
    requirements: JobRequirements
    publishOptions: JobPublishOptions

# Step Responses
class SalaryRangeSuggestion(BaseModel):
    min: int
    max: int
    note: Optional[str] = None

class JobStep1Response(BaseModel):
    message: str
    step: int
    sessionId: str
    aiSuggestions: Dict[str, Union[str, List[str], SalaryRangeSuggestion]] = {}

class JobStep2Response(BaseModel):
    message: str
    step: int
    sessionId: str
    similarJobs: List[Dict[str, Union[str, int]]] = []

class JobStep3Response(BaseModel):
    message: str
    step: int
    sessionId: str
    jobData: Dict[str, Optional[dict]]

class JobResponse(JobBase):
    id: str
    status: JobStatus
    createdAt: datetime
    updatedAt: datetime
    publishedAt: Optional[datetime] = None
    closedAt: Optional[datetime] = None


class JobCreationCompleteResponse(BaseModel):
    message: str
    job: JobResponse
    publishedTo: List[str] = []

# Creating job for candidate
class JobCreateRequest(BaseModel):
    title: str = Field(..., min_length=2)
    department: str
    location: str
    employmentType: EmploymentType
    salaryMin: int
    salaryMax: int
    salaryPeriod: SalaryPeriod
    description: str
    skills: List[str]
    education: Optional[str] = None
    languages: List[Dict[str, str]] = []  # ✅ Add default


class GuestJobResponse(BaseModel):
    id: str
    title: str
    department: str
    location: str
    employmentType: EmploymentType
    salaryMin: int
    salaryMax: int
    salaryPeriod: SalaryPeriod
    description: str
    skills: List[str]
    education: Optional[str]
    createdAt: datetime



# Interview Scheduling Schemas
class CandidateEducation(BaseModel):
    degree: Optional[str]
    institution: Optional[str]
    location: Optional[str]
    start_date: Optional[str]
    end_date: Optional[str]
    grade: Optional[str]

class CandidateExperience(BaseModel):
    title: Optional[str]
    company: Optional[str]
    location: Optional[str]
    start_date: Optional[str]
    end_date: Optional[str]

class InterviewerInfo(BaseModel):
    name: str
    email: EmailStr
    role: Optional[str] = None
    avatar: Optional[str] = None

class InterviewScheduleRequest(BaseModel):
    candidateId: str
    applicationId: str
    type: InterviewType
    scheduledDate: str  # YYYY-MM-DD
    scheduledTime: str  # HH:MM
    duration: int = 60  # minutes
    # timezone: str = "UTC"
    timezone: str = "Asia/Kolkata" 
    interviewers: List[InterviewerInfo] = []
    meetingLink: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    sendCalendarInvite: bool = True
    sendEmailNotification: bool = True

class InterviewRescheduleRequest(BaseModel):
    newDate: str  # YYYY-MM-DD
    newTime: str  # HH:MM
    reason: str
    notifyCandidate: bool = True

class StartInterviewRequest(BaseModel):
    candidate: dict  # e.g., {"name": "John Doe", "role": "Software Engineer", "experience": "3 years"}

# ✅ Single chat entry (for interview history)
class ChatEntry(BaseModel):
    question: str
    answer: Optional[str] = None
    score: Optional[int] = None
    level: Optional[int] = 1
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ChatHistoryItem(BaseModel):
    question: str
    answer: str
    score: int
    level: int
    timestamp: datetime

class InterviewResponseRequest(BaseModel):
    interviewId: str
    jd_text: dict
    question: str
    user_input: str
    last_score: Optional[int] = 3
    last_level: Optional[int] = 1
    history: List[ChatHistoryItem]

class InterviewChatRequest(BaseModel):
    interviewId: str
    candidateId: str
    applicationId: str
    history: List[ChatHistoryItem]

class FinalScoreRequest(BaseModel):
    history: List[ChatHistoryItem]

class InterviewFeedbackRequest(BaseModel):
    rating: int  # 1-5 scale
    technicalSkills: int  # 1-5 scale
    communicationSkills: int  # 1-5 scale
    culturalFit: int  # 1-5 scale
    overallRecommendation: str  # HIRE, NO_HIRE, MAYBE
    strengths: List[str] = []
    weaknesses: List[str] = []
    detailedFeedback: str
    nextSteps: Optional[str] = None

class ScheduleInterviewResponse(BaseModel):
    # Core Interview Fields
    id: str
    candidateId: str
    candidateName: str
    candidateEmail: str
    applicationId: Optional[str]
    jobId: str
    jobTitle: str
    interviewType: InterviewType
    status: InterviewStatus
    scheduledAt: datetime
    duration: int
    timezone: str
    interviewers: List[InterviewerInfo] = []
    meetingLink: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    feedback: Optional[dict] = None
    invitationSent: bool = False
    joinToken: Optional[str] = None
    tokenExpiry: Optional[datetime] = None
    createdAt: datetime
    updatedAt: datetime
    startedAt: Optional[datetime] = None   # ✅ make optional
    completedAt: Optional[datetime] = None

    # Candidate Additional Fields
    candidateEducation: Optional[List[CandidateEducation]] = None
    candidateExperience:Optional[List[CandidateExperience]] = None
    candidateSkills: List[str] = []
    
    candidateLinkedIn: Optional[str] = None
    candidateGitHub: Optional[str] = None
    candidateLocation: Optional[str] = None

    # Application
    coverLetter: Optional[str] = None

    # Job Additional Fields
    jobDepartment: Optional[str] = None
    jobDescription: Optional[str] = None
    jobResponsibility: Optional[List[str]] = []
    jobSkills: Optional[List[str]] = []
    jobEducation: Optional[str] = None
    jobCertificates: Optional[List[str]] = []
    jobPublished: Optional[datetime] = None

class InterviewResponse(BaseModel):
    # Core Interview Fields
    id: str
    candidateId: str
    candidateName: str
    candidateEmail: str
    applicationId: Optional[str]
    jobId: str
    jobTitle: str
    interviewType: InterviewType
    status: InterviewStatus
    scheduledAt: datetime
    duration: int
    timezone: str
    interviewers: List[InterviewerInfo] = []
    meetingLink: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    feedback: Optional[dict] = None
    invitationSent: bool = False
    joinToken: Optional[str] = None
    tokenExpiry: Optional[datetime] = None
    createdAt: datetime
    updatedAt: datetime
    startedAt: Optional[datetime] = None   # ✅ make optional
    completedAt: Optional[datetime] = None

   

class InterviewCalendarEvent(BaseModel):
    title: str
    description: str
    startTime: datetime
    endTime: datetime
    attendees: List[str] = []
    location: Optional[str] = None
    meetingLink: Optional[str] = None

# New schemas for calendar integration and join tokens
class CalendarInviteResponse(BaseModel):
    success: bool
    eventId: Optional[str] = None
    message: str

class InterviewConfirmationRequest(BaseModel):
    interviewId: str
    confirmed: bool
    response: Optional[str] = None  # Optional response message from candidate

class InterviewJoinResponse(BaseModel):
    success: bool
    message: str
    interview: Optional[ScheduleInterviewResponse] = None
    redirectUrl: Optional[str] = None

# Candidate schemas
class PersonalInfo(BaseModel):
    dob: Optional[str] = None
    gender: Optional[str] = None
    maritalStatus: Optional[str] = None
    nationality: Optional[str] = None


class Certification(BaseModel):
    title: str
    issuer: Optional[str] = None
    date: Optional[str] = None


class Project(BaseModel):
    title: str
    description: Optional[str] = None
    url: Optional[str] = None


class Education(BaseModel):
    degree: Optional[str]
    institution: Optional[str]
    location: Optional[str]
    start_date: Optional[str]
    end_date: Optional[str]
    grade: Optional[str]

class Experience(BaseModel):
    title: Optional[str]
    company: Optional[str]
    location: Optional[str]
    start_date: Optional[str]
    end_date: Optional[str]
    
class PreviousJob(BaseModel):
    title: str
    company: str
    location: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: List[str] = []

class LanguageModel(BaseModel):
    language: Optional[str]
    proficiency: Optional[str]

class CandidateBase(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    address: List[str] = []
    location: Optional[str] = None

    personalInfo: Optional[PersonalInfo] = None
    summary: Optional[str] = None

    education: Optional[List[Education]] = None
    experience: Optional[List[Experience]] = None
    previousJobs: List[PreviousJob] = []

    internships: List[str] = []
    technicalSkills: List[str] = []
    softSkills: List[str] = []
    languages: Optional[List[LanguageModel]] = None
    certifications: Optional[List[Certification]] = None
    projects: Optional[List[Project]] = None
    hobbies: List[str] = []
    
    salaryExpectation: Optional[int] = None
    department: Optional[str] = None

    resume: Optional[str] = None
    portfolio: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None

class CandidateCreate(CandidateBase):
    pass

class CandidateResponse(CandidateBase):
    id: str
    applicationStatus: Optional[ApplicationStatus] = None
    interviewStatus: Optional[InterviewStatus] = None
    createdAt: datetime
    updatedAt: datetime

class CandidateWithInterviews(CandidateResponse):
    upcomingInterviews: List[InterviewResponse] = []
    pastInterviews: List[InterviewResponse] = []
    applicationStatus: ApplicationStatus



# Application schemas
class ApplicationBase(BaseModel):
    jobId: str
    candidateId: str
    coverLetter: Optional[str] = None
    matchScore: Optional[int] = None

class ApplicationCreate(ApplicationBase):
    userId: str  # Add userId to ApplicationCreate
    appliedAt: datetime = datetime.utcnow()  # Automatically set the appliedAt timestamp

class ApplicationUpdate(BaseModel):
    status: Optional[ApplicationStatus] = None
    notes: Optional[str] = None
    matchScore: Optional[int] = None

class ApplicationResponse(ApplicationBase):
    id: str
    status: ApplicationStatus
    matchScore: Optional[int] = None
    notes: Optional[str] = None
    userId: str
    appliedAt: datetime
    updatedAt: datetime
    joinToken: Optional[str] = None
    tokenExpiry: Optional[datetime] = None

# Dashboard schemas

class MetricWithChange(BaseModel):
    value: int | float
    change: float  # percentage change

class DashboardMetrics(BaseModel):
    totalJobs: MetricWithChange
    activeCandidates: MetricWithChange
    hiringSuccessRate: MetricWithChange
    avgTimeToHire: MetricWithChange
    aiInterviewsCompleted: MetricWithChange

class RecruitmentTrend(BaseModel):
    month: str
    applications: int

class PipelineStage(BaseModel):
    stage: str
    count: int
    percentage: int

class ActivityItem(BaseModel):
    id: str
    type: str
    title: str
    description: str
    time: str

# Settings schemas
class UserSettingsBase(BaseModel):
    language: str = "en-US"
    timezone: str = "UTC"
    dateFormat: str = "MM/DD/YYYY"
    autoSave: bool = True
    emailDailyDigest: bool = True
    emailNewCandidateAlerts: bool = True
    emailMarketingEmails: bool = False
    emailNewApplications: bool = True
    pushNewApplications: bool = True
    emailInterviewReminders: bool = True
    pushInterviewReminders: bool = True
    emailTaskDeadlines: bool = True
    pushTaskDeadlines: bool = False
    emailProductUpdates: bool = True
    pushProductUpdates: bool = False
    emailSecurityAlerts: bool = True
    pushSecurityAlerts: bool = True

class UserSettingsCreate(UserSettingsBase):
    userId: str

class UserSettingsUpdate(BaseModel):
    language: Optional[str] = None
    timezone: Optional[str] = None
    dateFormat: Optional[str] = None
    autoSave: Optional[bool] = None
    emailDailyDigest: Optional[bool] = None
    emailNewCandidateAlerts: Optional[bool] = None
    emailMarketingEmails: Optional[bool] = None
    emailNewApplications: Optional[bool] = None
    pushNewApplications: Optional[bool] = None
    emailInterviewReminders: Optional[bool] = None
    pushInterviewReminders: Optional[bool] = None
    emailTaskDeadlines: Optional[bool] = None
    pushTaskDeadlines: Optional[bool] = None
    emailProductUpdates: Optional[bool] = None
    pushProductUpdates: Optional[bool] = None
    emailSecurityAlerts: Optional[bool] = None
    pushSecurityAlerts: Optional[bool] = None

class UserSettingsResponse(UserSettingsBase):
    id: str
    userId: str
    createdAt: datetime
    updatedAt: datetime

class GeneralSettingsUpdate(BaseModel):
    language: Optional[str] = None
    timezone: Optional[str] = None
    dateFormat: Optional[str] = None
    autoSave: Optional[bool] = None

class EmailSettingsUpdate(BaseModel):
    emailDailyDigest: Optional[bool] = None
    emailNewCandidateAlerts: Optional[bool] = None
    emailMarketingEmails: Optional[bool] = None

class NotificationSettingsUpdate(BaseModel):
    emailNewApplications: Optional[bool] = None
    pushNewApplications: Optional[bool] = None
    emailInterviewReminders: Optional[bool] = None
    pushInterviewReminders: Optional[bool] = None
    emailTaskDeadlines: Optional[bool] = None
    pushTaskDeadlines: Optional[bool] = None
    emailProductUpdates: Optional[bool] = None
    pushProductUpdates: Optional[bool] = None
    emailSecurityAlerts: Optional[bool] = None
    pushSecurityAlerts: Optional[bool] = None

# Company schemas
class SocialMediaLinks(BaseModel):
    linkedin: Optional[str] = None
    twitter: Optional[str] = None
    facebook: Optional[str] = None
    instagram: Optional[str] = None


class FeaturedImage(BaseModel):
    url: str
    caption: Optional[str] = None

class CompanyBase(BaseModel):
    name: str
    description: Optional[str] = None
    industry: Optional[str] = None
    founded: Optional[int] = None
    companySize: Optional[str] = None
    website: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    taxId: Optional[str] = None
    logo: Optional[str] = None
    coverImage: Optional[str] = None
    primaryColor: str = "#10b981"
    secondaryColor: str = "#3b82f6"
    careerHeadline: Optional[str] = None
    careerDescription: Optional[str] = None
    featuredImages: Optional[List[FeaturedImage]] = None
    socialMedia: Optional[SocialMediaLinks] = None
    remoteWorkPolicy: Optional[str] = None
    remoteHiringRegions: List[str] = []

class CompanyCreate(CompanyBase):
    pass

class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    founded: Optional[int] = None
    companySize: Optional[str] = None
    website: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    taxId: Optional[str] = None
    logo: Optional[str] = None
    coverImage: Optional[str] = None
    primaryColor: Optional[str] = None
    secondaryColor: Optional[str] = None
    careerHeadline: Optional[str] = None
    careerDescription: Optional[str] = None
    featuredImages: Optional[List[FeaturedImage]] = None
    socialMedia: Optional[SocialMediaLinks] = None
    remoteWorkPolicy: Optional[str] = None
    remoteHiringRegions: Optional[List[str]] = None

class CompanyResponse(CompanyBase):
    id: str
    userId: str
    createdAt: datetime
    updatedAt: datetime

# Company Location schemas
class CompanyLocationBase(BaseModel):
    name: str
    type: str = "office"
    address: str
    city: str
    state: Optional[str] = None
    country: str
    zipCode: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    isHeadquarters: bool = False

class CompanyLocationCreate(CompanyLocationBase):
    pass

class CompanyLocationUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    zipCode: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    isHeadquarters: Optional[bool] = None

class CompanyLocationResponse(CompanyLocationBase):
    id: str
    companyId: str
    createdAt: datetime
    updatedAt: datetime

# Team Member schemas
class TeamMemberBase(BaseModel):
    name: str
    email: EmailStr
    role: str
    department: str
    phone: Optional[str] = None
    avatar: Optional[str] = None
    status: str = "active"
    accessLevel: str = "member"

class TeamMemberCreate(TeamMemberBase):
    pass

class TeamMemberInvite(BaseModel):
    name: str
    email: EmailStr
    role: str
    department: str
    accessLevel: str = "member"

class TeamMemberUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    department: Optional[str] = None
    phone: Optional[str] = None
    avatar: Optional[str] = None
    status: Optional[str] = None
    accessLevel: Optional[str] = None

class TeamMemberResponse(TeamMemberBase):
    id: str
    companyId: str
    invitedAt: Optional[datetime] = None
    joinedAt: Optional[datetime] = None
    invitedBy: Optional[str] = None
    createdAt: datetime
    updatedAt: datetime

# Subscription schemas
class SubscriptionBase(BaseModel):
    planName: str
    planPrice: Decimal
    billingCycle: str = "monthly"
    status: str = "active"
    currentPeriodStart: datetime
    currentPeriodEnd: datetime
    cancelAtPeriodEnd: bool = False
    teamMemberLimit: int = 25
    aiCreditsLimit: int = 1000
    storageLimit: int = 10

class SubscriptionCreate(SubscriptionBase):
    stripeSubscriptionId: Optional[str] = None
    stripeCustomerId: Optional[str] = None

class SubscriptionUpdate(BaseModel):
    planName: Optional[str] = None
    planPrice: Optional[Decimal] = None
    billingCycle: Optional[str] = None
    status: Optional[str] = None
    currentPeriodEnd: Optional[datetime] = None
    cancelAtPeriodEnd: Optional[bool] = None
    teamMemberLimit: Optional[int] = None
    aiCreditsLimit: Optional[int] = None
    storageLimit: Optional[int] = None

class SubscriptionResponse(SubscriptionBase):
    id: str
    companyId: str
    stripeSubscriptionId: Optional[str] = None
    stripeCustomerId: Optional[str] = None
    createdAt: datetime
    updatedAt: datetime

# Payment Method schemas
class PaymentMethodBase(BaseModel):
    type: str = "card"
    last4: str
    brand: str
    expiryMonth: int
    expiryYear: int
    isDefault: bool = False

class PaymentMethodCreate(PaymentMethodBase):
    stripePaymentMethodId: Optional[str] = None

class PaymentMethodUpdate(BaseModel):
    isDefault: Optional[bool] = None

class PaymentMethodResponse(PaymentMethodBase):
    id: str
    companyId: str
    stripePaymentMethodId: Optional[str] = None
    createdAt: datetime
    updatedAt: datetime

# Billing Address schemas
class BillingAddressBase(BaseModel):
    contactName: str
    contactEmail: EmailStr
    contactPhone: Optional[str] = None
    companyName: str
    addressLine1: str
    addressLine2: Optional[str] = None
    city: str
    state: Optional[str] = None
    zipCode: str
    country: str

class BillingAddressCreate(BillingAddressBase):
    pass

class BillingAddressUpdate(BaseModel):
    contactName: Optional[str] = None
    contactEmail: Optional[EmailStr] = None
    contactPhone: Optional[str] = None
    companyName: Optional[str] = None
    addressLine1: Optional[str] = None
    addressLine2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zipCode: Optional[str] = None
    country: Optional[str] = None

class BillingAddressResponse(BillingAddressBase):
    id: str
    companyId: str
    createdAt: datetime
    updatedAt: datetime

# Invoice schemas
class InvoiceBase(BaseModel):
    invoiceNumber: str
    amount: Decimal
    currency: str = "USD"
    status: str = "pending"
    dueDate: datetime
    paidAt: Optional[datetime] = None

class InvoiceCreate(InvoiceBase):
    stripeInvoiceId: Optional[str] = None
    downloadUrl: Optional[str] = None

class InvoiceUpdate(BaseModel):
    status: Optional[str] = None
    paidAt: Optional[datetime] = None
    downloadUrl: Optional[str] = None

class InvoiceResponse(InvoiceBase):
    id: str
    companyId: str
    stripeInvoiceId: Optional[str] = None
    downloadUrl: Optional[str] = None
    createdAt: datetime
    updatedAt: datetime

# Subscription Addon schemas
class SubscriptionAddonBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: Decimal
    billingCycle: str = "monthly"
    isActive: bool = True

class SubscriptionAddonCreate(SubscriptionAddonBase):
    pass

class SubscriptionAddonUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    billingCycle: Optional[str] = None
    isActive: Optional[bool] = None

class SubscriptionAddonResponse(SubscriptionAddonBase):
    id: str
    subscriptionId: str
    createdAt: datetime
    updatedAt: datetime

# Usage and Plan Information
class PlanUsage(BaseModel):
    teamMembers: Dict[str, Union[int, str]]  # {"current": 18, "limit": 25}
    aiCredits: Dict[str, Union[int, str]]    # {"current": 873, "limit": 1000}
    storage: Dict[str, Union[int, str]]      # {"current": 4.2, "limit": 10, "unit": "GB"}

class PlanFeature(BaseModel):
    name: str
    included: bool
    description: Optional[str] = None

class PlanDetails(BaseModel):
    name: str
    price: Decimal
    billingCycle: str
    features: List[PlanFeature]
    limits: Dict[str, int]

# AI Tools schemas
class ErrorResponse(BaseModel):
    detail: str


# New schemas for resume parsing

    
class ResumeParseResult(BaseModel):
    file_name: str
    data: Optional[CandidateCreate] = None
    error: Optional[str] = None

class ParseResumesFromDriveResponse(BaseModel):
    folder_id: str
    resumes: List[CandidateCreate]
    message: str = "Resume parsing initiated."


class Tool(BaseModel):
    name: str
    description: str
    inputSchema: Dict[str, Any]  # <-- required

# New schemas for interview evaluation

class EvaluationRequestItem(BaseModel):
    question: str
    answer: str

class EvaluationRequest(BaseModel):
    interviewId: str
    evaluations: list[EvaluationRequestItem]  # Each question-answer to evaluate

class EvaluationResponseItem(BaseModel):
    question: str
    answer: str
    score: Optional[float]
    id: str
    createdAt: datetime

class EvaluationResponse(BaseModel):
    interviewId: str
    results: list[EvaluationResponseItem]
    message: str