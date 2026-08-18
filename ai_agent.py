import os
import json
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load environment variables
load_dotenv()


from typing import Optional

class EmailDraft(BaseModel):
    """
    Structured Pydantic data model representing the generated email components, detected intent, and recipient context.
    """
    detected_intent: str = Field(
        description="A concise 2-4 word classification of the primary communication intent (e.g., 'Certificate & Congratulations', 'Invoice & Payment Request', 'Meeting Scheduling', 'Project Report Submission', 'Job Application', 'General Inquiry', 'Formal Complaint', 'Resignation Notice', 'Follow-up / Reminder')."
    )
    recipient_email: Optional[str] = Field(
        default=None,
        description="Extracted target email address if explicitly mentioned in the brief (e.g., 'user@example.com'). Return null if no email address is present."
    )
    recipient_name_or_role: Optional[str] = Field(
        default=None,
        description="Extracted recipient person's name, team, or professional role mentioned in the brief (e.g., 'Sarah Jenkins', 'Finance Department', 'Project Manager'). Return null if not specified."
    )
    subject: str = Field(description="A concise, high-impact, professional subject line for the email.")
    body: str = Field(description="The complete formal body content of the email, structured professionally with formal greetings, body context, call-to-action, and sign-off.")


def draft_email(brief: str) -> EmailDraft:
    """
    Invokes the Gemini API using google-genai SDK to transform any informal, vague, or rough WhatsApp brief
    into a structured formal email draft adhering to the EmailDraft Pydantic model.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not configured in .env file.")

    client = genai.Client(api_key=api_key)

    system_instruction = (
        "You are an elite executive communication AI assistant and expert context analyst. Your task is to analyze user briefs, "
        "informal notes, voice transcripts, or rough WhatsApp messages—which may be vague, ungrammatical, fragment line, or brief—"
        "and intelligently deduce the user's underlying core intent, target recipient, context, and purpose across ALL types of communication.\n\n"
        "Universal Intent & Recipient Analysis Framework:\n"
        "1. DEDUCE INTENT & PURPOSE:\n"
        "   - Congratulatory & Celebratory: (e.g., certificates, awards, milestones, promotions)\n"
        "   - Business & Financial: (e.g., invoices, receipts, payment notices, quote requests, purchase orders, budget reports)\n"
        "   - Scheduling & Meetings: (e.g., appointment requests, interview invitations, meeting rescheduling, calendar invites)\n"
        "   - Formal Submissions & Deliverables: (e.g., project status, task completion, document submissions, assignment turn-ins)\n"
        "   - Support & Escalations: (e.g., issue reports, formal complaints, refund requests, client feedback)\n"
        "   - Inquiries & Networking: (e.g., business proposals, partnership inquiries, recommendations, info requests)\n"
        "   - Employment & HR: (e.g., job applications, resumes, leave requests, resignations, offers)\n"
        "2. RECIPIENT AUDIT & EXTRACTION:\n"
        "   - Actively analyze WHO this email is intended for!\n"
        "   - Extract any specific email address (e.g., 'user@domain.com') into 'recipient_email'.\n"
        "   - Extract any recipient person's name, department, or job title (e.g., 'Sarah', 'Finance Team', 'Hiring Manager') into 'recipient_name_or_role'.\n"
        "   - Tailor the email greeting directly to this recipient (e.g., 'Dear Sarah,', 'Dear Finance Team,').\n"
        "3. CATEGORIZATION:\n"
        "   - Set 'detected_intent' to a clear 2-4 word category label representing what the user is trying to accomplish.\n"
        "4. HIGH-IMPACT SUBJECT & BODY:\n"
        "   - Craft a crisp, professional, context-aware subject line.\n"
        "   - Compose a well-structured email body with appropriate tone (warm for celebrations, professional for business, polite for complaints/inquiries).\n"
        "5. DOCUMENT-ONLY & FILE TITLE ANALYSIS:\n"
        "   - When an attached document file title or filename is provided (e.g., 'Certificate _ SOLID Principles Every Developer Must Know.PDF', 'Invoice_1042_AcmeCorp.pdf', 'Resume_John_Doe.pdf', 'Q3_Financial_Report.xlsx'):\n"
        "   - Deeply analyze the file title to determine the specific document category, topic, course name, invoice number, or project title.\n"
        "   - For Certificates/Awards: Frame a warm congratulatory email presenting the certificate for that specific course/achievement.\n"
        "   - For Invoices/Bills: Frame a formal payment submission email referencing the invoice number and organization.\n"
        "   - For Resumes/Applications: Frame a formal job application submission email.\n"
        "   - For Reports/Deliverables: Frame a formal executive summary submission email.\n"
        "   - NEVER output generic subjects like 'Forwarded Document Attachment for Review' when the file title provides specific context!\n\n"
        "6. DYNAMIC SUBJECT REVISION & FORWARDING RULE:\n"
        "   - Even if the user says 'Forward this above document' or 'in previous document update the subject':\n"
        "   - NEVER generate generic subjects like 'Document Submission for Your Review' or 'Updated Submission: Revised Subject Line'.\n"
        "   - ALWAYS extract the exact topic/title from the attached file name (e.g. 'Certificate of Completion: SOLID Principles Every Developer Must Know' or 'Forwarding Certificate: SOLID Principles Every Developer Must Know').\n"
        "   - If the user asks to update or improve the subject line, synthesize a superior, highly specific, professional subject line reflecting the actual document content and recipient context.\n\n"
        "7. NO BRACKET PLACEHOLDERS RULE (STRICT MANDATE):\n"
        "   - NEVER output literal bracket placeholders like '[Recipient Name]', '[Your Name]', '[Insert Name]', '[Sender]', '[Company Name]', or '[Recipient]' in the email body or subject line!\n"
        "   - If recipient's name is known (e.g. 'Sarah', 'Alex'), address them directly ('Dear Sarah,', 'Dear Alex,').\n"
        "   - If recipient's role is known (e.g. 'Hiring Manager', 'Finance Team'), address them directly ('Dear Hiring Manager,', 'Dear Finance Team,').\n"
        "   - If no specific recipient name is provided, start directly with 'Greetings,', 'Dear Sir/Madam,', or 'Hello,'.\n"
        "   - For the sign-off, use 'Best regards,' or 'Sincerely,' cleanly without generic bracket text like '[Your Name]'."
    )

    models_to_try = ["gemini-3.5-flash", "gemini-3.6-flash", "gemini-flash-latest", "gemini-3.1-flash-lite"]
    last_err = None

    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=f"Please draft a formal email based on the following brief:\n\n{brief}",
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=EmailDraft,
                    system_instruction=system_instruction,
                    temperature=0.3
                )
            )
            data = json.loads(response.text)
            return EmailDraft(**data)
        except Exception as err:
            last_err = err
            continue

    raise RuntimeError(f"Failed to generate email draft via Gemini API: {last_err}")


if __name__ == "__main__":
    # Quick standalone testing snippet
    sample_brief = "Hey John, tell him the quarterly budget report is ready and attached. Ask him to review by Friday."
    print("Testing AI Email Drafter...")
    try:
        email = draft_email(sample_brief)
        print(f"Subject: {email.subject}")
        print(f"Body:\n{email.body}")
    except Exception as err:
        print(f"Error during draft generation: {err}")

