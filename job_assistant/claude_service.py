import json
import os

import anthropic
from dotenv import load_dotenv

from job_assistant.prompts import (
    ATS_SCORE_INSTRUCTION,
    COVER_LETTER_INSTRUCTION,
    SYSTEM_PROMPT,
    TAILOR_INSTRUCTION,
)

load_dotenv()


class ClaudeService:
    def __init__(self, verbose: bool = False):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "ANTHROPIC_API_KEY not set. Copy .env.example to .env and add your key."
            )
        self.client = anthropic.Anthropic(api_key=api_key)
        self.verbose = verbose

    def _call(self, resume_text: str, jd_text: str, task_instruction: str) -> dict:
        response = self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"Here is my resume:\n\n{resume_text}",
                            "cache_control": {"type": "ephemeral"},
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": f"Here is the job description:\n\n{jd_text}\n\n{task_instruction}",
                },
            ],
        )

        if self.verbose:
            u = response.usage
            print(
                f"\n[cache] input={u.input_tokens} "
                f"cache_write={getattr(u, 'cache_creation_input_tokens', 0)} "
                f"cache_read={getattr(u, 'cache_read_input_tokens', 0)} "
                f"output={u.output_tokens}"
            )

        raw = response.content[0].text.strip()
        # Strip markdown code fences if the model wraps the JSON anyway
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
            raw = raw.rsplit("```", 1)[0]

        return json.loads(raw)

    def tailor_resume(self, resume_text: str, jd_text: str) -> dict:
        return self._call(resume_text, jd_text, TAILOR_INSTRUCTION)

    def generate_cover_letter(self, resume_text: str, jd_text: str) -> dict:
        return self._call(resume_text, jd_text, COVER_LETTER_INSTRUCTION)

    def estimate_ats_score(self, resume_text: str, jd_text: str) -> dict:
        return self._call(resume_text, jd_text, ATS_SCORE_INSTRUCTION)
