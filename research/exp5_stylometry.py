#!/usr/bin/env python3
"""
Experiment 5: Stylometric Unlinkability Analysis

Research Question:
Can an attacker link local-mode queries to API-mode queries from the same user
by analyzing writing style ("stylometric fingerprinting")?

If yes: Users lose unlinkability, revealing behavioral patterns even with zero-disclosure
If no:  Stylometric defenses successfully prevent identity linking across modes

Threat Model:
- Attacker observes all API-mode queries (sent to Google, publicly accessible)
- Attacker gains access to some local-mode queries (device backup, forensics)
- Attacker extracts stylometric features and attempts to link them
- Goal: Prove/disprove that mode switching reveals identity

Defenses Tested:
1. Query Paraphrasing: Rephrase to neutral, formal language
2. Style Normalization: Force uniform formality/vocabulary
3. Obfuscation: Add random elements to stylometric signature
"""

import json
import numpy as np
from collections import defaultdict
import re
import string
from typing import Dict, List, Tuple
from dataclasses import dataclass
from sklearn.metrics.pairwise import cosine_similarity


@dataclass
class StyleometricFeatures:
    """Extract writing style features from a query"""
    
    # Lexical features
    avg_word_length: float
    avg_sentence_length: float
    type_token_ratio: float  # vocabulary diversity
    
    # Syntactic features
    punctuation_ratio: float
    question_ratio: float
    exclamation_ratio: float
    comma_ratio: float
    
    # Stylistic features
    capitalization_ratio: float
    uppercase_word_ratio: float
    lowercase_word_ratio: float
    
    # Sophistication
    long_word_ratio: float  # words > 6 chars
    unique_bigram_count: int
    
    def to_vector(self) -> np.ndarray:
        """Convert to numeric vector for ML"""
        return np.array([
            self.avg_word_length,
            self.avg_sentence_length,
            self.type_token_ratio,
            self.punctuation_ratio,
            self.question_ratio,
            self.exclamation_ratio,
            self.comma_ratio,
            self.capitalization_ratio,
            self.uppercase_word_ratio,
            self.lowercase_word_ratio,
            self.long_word_ratio,
            self.unique_bigram_count,
        ])


class StyleometricAnalyzer:
    """Analyze writing style to detect identity linking"""
    
    @staticmethod
    def extract_features(text: str) -> StyleometricFeatures:
        """Extract stylometric features from text"""
        
        # Clean text
        text = text.strip()
        if not text:
            return StyleometricFeatures(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        
        # Sentence-level features
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # Word-level features
        words = text.split()
        word_lengths = [len(w.strip(string.punctuation)) for w in words if w.strip(string.punctuation)]
        
        # Calculate metrics
        avg_word_length = np.mean(word_lengths) if word_lengths else 0
        avg_sentence_length = np.mean([len(s.split()) for s in sentences]) if sentences else 0
        
        unique_words = len(set(words))
        type_token_ratio = unique_words / len(words) if words else 0
        
        # Punctuation
        punct_count = sum(1 for c in text if c in string.punctuation)
        punctuation_ratio = punct_count / len(text) if text else 0
        
        question_count = text.count('?')
        question_ratio = question_count / len(sentences) if sentences else 0
        
        exclamation_count = text.count('!')
        exclamation_ratio = exclamation_count / len(sentences) if sentences else 0
        
        comma_count = text.count(',')
        comma_ratio = comma_count / len(words) if words else 0
        
        # Capitalization
        capital_chars = sum(1 for c in text if c.isupper())
        capitalization_ratio = capital_chars / len(text) if text else 0
        
        capital_words = sum(1 for w in words if w[0].isupper())
        uppercase_word_ratio = capital_words / len(words) if words else 0
        
        lowercase_words = sum(1 for w in words if w[0].islower())
        lowercase_word_ratio = lowercase_words / len(words) if words else 0
        
        # Sophistication
        long_words = sum(1 for w in word_lengths if w > 6)
        long_word_ratio = long_words / len(word_lengths) if word_lengths else 0
        
        # Bigrams
        bigrams = [words[i] + words[i+1] for i in range(len(words)-1)]
        unique_bigram_count = len(set(bigrams))
        
        return StyleometricFeatures(
            avg_word_length=avg_word_length,
            avg_sentence_length=avg_sentence_length,
            type_token_ratio=type_token_ratio,
            punctuation_ratio=punctuation_ratio,
            question_ratio=question_ratio,
            exclamation_ratio=exclamation_ratio,
            comma_ratio=comma_ratio,
            capitalization_ratio=capitalization_ratio,
            uppercase_word_ratio=uppercase_word_ratio,
            lowercase_word_ratio=lowercase_word_ratio,
            long_word_ratio=long_word_ratio,
            unique_bigram_count=unique_bigram_count,
        )
    
    @staticmethod
    def link_attack(api_vectors: np.ndarray, local_vectors: np.ndarray) -> Dict:
        """
        Stylometric linking attack:
        Given API-mode query vectors and local-mode query vectors,
        try to link them based on writing style similarity
        
        Returns: Linking accuracy and vulnerability metrics
        """
        similarities = cosine_similarity(api_vectors, local_vectors)
        
        # For each API query, find closest local query
        links = np.argmax(similarities, axis=1)
        max_similarities = np.max(similarities, axis=1)
        
        return {
            "mean_max_similarity": float(np.mean(max_similarities)),
            "median_max_similarity": float(np.median(max_similarities)),
            "std_max_similarity": float(np.std(max_similarities)),
            "high_confidence_links": int(np.sum(max_similarities > 0.8)),
            "medium_confidence_links": int(np.sum((max_similarities > 0.6) & (max_similarities <= 0.8))),
            "vulnerable": float(np.mean(max_similarities)) > 0.65,  # Vulnerable if avg similarity > 0.65
        }


class StyleometricDefense:
    """Apply defenses against stylometric attacks"""
    
    @staticmethod
    def paraphrase_query(query: str) -> str:
        """
        Defense 1: Paraphrase to neutral, formal language
        Simple heuristic: convert to passive voice patterns, formal vocabulary
        """
        # Remove personal pronouns and replace with passive constructions
        query = re.sub(r'\bI\b', 'The user', query, flags=re.IGNORECASE)
        query = re.sub(r'\bwe\b', 'Users', query, flags=re.IGNORECASE)
        query = re.sub(r'\bmy\b', 'the', query, flags=re.IGNORECASE)
        
        # Normalize contractions to formal
        contractions = {
            "don't": "do not",
            "can't": "cannot",
            "won't": "will not",
            "it's": "it is",
            "that's": "that is",
            "what's": "what is",
        }
        for short, long in contractions.items():
            query = re.sub(short, long, query, flags=re.IGNORECASE)
        
        # Normalize exclamations
        query = re.sub(r'!+', '.', query)
        
        # Normalize question marks
        query = re.sub(r'\?+', '?', query)
        
        return query
    
    @staticmethod
    def normalize_style(query: str) -> str:
        """
        Defense 2: Normalize style (uniform formality, sentence structure)
        Force: Title Case, Standard punctuation, Simple sentence structure
        """
        # Title case
        words = query.split()
        words = [w.capitalize() if not w.isupper() else w for w in words]
        query = ' '.join(words)
        
        # Remove excessive punctuation
        query = re.sub(r'[!?]{2,}', '.', query)
        
        # Normalize spacing
        query = re.sub(r'\s+', ' ', query).strip()
        
        # Ensure ends with period
        if not query.endswith(('.', '?')):
            query += '.'
        
        return query
    
    @staticmethod
    def obfuscate_query(query: str) -> str:
        """
        Defense 3: Obfuscate by adding noise to stylometric signature
        Strategy: randomly add/remove punctuation, vary capitalization
        """
        import random
        
        # Random capitalization pattern
        if random.random() > 0.5:
            # ALL CAPS
            query = query.upper()
        else:
            # lowercase
            query = query.lower()
        
        # Random punctuation insertion
        words = query.split()
        if len(words) > 3:
            idx = random.randint(1, len(words)-1)
            punct = random.choice([',', ';', '-'])
            words.insert(idx, punct)
        
        query = ' '.join(words)
        return query


def load_test_queries() -> Tuple[List[str], List[str]]:
    """Load test queries from research data"""
    try:
        with open('test_queries.json', 'r') as f:
            all_queries = json.load(f)
            
        # Simulate: first 20 queries are "API mode"
        # next 20 are "local mode" (same user, but mode-switched)
        api_queries = [q.get('query', '') for q in all_queries[:20] if q.get('query')]
        local_queries = [q.get('query', '') for q in all_queries[20:40] if q.get('query')]
        
        return api_queries, local_queries
    except Exception as e:
        print(f"Error loading queries: {e}")
        # Fallback: synthetic queries
        return [], []


def main():
    print("=" * 80)
    print("EXPERIMENT 5: STYLOMETRIC UNLINKABILITY ANALYSIS")
    print("=" * 80)
    print()
    
    # Load test queries
    api_queries, local_queries = load_test_queries()
    
    if not api_queries or not local_queries:
        # Synthetic test case
        print("Using synthetic test queries (fallback)...")
        api_queries = [
            "What is the weather today?",
            "I need to find information about Python.",
            "Can you help me understand machine learning?",
            "Tell me about artificial intelligence",
            "How do neural networks work?",
        ] * 4
        
        local_queries = [
            "What does the weather look like?",
            "I'm looking for info on Python programming.",
            "Could you explain machine learning to me?",
            "Fill me in on AI",
            "Explain neural networks",
        ] * 4
    
    print(f"Analyzing {len(api_queries)} API-mode queries")
    print(f"Analyzing {len(local_queries)} local-mode queries")
    print()
    
    # ============================================================================
    # PHASE 1: Baseline Attack (No Defense)
    # ============================================================================
    print("PHASE 1: BASELINE ATTACK (No Defenses)")
    print("-" * 80)
    
    analyzer = StyleometricAnalyzer()
    
    api_features = [analyzer.extract_features(q) for q in api_queries]
    local_features = [analyzer.extract_features(q) for q in local_queries]
    
    api_vectors = np.array([f.to_vector() for f in api_features])
    local_vectors = np.array([f.to_vector() for f in local_features])
    
    # Normalize vectors
    api_vectors = (api_vectors - np.mean(api_vectors, axis=0)) / (np.std(api_vectors, axis=0) + 1e-8)
    local_vectors = (local_vectors - np.mean(local_vectors, axis=0)) / (np.std(local_vectors, axis=0) + 1e-8)
    
    baseline_results = analyzer.link_attack(api_vectors, local_vectors)
    
    print(f"Mean max similarity: {baseline_results['mean_max_similarity']:.4f}")
    print(f"Median max similarity: {baseline_results['median_max_similarity']:.4f}")
    print(f"High-confidence links (>0.8): {baseline_results['high_confidence_links']}")
    print(f"Medium-confidence links (0.6-0.8): {baseline_results['medium_confidence_links']}")
    print(f"System VULNERABLE to stylometric attack: {baseline_results['vulnerable']}")
    print()
    
    # ============================================================================
    # PHASE 2: Defense Evaluation
    # ============================================================================
    print("PHASE 2: DEFENSE EVALUATION")
    print("-" * 80)
    
    defenses = {
        "paraphrase": StyleometricDefense.paraphrase_query,
        "normalize": StyleometricDefense.normalize_style,
        "obfuscate": StyleometricDefense.obfuscate_query,
    }
    
    defense_results = {}
    
    for defense_name, defense_fn in defenses.items():
        print(f"\nTesting: {defense_name.upper()}")
        
        # Apply defense to local queries
        defended_local_queries = [defense_fn(q) for q in local_queries]
        
        # Re-extract features
        defended_local_features = [analyzer.extract_features(q) for q in defended_local_queries]
        defended_local_vectors = np.array([f.to_vector() for f in defended_local_features])
        
        # Normalize
        defended_local_vectors = (defended_local_vectors - np.mean(defended_local_vectors, axis=0)) / (
            np.std(defended_local_vectors, axis=0) + 1e-8
        )
        
        # Attack
        defense_attack = analyzer.link_attack(api_vectors, defended_local_vectors)
        defense_results[defense_name] = defense_attack
        
        print(f"  Mean max similarity: {defense_attack['mean_max_similarity']:.4f}")
        print(f"  Reduction from baseline: {(1 - defense_attack['mean_max_similarity'] / baseline_results['mean_max_similarity']) * 100:.1f}%")
        print(f"  High-confidence links: {defense_attack['high_confidence_links']}")
        print(f"  Vulnerable: {defense_attack['vulnerable']}")
    
    # ============================================================================
    # PHASE 3: Combined Defense
    # ============================================================================
    print()
    print("PHASE 3: COMBINED DEFENSE (Paraphrase + Normalize)")
    print("-" * 80)
    
    combined_queries = [
        StyleometricDefense.normalize_style(StyleometricDefense.paraphrase_query(q))
        for q in local_queries
    ]
    
    combined_features = [analyzer.extract_features(q) for q in combined_queries]
    combined_vectors = np.array([f.to_vector() for f in combined_features])
    
    combined_vectors = (combined_vectors - np.mean(combined_vectors, axis=0)) / (
        np.std(combined_vectors, axis=0) + 1e-8
    )
    
    combined_attack = analyzer.link_attack(api_vectors, combined_vectors)
    
    print(f"Mean max similarity: {combined_attack['mean_max_similarity']:.4f}")
    print(f"Reduction from baseline: {(1 - combined_attack['mean_max_similarity'] / baseline_results['mean_max_similarity']) * 100:.1f}%")
    print(f"High-confidence links: {combined_attack['high_confidence_links']}")
    print(f"Vulnerable: {combined_attack['vulnerable']}")
    
    # ============================================================================
    # RESULTS SUMMARY
    # ============================================================================
    print()
    print("=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80)
    
    results = {
        "baseline": baseline_results,
        "defenses": defense_results,
        "combined": combined_attack,
        "key_findings": {
            "baseline_vulnerability": baseline_results["vulnerable"],
            "baseline_similarity": baseline_results["mean_max_similarity"],
            "best_defense": min(defense_results.items(), key=lambda x: x[1]["mean_max_similarity"])[0],
            "best_defense_similarity": min(
                [d["mean_max_similarity"] for d in defense_results.values()]
            ),
            "combined_defense_similarity": combined_attack["mean_max_similarity"],
            "combined_reduces_vulnerability": not combined_attack["vulnerable"],
            "recommendation": (
                "DEPLOY_COMBINED_DEFENSE" if not combined_attack["vulnerable"]
                else "REQUIRES_FURTHER_RESEARCH"
            ),
        }
    }
    
    print(f"\n✅ BASELINE VULNERABILITY: {results['key_findings']['baseline_vulnerability']}")
    print(f"   Mean similarity (baseline): {results['key_findings']['baseline_similarity']:.4f}")
    print(f"\n✅ BEST SINGLE DEFENSE: {results['key_findings']['best_defense'].upper()}")
    print(f"   Mean similarity: {results['key_findings']['best_defense_similarity']:.4f}")
    print(f"\n✅ COMBINED DEFENSE EFFECTIVENESS:")
    print(f"   Mean similarity: {results['key_findings']['combined_defense_similarity']:.4f}")
    print(f"   Eliminates vulnerability: {results['key_findings']['combined_reduces_vulnerability']}")
    print(f"\n✅ RECOMMENDATION: {results['key_findings']['recommendation']}")
    
    # Save results
    with open('results_exp5.json', 'w') as f:
        # Convert numpy types for JSON serialization
        json_results = {
            "baseline": {k: float(v) if isinstance(v, (np.floating, np.integer)) else v
                         for k, v in baseline_results.items()},
            "defenses": {
                k: {kk: float(vv) if isinstance(vv, (np.floating, np.integer)) else vv
                    for kk, vv in v.items()}
                for k, v in defense_results.items()
            },
            "combined": {k: float(v) if isinstance(v, (np.floating, np.integer)) else v
                        for k, v in combined_attack.items()},
            "key_findings": {k: float(v) if isinstance(v, (np.floating, np.integer)) else v
                            for k, v in results['key_findings'].items()},
        }
        json.dump(json_results, f, indent=2)
    
    print(f"\n✅ Results saved to results_exp5.json")
    print()


if __name__ == "__main__":
    main()
