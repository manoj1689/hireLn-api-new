import smtplib
import os
import json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.email_address = os.getenv("EMAIL_ADDRESS")
        self.email_password = os.getenv("EMAIL_PASSWORD")

    def _create_smtp_connection(self):
        """Create and return SMTP connection"""
        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email_address, self.email_password)
            return server
        except Exception as e:
            logger.error(f"Failed to create SMTP connection: {e}")
            return None

    def send_email(self, to_email: str, subject: str, body: str, html_body: Optional[str] = None) -> bool:
        """Send email with optional HTML body"""
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = self.email_address
            msg['To'] = to_email
            msg['Subject'] = subject

            msg.attach(MIMEText(body, 'plain'))
            if html_body:
                msg.attach(MIMEText(html_body, 'html'))

            server = self._create_smtp_connection()
            if server is None:
                return False

            server.send_message(msg)
            server.quit()
            logger.info(f"Email sent successfully to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    
    def send_interview_accept(
        self,
        candidate_email: str,
        candidate_name: str,
        application_id: str,
        job_id:str,
        application_title: str,
        join_token:str,
        frontend_url: str = "https://hireln.com" 
        # frontend_url: str = "http://localhost:3000"  
    ) -> bool:
        """
        Send an ACCEPT/REJECT invitation email with a link.
        """
        subject = f"Invitation to Interview for {application_title}"
        invitation_link = f"{frontend_url}/ai-interview-accept?application_id={application_id}&job_id={job_id}&token={join_token}"

        body = f"""
            Hi {candidate_name},

            Congratulations! Your application for the position of {application_title} has been shortlisted.

            Please use the link below to confirm your participation in the interview process:

            {invitation_link}

            If you are unable to attend or have any schedule constraints, feel free to write back so we can reschedule.

            We look forward to speaking with you.

            Best Regards,  
            Hiring Team
            """

        html_body = f"""
            <body style="font-family:Arial,sans-serif; background:#ffffff; padding:20; margin:0;">
            <div style="max-width:600px; margin:auto; background:#ffffff; border-radius:8px; border:1px solid #e5e7eb;">
                
                <!-- Header -->
                <div style="background: linear-gradient(to right, #38BDF8, #F472B6); padding:18px; text-align:center; color:#fff;">
                <h2 style="margin:0; font-size:20px;">Interview Invitation – {application_title}</h2>
                </div>

                <!-- Body Content -->
                <div style="padding:24px; color:#374151; font-size:15px; line-height:1.6;">
                <p>Hi {candidate_name},</p>

                <p>
                    Congratulations! We are pleased to inform you that you have been 
                    shortlisted for the <strong>{application_title}</strong> position.
                </p>

                <p>
                    Please use the link below to <strong>accept or decline</strong> the interview invitation:
                </p>

                <!-- ✅ Clickable Link Instead of Button -->
                <p style="margin:16px 0; font-size:15px;">
                    <a href="{invitation_link}" target="_blank" 
                    style="color:#2563eb; text-decoration:underline; font-weight:bold;">
                    Click here to Accept or Reject Interview Invitation
                    </a>
                </p>

                <p>
                    If you have any questions or need to request a different interview time, 
                    you may reply directly to this email.
                </p>

                <p>We look forward to your response.</p>

                <p>Best regards,<br><strong>Hiring Team</strong></p>
                </div>

                <!-- Footer -->
                <div style="background:#f3f4f6; padding:12px; text-align:center; font-size:12px; color:#6b7280;">
                <p style="margin:0;">This is an automated email. Do not share your invite link.</p>
                </div>

            </div>
            </body>

            """


        return self.send_email(candidate_email, subject, body, html_body)


    
    def send_interview_invitation(self, 
        candidate_email: str, 
        candidate_name: str,
        job_title: str,
        interview_type: str,
        scheduled_at: datetime,
        duration: int,
        meeting_link: Optional[str] = None,
        location: Optional[str] = None,
        interviewers: Optional[List[str]] = None,
        interview_id: Optional[str] = None,
        join_token: Optional[str] = None,
        frontend_url: str = "https://hireln.com"
        # frontend_url: str = "http://localhost:3000"
    ) -> bool:
        """Send interview invitation email with full interview metadata"""

        interview_date = scheduled_at.strftime("%B %d, %Y")
        interview_time = scheduled_at.strftime("%I:%M %p")
        join_url = f"{frontend_url}/ai-interview-round?interview_id={interview_id}"
        if join_token:
                join_url += f"&token={join_token}"
        subject = f"Interview Invitation for {job_title}"

        body = f"""Dear {candidate_name},

    You have been invited to an interview for the position of {job_title}.

    Interview Details:
    - Date: {interview_date}
    - Time: {interview_time}
    - Duration: {duration} minutes
    - Type: {interview_type}"""

        if location:
            body += f"\n- Location: {location}"
        if join_url:
            body += f"\n- Join Link: {join_url}"
        if interviewers:
            body += f"\n- Interviewers: {', '.join(interviewers)}"

        body += f"""

    Interview ID: {interview_id or 'N/A'}

    Please confirm your attendance by replying to this email.

    Best regards,
    Hiring Team
    """

        html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
 <style>
    body {{
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background-color: #f3f4f6;
    margin: 0;
    padding: 0;
    color: #111827;
    }}
    .container {{
    max-width: 600px;
    margin: 20px auto;
    background-color: #ffffff;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }}
    .header {{
    background-color: #34d399;
    color: #ffffff;
    padding: 24px;
    text-align: center;
    }}
    .content {{
    padding: 24px;
    }}
    .content p {{
    margin: 12px 0;
    line-height: 1.6;
    }}
    .details {{
    background-color: #f9fafb;
    border-left: 4px solid #34d399;
    padding: 16px;
    margin: 20px 0;
    border-radius: 8px;
    }}
    .details p {{
    margin: 8px 0;
    }}
    .button-wrapper {{
    text-align: center;
    margin: 24px 0;
    }}
    .button {{
    background-color: #34d399;
    color: #ffffff !important;
    text-decoration: none;
    padding: 14px 28px;
    font-size: 16px;
    border-radius: 6px;
    display: inline-block;
    transition: background-color 0.2s ease;
    }}
    .button:hover {{
    background-color: #10b981;
    color: #ffffff !important;
    }}
    .footer {{
    font-size: 14px;
    color: #6b7280;
    text-align: center;
    padding: 16px;
    }}
</style>

    </head>
        <body style="font-family: Arial, sans-serif; background-color:#f6f9fc; margin:0; padding:0;">
        <div style="max-width:600px; margin:auto; background:#ffffff; border-radius:8px; overflow:hidden; border:1px solid #e5e7eb;">
            
            <!-- Header -->
            <div style="background:#2563eb; padding:20px; text-align:center; color:#ffffff;">
            <h2 style="margin:0; font-size:22px;">Interview Invitation – {job_title}</h2>
            </div>

            <!-- Body -->
            <div style="padding:25px; color:#374151;">
            <p style="font-size:16px;">Hi {candidate_name},</p>

            <p style="font-size:15px; line-height:1.6;">
                Congratulations! Based on your application, we are pleased to invite you to the interview process for the
                <strong>{job_title}</strong> role.
            </p>

            <p style="font-size:15px; line-height:1.6;">Below are the interview details:</p>

            <!-- Interview Details Box -->
            <div style="background:#f9fafb; padding:15px; border-radius:6px; border:1px solid #e5e7eb; font-size:14px; line-height:1.7;">
                <p><strong>Date:</strong> {interview_date}</p>
                <p><strong>Time:</strong> {interview_time}</p>
                <p><strong>Duration:</strong> {duration} minutes</p>
                <p><strong>Format:</strong> {interview_type}</p>
                {f'<p><strong>Location:</strong> {location}</p>' if location else ''}
                {f'<p><strong>Interviewers:</strong> {", ".join(interviewers)}</p>' if interviewers else ''}
                <p><strong>Interview ID:</strong> {interview_id or 'N/A'}</p>
            </div>

            <!-- CTA Button -->
            {f'''
            <div style="text-align:center; margin:25px 0;">
                <a href="{join_url}" 
                style="background:#2563eb; color:white; padding:12px 25px; text-decoration:none; font-size:15px; border-radius:6px; display:inline-block;">
                Join Interview
                </a>
            </div>
            ''' if join_url else ''}

            <p style="font-size:15px; line-height:1.6;">
                Please confirm your availability by replying to this email. If you have any scheduling concerns or require assistance, feel free to contact us.
            </p>

            <p style="font-size:15px; line-height:1.6;">
                We look forward to speaking with you!
            </p>
            </div>

            <!-- Footer -->
            <div style="background:#f3f4f6; padding:15px; text-align:center; font-size:13px; color:#6b7280;">
            <p style="margin:0;">Best regards,<br><strong>Hiring Team</strong></p>
            <p style="margin-top:8px; font-size:12px; color:#9ca3af;">
                This is an automated email. Please do not share your interview link with anyone.
            </p>
            </div>

        </div>
        </body>

    </html>
    """

        return self.send_email(candidate_email, subject, body, html_body)

    def send_individual_result(
        self,
        email: str,
        name: str,
        organization_name: str,
        invitation_token: Optional[str],
        application_status: Optional[str],
        score: Optional[float],
        job_title: Optional[str],
        department: Optional[str],
        interview_date: Optional[str],
        message: Optional[str] = None,
    ) -> bool:
        """Send post-interview result email with optional invitation to selected candidate"""

        subject = f"Your Interview Result for {job_title or 'the position'} at {organization_name}"
        registration_link = (
            f"{os.getenv('FRONTEND_URL', 'https://hireln.com')}/register/individual?token={invitation_token}"
            if invitation_token else None
        )

        plain_details = f"""
    Interview Date: {interview_date or 'N/A'}
    Application Status: {application_status or 'N/A'}
    Score: {score if score is not None else 'N/A'}
    Job Title: {job_title or 'N/A'}
    Department: {department or 'N/A'}
    """

        # Plain text body
        body = f"""
    Dear {name},

    Thank you for interviewing for the position of {job_title or 'a role'} at {organization_name}.

    Here is a summary of your application:
    {plain_details}

    {f'Message from the team: {message}' if message else ''}

    {f'To proceed and join our team, please complete your registration here: {registration_link}' if registration_link else ''}

    Best regards,  
    {organization_name} Team
    """

        # HTML body
        html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #4f46e5; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; background-color: #f9fafb; }}
        .result-box, .details-box {{
        background-color: white; padding: 20px; border-radius: 8px; margin: 20px 0;
        border-left: 4px solid #4f46e5;
        }}
        .button {{
        display: inline-block; padding: 12px 24px; background-color: #4f46e5;
        color: white; text-decoration: none; border-radius: 5px; margin: 15px 0;
        }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 14px; }}
    </style>
    </head>
    <body>
    <div class="container">
        <div class="header">
        <h1>Interview Result</h1>
        </div>
        <div class="content">
        <p>Dear {name},</p>
        <div class="result-box">
            <h3>Thank you for interviewing for <strong>{job_title or 'the position'}</strong> at {organization_name}.</h3>
            {f'<p><em>"{message}"</em></p>' if message else ''}
        </div>
        <div class="details-box">
            <h4>📋 Your Interview Summary:</h4>
            <ul>
            <li><strong>Status:</strong> {application_status or 'N/A'}</li>
            <li><strong>Score:</strong> {score if score is not None else 'N/A'}</li>
            <li><strong>Interview Date:</strong> {interview_date or 'N/A'}</li>
            <li><strong>Department:</strong> {department or 'N/A'}</li>
            </ul>
        </div>
        {"<p>We're excited to move forward! Please click the button below to complete your registration and join the team:</p>" if registration_link else ""}
        {f'<a href="{registration_link}" class="button">Complete Registration</a>' if registration_link else ""}
        <p>If you have any questions, feel free to reach out to our team.</p>
        </div>
        <div class="footer">
        <p>Best regards,<br>{organization_name} Team</p>
        <p>Powered by HireIn</p>
        </div>
    </div>
    </body>
    </html>
    """
        return self.send_email(email, subject, body, html_body)

    def send_calendar_invite(self,
        to_email: str,
        subject: str,
        start_time: datetime,
        end_time: datetime,
        description: str,
        location: Optional[str] = None
    ) -> bool:
        """Send simplified calendar invitation via email"""
        body = f"""
Calendar Invitation: {subject}

Start Time: {start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}
End Time: {end_time.strftime('%Y-%m-%d %H:%M:%S UTC')}
{f'Location: {location}' if location else ''}

Description:
{description}
"""
        return self.send_email(to_email, f"Calendar Invite: {subject}", body)

# ✅ Global instance
email_service = EmailService()
