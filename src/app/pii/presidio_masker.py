"""Microsoft Presidio PII masking."""

from presidio_analyzer import AnalyzerEngine, RecognizerResult
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig


# Entity → replacement token mapping.
# Extend this dict to add domain-specific mask tokens.
_MASK_TOKENS: dict[str, str] = {
    "PERSON": "[NAME]",
    "EMAIL_ADDRESS": "[EMAIL]",
    "PHONE_NUMBER": "[PHONE_NUMBER]",
    "LOCATION": "[LOCATION]",
    "NRP": "[GROUP]",          # nationality / religion / political group
    "DATE_TIME": "[DATE]",
    "IBAN_CODE": "[IBAN]",
    "CREDIT_CARD": "[CARD]",
    "CRYPTO": "[CRYPTO]",
    "IP_ADDRESS": "[IP]",
    "URL": "[URL]",
    "US_SSN": "[SSN]",
    "MEDICAL_LICENSE": "[LICENSE]",
}

_SUPPORTED_LANGUAGES = ["en", "ru"]


class PIIMasker:
    """Masks PII in arbitrary text using Microsoft Presidio."""

    def __init__(self) -> None:
        # Use the default spaCy NLP engine (en_core_web_lg must be installed).
        # For Russian, add a multilingual or separate model as needed.
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()

        # Build anonymizer operator config from the token map.
        self._operators = {
            entity: OperatorConfig("replace", {"new_value": token})
            for entity, token in _MASK_TOKENS.items()
        }

    async def mask_text(self, text: str, language: str = "en") -> str:
        """Replace PII entities in *text* with mask tokens.

        Args:
            text:     Input text (user message).
            language: ISO-639-1 code; "en" by default.

        Returns:
            Text with PII replaced, e.g. "Call John at 555-1234" →
            "Call [NAME] at [PHONE_NUMBER]".
        """
        if not text.strip():
            return text

        # Detect PII entities
        results: list[RecognizerResult] = self.analyzer.analyze(
            text=text,
            language=language if language in _SUPPORTED_LANGUAGES else "en",
            entities=list(_MASK_TOKENS.keys()),
        )

        if not results:
            return text

        # Anonymize using custom tokens
        anonymized = self.anonymizer.anonymize(
            text=text,
            analyzer_results=results,
            operators=self._operators,
        )
        return anonymized.text

    async def mask_text_ru(self, text: str) -> str:
        """Convenience wrapper for Russian input.

        Note: Presidio's built-in Russian support is limited.
        For production, integrate a Russian NER model (e.g. natasha / DeepPavlov).
        This currently falls back to English recognizers on the Russian text.
        """
        # TODO: integrate Russian NER model for better RU PII detection.
        return await self.mask_text(text, language="en")
