import os
import time
import json
import subprocess
import pandas as pd
from fpdf import FPDF
from pydantic import BaseModel, ValidationError
import dotenv
import logging
dotenv.load_dotenv()

from transformations.llm_transformation import MultiLLMTransformation

# Advanced resume generation imports
try:
    from langchain_openai.embeddings import OpenAIEmbeddings
except ImportError:
    from langchain.embeddings import OpenAIEmbeddings
try:
    from langchain_community.vectorstores import FAISS
except ImportError:
    from langchain.vectorstores import FAISS
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

# Allowed resume section types
ALLOWED_TYPES = [
    'summary', 'profile', 'work', 'volunteer', 'education', 'awards',
    'certificates', 'publications', 'skills', 'languages', 'interests',
    'references', 'projects'
]

# Pydantic model for resume section
class ResumeSection(BaseModel):
    section: str
    text: str
    details: dict

def resume_to_objects(resume: dict) -> list:
    logger.debug("Converting resume dictionary to ResumeSection objects")
    result = []
    if 'basics' in resume and 'summary' in resume['basics']:
        result.append(ResumeSection(section='summary', text=resume['basics'].get('summary', ''), details=resume['basics']))
    if 'basics' in resume and 'profiles' in resume['basics']:
        for profile in resume['basics'].get('profiles', []):
            network = profile.get('network', '')
            url = profile.get('url', '')
            if network and url:
                result.append(ResumeSection(section='profile', text=f"{network}: {url}", details=profile))
    for section in ['work', 'volunteer', 'education', 'awards', 'certificates', 'publications', 'skills', 'languages', 'interests', 'references', 'projects']:
        if section in resume:
            for item in resume.get(section, []):
                text = ""
                details = item
                if section in ['work', 'volunteer', 'projects']:
                    position = item.get('position', '')
                    name = item.get('name', '')
                    startDate = item.get('startDate', '')
                    endDate = item.get('endDate', '')
                    summary = item.get('summary', '')
                    text = f"{position} at {name} ({startDate} - {endDate}) - {summary}"
                    for highlight in item.get('highlights', []):
                        text += f"\nHighlight: {highlight}"
                elif section == 'education':
                    studyType = item.get('studyType', '')
                    area = item.get('area', '')
                    institution = item.get('institution', '')
                    startDate = item.get('startDate', '')
                    endDate = item.get('endDate', '')
                    score = item.get('score', '')
                    text = f"{studyType} in {area} from {institution} ({startDate} - {endDate}) - Score: {score}"
                    for course in item.get('courses', []):
                        text += f"\nCourse: {course}"
                elif section in ['awards', 'certificates', 'publications']:
                    name = item.get('name', '')
                    date = item.get('date', '')
                    issuer_or_awarder = item.get('issuer', item.get('awarder', ''))
                    summary = item.get('summary', '')
                    text = f"{name} ({date}) by {issuer_or_awarder} - {summary}"
                elif section == 'skills':
                    name = item.get('name', '')
                    level = item.get('level', '')
                    keywords = ', '.join(item.get('keywords', []))
                    text = f"{name} ({level}) - Keywords: {keywords}"
                elif section == 'languages':
                    language = item.get('language', '')
                    fluency = item.get('fluency', '')
                    text = f"{language} ({fluency})"
                elif section == 'interests':
                    name = item.get('name', '')
                    keywords = ', '.join(item.get('keywords', []))
                    text = f"{name} - Keywords: {keywords}"
                elif section == 'references':
                    name = item.get('name', '')
                    reference = item.get('reference', '')
                    text = f"{name} - {reference}"
                result.append(ResumeSection(section=section, text=text, details=details))
    logger.debug(f"Created {len(result)} ResumeSection objects")
    return result

def verify_resume_json(resume_json):
    logger.debug("Verifying and adjusting resume JSON format")
    def highlights_included(resume_json):
        for section in ['work', 'volunteer', 'projects']:
            for item in resume_json.get(section, []):
                highlights = item.get('highlights', [])
                if len(highlights) < 2:
                    item['highlights'] = item.get('summary', '').split('. ')
        return resume_json
    def highlights_terminated(resume_json):
        for section in ['work', 'volunteer', 'projects']:
            for item in resume_json.get(section, []):
                highlights = item.get('highlights', [])
                if highlights and not highlights[-1].endswith('.'):
                    highlights[-1] += '.'
        return resume_json
    logger.debug("Resume JSON verification complete")
    return highlights_terminated(highlights_included(resume_json))

# New Pydantic model for full resume JSON validation.
class ResumeModel(BaseModel):
    basics: dict
    work: list = []
    volunteer: list = []
    education: list = []
    awards: list = []
    certificates: list = []
    publications: list = []
    skills: list = []
    languages: list = []
    interests: list = []
    references: list = []
    projects: list = []

class MakeResumeTransformation(MultiLLMTransformation):
    name = "Make Resume Transformation"
    description = "Generates a comprehensive resume PDF tailored for a job application by combining personal resume data with job description analysis."
    predefined_output = True
    def required_inputs(self):
        # Require the Job_Description column.
        return ["Job_Description"]

    def required_static_params(self):
        base_params = super().required_static_params()  # e.g. system_prompt, user_prompt, provider, model, api_key, etc.
        additional_params = [
            {
                "name": "pdf_output_dir",
                "type": "text",
                "description": "Directory path where generated resume PDF will be saved.",
                "default": os.getcwd()
            },
            {
                "name": "open_file_command",
                "type": "text",
                "description": "Command to open the generated PDF file (e.g. 'open {file}' on macOS or 'start {file}' on Windows).",
                "default": "open {file}" if os.name == "posix" else "start {file}"
            }
        ]
        return base_params + additional_params

    def transform(self, df, output_col_name, *args, **kwargs):
        # Verify Node.js environment first
        self._verify_node_environment()
        
        # Get required parameters from kwargs instead of positionals
        system_prompt = kwargs.get("system_prompt", "")
        user_prompt = kwargs.get("user_prompt", "")
        extra_placeholders = kwargs.get("extra_placeholders", None)
        json_mode = kwargs.get("json_mode", False)
        
        if extra_placeholders is None:
            extra_placeholders = {}
            
        placeholder_wrapper = self.get_placeholder_wrapper(extra_placeholders)
        
        provider = kwargs.get("provider", "OpenAI").strip().lower()
        model_name = kwargs.get("model", "gpt-4o-mini").strip()
        pdf_output_dir = kwargs.get("pdf_output_dir", os.getcwd())
        open_file_command = kwargs.get("open_file_command", "open {file}")
        
        os.makedirs(pdf_output_dir, exist_ok=True)
        
        for idx, row in df.iterrows():
            try:
                job_desc = str(row.get("Job_Description", "")).strip()
                if not job_desc:
                    continue
                
                # Step 1: Summarize job description
                summarized_job = self._summarize_job_description(job_desc, provider, model_name)
                
                # Step 2: Get resume JSON (will convert from text if needed)
                from services.settings_service import get_resume_json
                resume_json = get_resume_json()
                if not resume_json:
                    raise ValueError("Could not load or generate resume JSON")
                
                # Validate resume JSON using Pydantic.
                try:
                    ResumeModel.model_validate(resume_json)
                except ValidationError as ve:
                    # If invalid, attempt conversion from resume text.
                    resume_text = self._load_user_resume()
                    resume_json_str = self._convert_resume_text_to_json(resume_text, provider, model_name)
                    try:
                        validated_resume = ResumeModel.model_validate_json(resume_json_str)
                        resume_json = validated_resume.model_dump()
                    except ValidationError as ve2:
                        raise ValueError(f"Resume JSON validation error after conversion: {ve2}")
                
                # Step 3: Verify and adjust resume JSON.
                resume_json = verify_resume_json(resume_json)
                
                # Step 4: Embed resume sections into a vector store.
                vectorstore = self._embed_resume(resume_json)
                
                # Step 5: Retrieve top 5 matching sections per allowed type based on job description.
                targeted_sections = self._get_target_resume_sections(vectorstore, summarized_job)
                
                # Step 6: Build final resume text from targeted sections.
                final_resume_text = self._build_final_resume_text(targeted_sections)
                
                # Generate PDF filename
                first_name = resume_json['basics'].get('firstName', '')
                last_name = resume_json['basics'].get('lastName', '')
                job_position = resume_json['basics'].get('label', 'Resume')
                company_name = row.get("Company", "Company")  # Assuming Company column exists
                
                # Create sanitized filename
                file_base = f"{first_name}_{last_name}_resume_for_{job_position}_at_{company_name}".replace(" ", "_")
                pdf_filename = f"{file_base}.pdf"
                pdf_path = os.path.join(pdf_output_dir, pdf_filename)
                
                # Save temporary JSON file
                temp_json = os.path.join(pdf_output_dir, f"temp_{int(time.time())}.json")
                with open(temp_json, 'w') as f:
                    json.dump(resume_json, f)
                
                # Generate PDF using resume-cli
                subprocess.run(
                    [
                        'resume', 'export', pdf_path,
                        '--resume', temp_json,
                        '--theme', 'even',
                        '--format', 'pdf'
                    ],
                    check=True
                )
                
                # Clean up temporary JSON
                os.remove(temp_json)
                
                df.at[idx, output_col_name] = pdf_path
                
            except Exception as e:
                df.at[idx, output_col_name] = f"ERROR: {str(e)}"
        return df

    def _verify_node_environment(self):
        """Verify Node.js and required packages are installed"""
        logger.debug("Verifying Node.js environment")
        
        try:
            # Check Node.js exists
            try:
                if os.name == 'nt':  # Windows
                    subprocess.run(['where', 'node'], check=True, capture_output=True, shell=True)
                    subprocess.run(['where', 'npm'], check=True, capture_output=True, shell=True)
                else:  # Linux/Mac
                    subprocess.run(['which', 'node'], check=True, capture_output=True)
                    subprocess.run(['which', 'npm'], check=True, capture_output=True)
            except subprocess.CalledProcessError:
                raise RuntimeError(
                    "Node.js not found in PATH.\n"
                    "1. Install Node.js from https://nodejs.org\n"
                    "2. Restart your terminal/application after installation\n"
                    "3. Verify with: node --version"
                )

            # Check global packages
            packages = subprocess.run(
                ['npm', 'list', '-g', 'resume-cli', 'jsonresume-theme-even', '--parseable'],
                capture_output=True,
                text=True,
                shell=True if os.name == 'nt' else False
            )
            
            # Verify required packages
            missing = []
            if 'resume-cli' not in packages.stdout:
                missing.append('resume-cli')
            if 'jsonresume-theme-even' not in packages.stdout:
                missing.append('jsonresume-theme-even')
            
            if missing:
                logger.info(f"Installing missing packages: {', '.join(missing)}")
                subprocess.run(
                    ['npm', 'install', '-g'] + missing,
                    check=True,
                    shell=True if os.name == 'nt' else False
                )
            
        except subprocess.CalledProcessError as e:
            error_msg = (
                "Failed to verify Node.js environment:\n"
                f"Command: {e.cmd}\n"
                f"Error: {e.stderr.decode().strip()}"
            )
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def _summarize_job_description(self, job_description, provider, model_name):
        logger.debug(f"Summarizing job description using {provider} {model_name}")
        prompt_template = (
            "Summarize this job description focusing on responsibilities, skills, and requirements. "
            "Keep it under 100 words.\n"
            "----JOB DESCRIPTION----\n{job_description}\n-----------------------\n"
            "RESPONSE:"
        )
        summary = self._call_llm(provider, model_name, "", prompt_template.format(job_description=job_description))
        logger.debug("Job description summary complete")
        return summary.strip()

    def _load_user_resume(self):
        logger.debug("Loading user resume from file")
        if os.path.exists("user_resume.txt"):
            with open("user_resume.txt", "r", encoding="utf-8") as f:
                return f.read()
        logger.debug("User resume loaded successfully" if os.path.exists("user_resume.txt") else "No user resume file found")
        return ""

    def _convert_resume_text_to_json(self, resume_text, provider, model_name):
        logger.debug(f"Converting resume text to JSON using {provider} {model_name}")
        if not os.path.exists("resumeJSONSchema.json"):
            raise FileNotFoundError("resumeJSONSchema.json not found.")
        with open("resumeJSONSchema.json", "r", encoding="utf-8") as f:
            resume_format = f.read()
        
        prompt_template = (
            "Convert this text extracted from my resume to resumeJSON.\n"
            "----MY RESUME TEXT----\n{resume_text}\n----------------------\n"
            "Respond with it in the following JSON format:\n"
            "----RESUME JSON FORMAT----\n{resume_format}\n--------------------------\n"
            "Rules:\n"
            "1. If there is no information matching the field or it's not in the right format (e.g. date in YYYY-MM-DD), don't include the field.\n"
            "2. You MUST respond with the entire field's text if it is in the right format.\n"
            "Respond with just the JSON.\n"
            "RESPONSE:"
        )
        prompt = prompt_template.format(resume_text=resume_text, resume_format=resume_format)
        resume_json_str = self._call_llm(provider, model_name, "", prompt)
        # Validate the LLM output using Pydantic.
        try:
            ResumeModel.model_validate_json(resume_json_str)
            logger.debug("Resume text conversion to JSON complete")
            return resume_json_str.strip()
        except ValidationError as ve:
            raise ValueError("LLM output did not validate against the resume schema: " + str(ve))

    def _embed_resume(self, resume_json):
        logger.debug("Creating embeddings for resume sections")
        sections = resume_to_objects(resume_json)
        docs = []
        for obj in sections:
            docs.append(Document(page_content=obj.text, metadata={"type": obj.section, "details": obj.details}))
        embeddings = OpenAIEmbeddings()
        vectorstore = FAISS.from_documents(docs, embeddings)
        logger.debug(f"Created embeddings for {len(docs)} resume sections")
        return vectorstore

    def _get_target_resume_sections(self, vectorstore, job_description):
        logger.debug("Retrieving targeted resume sections based on job description")
        retriever = vectorstore.as_retriever(search_kwargs={"k": 1000})
        results = retriever.get_relevant_documents(job_description)
        targeted = {}
        for t in ALLOWED_TYPES:
            targeted[t] = []
            count = 0
            for doc in results:
                if doc.metadata.get("type") == t:
                    targeted[t].append(doc.metadata.get("details"))
                    count += 1
                if count == 5:
                    break
        logger.debug(f"Retrieved sections for {len(targeted)} categories")
        return targeted

    def _build_final_resume_text(self, targeted_sections):
        logger.debug("Building final resume text from targeted sections")
        final_text = ""
        for section, items in targeted_sections.items():
            if items:
                final_text += section.upper() + ":\n"
                for item in items:
                    final_text += "- " + json.dumps(item) + "\n"
                final_text += "\n"
        logger.debug("Final resume text assembly complete")
        return final_text.strip()