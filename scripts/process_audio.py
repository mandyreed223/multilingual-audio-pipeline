#!/usr/bin/env python3
"""
Multilingual Audio Pipeline
- Upload .mp3 to S3
- Transcribe -> transcript text
- Translate -> translated text (one or many languages)
- Polly -> synthesized speech audio
- Upload artifacts to structured S3 prefixes (beta/ or prod/)

Required environment variables (set via GitHub Actions Secrets):
- AWS_REGION
- S3_BUCKET

Optional environment variables:
- ENV_PREFIX           (default: "beta")  # set to "prod" on merge workflow
- INPUT_DIR            (default: "audio_inputs")
- TARGET_LANGUAGES     (default: "es,fr") # comma-separated, e.g. "es,fr,de"
- TRANSCRIBE_LANGUAGE  (default: "en-US")
- POLLY_ENGINE         (default: "neural") # fallback to "standard" if neural fails
"""

import json
import os
import time
import uuid
from pathlib import Path
from typing import Dict, List, Tuple

import boto3
from botocore.exceptions import ClientError


def get_env(name: str, default: str = "") -> str:
    # Read environment variable with optional default
    value = os.getenv(name, default)
    # Normalize whitespace
    return value.strip() if isinstance(value, str) else value


def split_languages(csv_value: str) -> List[str]:
    # Split comma-separated language list into clean codes
    langs = []
    for part in csv_value.split(","):
        code = part.strip()
        if code:
            langs.append(code)
    return langs


def build_s3_key(env_prefix: str, folder: str, filename: str) -> str:
    # Build S3 key like: beta/transcripts/file.txt
    return f"{env_prefix}/{folder}/{filename}"


def upload_file_to_s3(s3_client, bucket: str, local_path: Path, s3_key: str) -> None:
    # Upload file to S3
    s3_client.upload_file(str(local_path), bucket, s3_key)


def put_text_to_s3(s3_client, bucket: str, s3_key: str, text: str) -> None:
    # Upload text as an S3 object
    s3_client.put_object(
        Bucket=bucket,
        Key=s3_key,
        Body=text.encode("utf-8"),
        ContentType="text/plain; charset=utf-8",
    )


def get_json_from_s3(s3_client, bucket: str, s3_key: str) -> Dict:
    # Read JSON from S3 and parse it
    response = s3_client.get_object(Bucket=bucket, Key=s3_key)
    body = response["Body"].read().decode("utf-8")
    return json.loads(body)


def start_transcribe_job(
    transcribe_client,
    job_name: str,
    media_uri: str,
    language_code: str,
    output_bucket: str,
    output_key: str,
) -> None:
    # Start Transcribe job and save output JSON to S3
    transcribe_client.start_transcription_job(
        TranscriptionJobName=job_name,
        LanguageCode=language_code,
        Media={"MediaFileUri": media_uri},
        OutputBucketName=output_bucket,
        OutputKey=output_key,
    )


def wait_for_transcribe_job(transcribe_client, job_name: str, timeout_seconds: int = 900) -> str:
    # Poll Transcribe until complete/fail or timeout
    start = time.time()

    while True:
        response = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
        status = response["TranscriptionJob"]["TranscriptionJobStatus"]

        if status in ("COMPLETED", "FAILED"):
            return status

        if time.time() - start > timeout_seconds:
            raise TimeoutError(f"Transcribe job timed out after {timeout_seconds}s: {job_name}")

        time.sleep(5)


def extract_transcript_text(transcribe_output_json: Dict) -> str:
    # Extract transcript text from Transcribe JSON output
    # The main transcript is typically stored in results.transcripts[0].transcript
    results = transcribe_output_json.get("results", {})
    transcripts = results.get("transcripts", [])

    if not transcripts:
        raise ValueError("No transcripts found in Transcribe output JSON.")

    transcript_text = transcripts[0].get("transcript", "")
    if not transcript_text.strip():
        raise ValueError("Transcript text was empty in Transcribe output JSON.")

    return transcript_text.strip()


def translate_text(translate_client, text: str, source_lang: str, target_lang: str) -> str:
    # Translate text using Amazon Translate
    response = translate_client.translate_text(
        Text=text,
        SourceLanguageCode=source_lang,
        TargetLanguageCode=target_lang,
    )
    return response["TranslatedText"]


def get_voice_map() -> Dict[str, str]:
    """
    Simple default voice mapping.
    You can expand this list as you add more languages.

    Note:
    - Polly voices can vary by region and availability.
    - If a language isn't mapped, the script will raise a clear error so you can add it.
    """
    return {
        # Spanish
        "es": "Lupe",
        # French
        "fr": "Lea",
        # German (example)
        "de": "Vicki",
        # Italian (example)
        "it": "Bianca",
        # Portuguese (example)
        "pt": "Camila",
    }


def synthesize_speech(
    polly_client,
    text: str,
    voice_id: str,
    engine_preference: str = "neural",
    output_format: str = "mp3",
) -> bytes:
    # Try preferred engine first (often "neural"), then fallback to "standard"
    engines_to_try = [engine_preference, "standard"] if engine_preference != "standard" else ["standard"]

    last_error = None
    for engine in engines_to_try:
        try:
            # Request speech synthesis from Polly
            response = polly_client.synthesize_speech(
                Text=text,
                VoiceId=voice_id,
                OutputFormat=output_format,
                Engine=engine,
            )

            audio_stream = response.get("AudioStream")
            if not audio_stream:
                raise ValueError("Polly response did not include an AudioStream.")

            return audio_stream.read()

        except ClientError as e:
            last_error = e

    raise RuntimeError(f"Polly synthesis failed for voice '{voice_id}'. Last error: {last_error}")


def process_one_audio_file(
    s3_client,
    transcribe_client,
    translate_client,
    polly_client,
    bucket: str,
    env_prefix: str,
    audio_path: Path,
    transcribe_language: str,
    target_languages: List[str],
    polly_engine: str,
) -> None:
    # Determine base filename without extension
    base_name = audio_path.stem

    # Upload input audio to S3
    input_key = build_s3_key(env_prefix, "audio_inputs", audio_path.name)
    upload_file_to_s3(s3_client, bucket, audio_path, input_key)

    # Create a unique Transcribe job name
    job_name = f"{env_prefix}-{base_name}-{uuid.uuid4().hex[:10]}"

    # Set Transcribe output location (JSON)
    transcribe_output_key = build_s3_key(env_prefix, "transcribe_jobs", f"{job_name}.json")

    # Media URI for Transcribe (S3 URI)
    media_uri = f"s3://{bucket}/{input_key}"

    # Start the Transcribe job
    start_transcribe_job(
        transcribe_client=transcribe_client,
        job_name=job_name,
        media_uri=media_uri,
        language_code=transcribe_language,
        output_bucket=bucket,
        output_key=transcribe_output_key,
    )

    # Wait for completion
    status = wait_for_transcribe_job(transcribe_client, job_name)
    if status != "COMPLETED":
        raise RuntimeError(f"Transcribe job failed: {job_name}")

    # Read the Transcribe output JSON from S3
    transcribe_json = get_json_from_s3(s3_client, bucket, transcribe_output_key)

    # Extract transcript text
    transcript_text = extract_transcript_text(transcribe_json)

    # Upload transcript as a .txt file
    transcript_key = build_s3_key(env_prefix, "transcripts", f"{base_name}.txt")
    put_text_to_s3(s3_client, bucket, transcript_key, transcript_text)

    # Translate + synthesize for each language
    voice_map = get_voice_map()

    for lang in target_languages:
