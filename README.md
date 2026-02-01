# 🎧 Multilingual Audio Pipeline  
**Teaching the Cloud to Speak Every Language**

Automating transcription, translation, and speech synthesis using AWS AI services and GitHub Actions.

---

## 📌 Overview

Pixel Learning Co. is a digital-first education startup focused on accessibility and global learning.  
As the platform grew, instructors began uploading audio-based lessons, but supporting international learners required a scalable way to localize spoken content.

This project demonstrates a fully automated CI/CD pipeline that:

- Transcribes English audio into text
- Translates the transcript into other languages
- Converts translated text back into natural-sounding speech
- Stores all artifacts in structured Amazon S3 folders
- Runs automatically through GitHub Actions

All triggered by simply adding an `.mp3` file to the repository.

---

## 🧠 What This Pipeline Does

1. Detects `.mp3` audio files added to the repository  
2. Uploads audio files to Amazon S3  
3. Uses Amazon Transcribe to convert speech to text  
4. Uses Amazon Translate to translate transcripts into target languages  
5. Uses Amazon Polly to synthesize translated speech  
6. Uploads transcripts, translations, and audio outputs back to S3  
7. Separates outputs by environment (`beta` or `prod`) based on workflow trigger  

---

## 🛠️ Technologies Used

- Amazon Transcribe – Speech-to-text  
- Amazon Translate – Language translation  
- Amazon Polly – Text-to-speech  
- Amazon S3 – Artifact storage  
- GitHub Actions – CI/CD automation  
- Python (boto3) – AWS service orchestration  

---

## 📁 Repository Structure

    .
    ├── audio_inputs/
    ├── scripts/
    │   └── process_audio.py
    ├── .github/
    │   └── workflows/
    │       ├── on_pull_request.yml
    │       └── on_merge.yml
    └── README.md

---

## ☁️ S3 Folder Structure

    s3://your-bucket/
    ├── beta/
    │   ├── transcripts/
    │   ├── translations/
    │   └── audio_outputs/
    └── prod/
        ├── transcripts/
        ├── translations/
        └── audio_outputs/

---

## 📄 Example S3 Paths

    beta/transcripts/lesson1.txt
    beta/translations/lesson1_es.txt
    prod/audio_outputs/lesson1_es.mp3

---

## 🔁 CI/CD Workflows

### Pull Request Workflow (`on_pull_request.yml`)

Triggered when a pull request targets `main`.

- Executes the audio processing script  
- Uploads results to the `beta/` S3 prefix  

### Merge Workflow (`on_merge.yml`)

Triggered on push events to the `main` branch.

- Executes the audio processing script  
- Uploads results to the `prod/` S3 prefix  

---

## 🔐 GitHub Secrets Configuration

    AWS_ACCESS_KEY_ID
    AWS_SECRET_ACCESS_KEY
    AWS_REGION
    S3_BUCKET

Credentials are never hardcoded in scripts or workflows.

---

## ▶️ How to Use This Project

1. Add one or more `.mp3` files to the `audio_inputs/` folder  
2. Commit and push changes to a feature branch  
3. Open a pull request targeting `main`  
4. Review outputs uploaded to the `beta/` folder in S3  
5. Merge the pull request  
6. Confirm final outputs in the `prod/` folder in S3  

---

## ✅ How to Verify Results

After the workflow completes, confirm the following in your S3 bucket:

- Transcript `.txt` file  
- Translated text file (e.g., `_es`, `_fr`)  
- Generated `.mp3` audio file for each language  

---

## ✨ Why This Project Matters

This pipeline demonstrates how fully managed AWS AI services can be integrated into modern DevOps workflows to:

- Improve accessibility  
- Eliminate manual localization steps  
- Scale global content delivery  
- Maintain a serverless, low-maintenance architecture  
 
