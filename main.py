from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
import os
from dotenv import load_dotenv
import google.generativeai as genai
from io import BytesIO
import PyPDF2
from fastapi.middleware.cors import CORSMiddleware
from docx import Document
from typing import List
import uvicorn

app = FastAPI()
# Configure CORS
origins = [
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins = ["*"],
    allow_credentials=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/")
async def rootMsg():
    return "API IS RUNNING PERFECTLY"

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
    if len(uploaded_files) > 10:
        raise HTTPException(status_code=400, detail="You can upload up to 10 files at a time.")

    for uploaded_file in uploaded_files:
        if uploaded_file.content_type not in ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
            raise HTTPException(status_code=400, detail="Only PDF and DOCX files are allowed.")
    prompts = []
    for uploaded_file in uploaded_files:
        resume_text = extract_text(await uploaded_file.read(), uploaded_file.content_type)

        instruction = (
            "Evaluate each resume to determine if the candidate meets the specified role requirements, skills, and working experience."
            "If all criteria are met, provide a brief report containing only the candidate's name, mobile number and Email"
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

@app.post("/pre-analyze-validate")
async def analyze_resumes(
    role: str = Form(...), 
    skills: str = Form(...), 
    experience: int = Form(...)
):
    prompt = (
        f"`Role: {role}`, `Experience: {experience} years`, and `Skill: {skills}` are these all relevant to actual human skills and professions, or do they not match each other? Answer either clear `YES` or `NO`."
    )
    responses_2 = []
    response = model.generate_content(prompt)
    responses_2.append(response.text)
    return JSONResponse(content={"result": responses_2})


# Route to upload and process resumes
@app.post("/analyze-resumes-v2")
async def analyze_resumesV2(
    role: str = Form(...), 
    skills: str = Form(...), 
    experience: int = Form(...), 
    uploaded_files: List[UploadFile] = File(...)
):
    main_prompt = ""
    
    for index, uploaded_file in enumerate(uploaded_files):
        resume_text = extract_text(await uploaded_file.read(), uploaded_file.content_type)
        main_prompt += f"~! Resume #{index}"
        main_prompt += resume_text
        main_prompt += "\n\n"

    main_prompt += f"\n\n Evaluate each resume to determine if the candidate meets the specified role requirements, skills, and working experience. Rank down all resumes that match the criteria and exclude the ones that do not match. Then, return an array of objects containing the candidate's Name, Phone, and Email. Focus mostly on the role and ensure that the evaluation is consistent and deterministic, meaning the same resume always yields the same result without any changes. Do not include any additional information. The role should be `{role}`, the years of experience should be equal to or greater than `{experience}` and the skills should match `{skills}`"
    main_prompt += f"\n Remember to return a JSON array of objects containing the candidate's Name, Phone, and Email."

    responses_3 = []
    response = model.generate_content(main_prompt)
    responses_3.append(response.text)

    return JSONResponse(content={"results": responses_3})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

