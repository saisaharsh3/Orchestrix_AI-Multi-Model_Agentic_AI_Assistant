"""
core/stylometric_defense.py - Linguistic Masking Defense (Experiment 5)

Implements stylometric defense mechanisms to reduce the effectiveness of 
stylometric attacks that can link users across local-mode and API-mode queries.

Reference: Experiment 5 (Stylometric Unlinkability Analysis)
Research: See research/EXPERIMENT_5_CRITICAL_BRIEFING.md
"""

import re
import string
from typing import Dict, List
from core.logger import get_logger

logger = get_logger(__name__)


class StyleometricDefense:
    """Implements linguistic masking defenses against stylometric attacks"""

    @staticmethod
    def normalize_style(query: str) -> str:
        """
        Normalize writing style by removing stylometric outliers.

        Defense mechanism: -18.5% reduction in stylometric similarity (Exp 5)
        
        This is Phase 1 defense: quick deployment, partial mitigation.
        For stronger defense, see semantic_paraphrase() or text_differential_privacy().

        Args:
            query: Original user query

        Returns:
            Style-normalized query that maintains intent but reduces stylistic markers

        Implementation:
            1. Strip unusual punctuation patterns (!!!???)
            2. Normalize sentence length (avoid very short/long sentences)
            3. Remove excessive capitalization
            4. Regularize common patterns (contractions expand, etc.)
            5. Balance vocabulary complexity (remove very rare words)
        """

        if not query or len(query) < 3:
            return query

        logger.debug(f"Normalizing style for query: {query[:50]}...")

        normalized = query

        # ── Step 1: Normalize unusual punctuation patterns ──────────────────
        # Replace multiple punctuation marks with single marks
        normalized = re.sub(r"!{2,}", "!", normalized)  # !! → !
        normalized = re.sub(r"\?{2,}", "?", normalized)  # ?? → ?
        normalized = re.sub(r"\.{2,}", ".", normalized)  # .. → .

        # Remove excessive punctuation at end (!!!, ???, etc.)
        normalized = re.sub(r"([!?.]){2,}$", r"\1", normalized)

        # ── Step 2: Normalize sentence structure ──────────────────────────
        # Split into sentences
        sentences = re.split(r"[.!?]+", normalized)
        sentences = [s.strip() for s in sentences if s.strip()]

        if sentences:
            # Normalize sentence lengths to avoid extremes
            normalized_sentences = []
            for sentence in sentences:
                words = sentence.split()

                # If too short (< 3 words), pad with neutral words
                if len(words) < 3:
                    words.append("please")

                # If too long (> 25 words), break into chunks at conjunctions
                if len(words) > 25:
                    # Find natural break points (and, but, or, because)
                    new_words = []
                    current_chunk = []
                    for word in words:
                        current_chunk.append(word)
                        if len(current_chunk) > 15 and word.lower() in {
                            "and",
                            "but",
                            "or",
                            "so",
                            "because",
                        }:
                            new_words.extend(current_chunk)
                            new_words.append(".")
                            current_chunk = []
                    new_words.extend(current_chunk)
                    words = new_words

                normalized_sentences.append(" ".join(words))

            normalized = ". ".join(normalized_sentences)
            if not normalized.endswith("."):
                normalized += "."

        # ── Step 3: Remove excessive capitalization ──────────────────────
        # Convert ALL_CAPS words to Title case (except acronyms < 3 chars)
        words = normalized.split()
        new_words = []
        for word in words:
            # Keep acronyms (< 3 letters, all caps) but convert longer sequences
            if len(word.rstrip(string.punctuation)) > 3 and word.isupper():
                word = word.capitalize()
            new_words.append(word)
        normalized = " ".join(new_words)

        # ── Step 4: Expand common contractions ────────────────────────────
        contraction_map = {
            "don't": "do not",
            "doesn't": "does not",
            "didn't": "did not",
            "won't": "will not",
            "wouldn't": "would not",
            "can't": "cannot",
            "couldn't": "could not",
            "shouldn't": "should not",
            "isn't": "is not",
            "aren't": "are not",
            "wasn't": "was not",
            "weren't": "were not",
            "haven't": "have not",
            "hasn't": "has not",
            "hadn't": "had not",
            "i'm": "i am",
            "i've": "i have",
            "i'll": "i will",
            "i'd": "i would",
            "you're": "you are",
            "you've": "you have",
            "you'll": "you will",
            "you'd": "you would",
            "he's": "he is",
            "she's": "she is",
            "it's": "it is",
            "that's": "that is",
            "what's": "what is",
            "where's": "where is",
            "who's": "who is",
        }

        for contraction, expansion in contraction_map.items():
            normalized = re.sub(
                r"\b" + re.escape(contraction) + r"\b",
                expansion,
                normalized,
                flags=re.IGNORECASE,
            )

        # ── Step 5: Normalize question marks and exclamations ──────────────
        # Replace ??? with single ? and !!! with single !
        normalized = re.sub(r"\?+", "?", normalized)
        normalized = re.sub(r"!+", "!", normalized)

        # ── Step 6: Normalize whitespace ───────────────────────────────────
        normalized = re.sub(r"\s+", " ", normalized).strip()

        logger.debug(f"Normalized query: {normalized[:50]}...")

        return normalized

    @staticmethod
    def semantic_paraphrase_placeholder(query: str) -> str:
        """
        Placeholder for semantic paraphrasing defense (Phase 2).

        Phase 2 implementation will use LLM to rewrite queries while preserving intent,
        expected to reduce stylometric similarity by 40-60%.

        Current implementation: Returns query unchanged (awaiting Phase 2 research)

        See: DEFENSE_IMPLEMENTATION_ROADMAP.md Phase 3 for implementation plan
        """
        logger.debug("Semantic paraphrasing not yet implemented (Phase 2 pending)")
        return query

    @staticmethod
    def text_dp_placeholder(query: str) -> str:
        """
        Placeholder for text differential privacy defense (Phase 2).

        Phase 2 implementation will add formal DP noise to queries,
        expected to reduce stylometric similarity by 50-70%.

        Current implementation: Returns query unchanged (awaiting Phase 2 research)

        See: DEFENSE_IMPLEMENTATION_ROADMAP.md Phase 3 for implementation plan
        """
        logger.debug("Text DP not yet implemented (Phase 2 pending)")
        return query

    @staticmethod
    def get_defense_metrics() -> Dict[str, float]:
        """
        Return effectiveness metrics for all defenses from Experiment 5.

        This data is used to inform Phase 2-3 defense selection decisions.

        Return format:
        {
            "baseline": 0.8456,  # Mean stylometric similarity (VULNERABLE)
            "normalize": 0.6888,  # -18.5% reduction
            "paraphrase": 0.8467,  # -0.1% reduction (INEFFECTIVE)
            "obfuscate": 0.8142,  # -3.7% reduction (WEAK)
            "semantic_paraphrase_est": 0.35,  # -40-60% estimated (Phase 2)
            "text_dp_est": 0.25,  # -50-70% estimated (Phase 2)
            "threshold_safe": 0.65,  # Below this = user safe
        }
        """
        return {
            "baseline": 0.8456,
            "normalize": 0.6888,
            "paraphrase": 0.8467,
            "obfuscate": 0.8142,
            "semantic_paraphrase_est": 0.35,
            "text_dp_est": 0.25,
            "multi_device_est": 0.0,
            "threshold_safe": 0.65,
            "current_best_deployed": 0.6888,
        }


# Usage:
#
# from core.stylometric_defense import StyleometricDefense
#
# # In orchestrator.py, when stealth_mode is enabled:
# if user_prefs.get("stealth_mode"):
#     query = StyleometricDefense.normalize_style(query)
#     logger.debug("Applied Stealth Mode (style normalization) to query")
#
# # Phase 2: When semantic paraphrasing is ready:
# if user_prefs.get("defense_mode") == "paraphrase":
#     query = StyleometricDefense.semantic_paraphrase(query)
