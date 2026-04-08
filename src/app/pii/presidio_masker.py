"""Microsoft Presidio PII masking with Russian language support."""

from presidio_analyzer import AnalyzerEngine, RecognizerResult
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
import logging
import spacy

logger = logging.getLogger(__name__)

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

_SUPPORTED_LANGUAGES = ["ru"]


class PIIMasker:
    """Masks PII in arbitrary text using Microsoft Presidio with Russian NLP."""

    def __init__(self) -> None:
        # Verify Russian spaCy model is available
        try:
            spacy.load("ru_core_news_md")
        except OSError as e:
            raise RuntimeError(
                "Russian spaCy model 'ru_core_news_md' not found. "
                "Install it with: python -m spacy download ru_core_news_md"
            ) from e

        # Configure NLP engine to use Russian spaCy model
        nlp_engine_provider = NlpEngineProvider(
            nlp_configuration={
                "nlp_engine_name": "spacy",
                "models": [{"lang_code": "ru", "model_name": "ru_core_news_md"}],
            }
        )
        nlp_engine = nlp_engine_provider.create_engine()

        self.analyzer = AnalyzerEngine(
            nlp_engine=nlp_engine,
            supported_languages=_SUPPORTED_LANGUAGES,
        )
        self.anonymizer = AnonymizerEngine()

        # Build anonymizer operator config from the token map.
        self._operators = {
            entity: OperatorConfig("replace", {"new_value": token})
            for entity, token in _MASK_TOKENS.items()
        }

        logger.info("PIIMasker initialized with Russian language support (ru_core_news_md)")

    async def mask_text(self, text: str, language: str = "ru") -> str:
        """Replace PII entities in *text* with mask tokens.

        Args:
            text:     Input text (user message).
            language: ISO-639-1 code; "ru" by default.

        Returns:
            Text with PII replaced, e.g. "Call John at 555-1234" →
            "Call [NAME] at [PHONE_NUMBER]".
        """
        masked, _ = await self.mask_text_with_spans(text, language)
        return masked

    async def mask_text_with_spans(
        self, text: str, language: str = "ru"
    ) -> tuple[str, list[dict]]:
        """Replace PII and also return metadata about replaced spans.

        Args:
            text: Input text
            language: ISO-639-1 code

        Returns:
            (masked_text, spans) where spans is a list of dicts:
                {
                    "start": int,        # char offset in original text
                    "end": int,          # char offset in original text
                    "entity_type": str,  # e.g., "PERSON"
                    "original": str,     # original text that was masked
                    "replaced_token": str  # e.g., "[NAME]"
                }
        """
        if not text.strip():
            return text, []

        # Detect PII entities
        results: list[RecognizerResult] = self.analyzer.analyze(
            text=text,
            language=language if language in _SUPPORTED_LANGUAGES else "en",
            entities=list(_MASK_TOKENS.keys()),
        )

        if not results:
            return text, []

        # Build spans list (before anonymization modifies text)
        spans = []
        for r in results:
            entity_type = r.entity_type
            token = _MASK_TOKENS.get(entity_type, f"[{entity_type}]")
            spans.append({
                "start": r.start,
                "end": r.end,
                "entity_type": entity_type,
                "original": text[r.start:r.end],
                "replaced_token": token,
            })

        # Anonymize using custom tokens
        anonymized = self.anonymizer.anonymize(
            text=text,
            analyzer_results=results,
            operators=self._operators,
        )
        return anonymized.text, spans
