from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
import os
from dotenv import load_dotenv
import google.generativeai as genai
from io import BytesIO
import PyPDF2
from docx import Document
from typing import List

app = FastAPI()

# Load environment variables
load_dotenv()

# Fetch the API key from the environment variables
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

# Configure the Google Generative AI model
genai.configure(api_key=GOOGLE_API_KEY)

# Initialize the model
model = genai.GenerativeModel('gemini-1.5-flash')

# Extract text from files
def extract_text(file_content, file_type):
    content = ""

    if file_type == "application/pdf":
        pdf_reader = PyPDF2.PdfReader(BytesIO(file_content))
        for page in pdf_reader.pages:
            content += page.extract_text()

    elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        doc = Document(BytesIO(file_content))
        for paragraph in doc.paragraphs:
            content += paragraph.text + "\n"
    
    return content

# Route to upload and process resumes
@app.post("/analyze-resumes")
async def analyze_resumes(
    role: str = Form(...), 
    skills: str = Form(...), 
    experience: int = Form(...), 
    uploaded_files: List[UploadFile] = File(...)
):
    prompts = []
    for uploaded_file in uploaded_files:
        resume_text = extract_text(await uploaded_file.read(), uploaded_file.content_type)

        instruction = (
            "Evaluate each resume to determine if the candidate meets the specified role requirements, skills, and working experience."
            "If all criteria are met, provide a brief report containing only the candidate's name and mobile number"
            "Ensure the evaluation is consistent and deterministic, such that the same resume always yields the same result without any changes. Do not include any additional information."
            "If any requirement specified by the user is not fulfilled, do not include that resume in the report Check in Role for every resume if role is not match so do not include that resume. You need most focus on role Do not include any additional information."
            "Focus on the role specified by the user, and if the role does not match, do not include that resume in the report. Do not include any additional information."
)

        prompt = (
            f"Position or Role: {role}\n"
            f"Required Skills: {skills}\n"
            f"Minimum Working Experience: {experience} years\n"
            f"Resume Content: {resume_text}\n"
            f"{instruction}"
        )
        prompts.append(prompt)

    responses = []
    for prompt in prompts:
        response = model.generate_content(prompt)
        responses.append(response.text)

    return JSONResponse(content={"results": responses})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

