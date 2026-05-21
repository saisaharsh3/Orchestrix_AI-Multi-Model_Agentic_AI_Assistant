# Defense Implementation Roadmap: Stylometric Unlinkability

**Status:** Planning Phase  
**Priority:** 🔴 HIGH  
**Timeline:** 6 weeks to strong mitigation  
**Effort:** 60-80 dev hours + 20-30 research hours  

---

## Executive Overview

**Problem:** Stylometric attacks can link local-mode to API-mode queries with 84.6% confidence, breaking unlinkability even though PDFs remain confidential.

**Goal:** Reduce stylometric similarity from 0.8456 to <0.65 (below vulnerability threshold) within 6 weeks.

**Approach:** Layered defenses (documentation → normalization → strong defenses)

---

## Phase 1: IMMEDIATE (This Week) - Documentation & User Protection

### 1A: Privacy ToS Update ⏱️ 1-2 hours

**Current ToS Language:**
```
"Local mode keeps your PDFs private and on-device."
```

**Updated ToS Language:**
```
"Local mode ensures your PDF documents remain on-device and are 
never sent to external servers. However, writing style analysis 
(stylometry) may enable linking of local and API-mode queries 
if both are compromised (e.g., via device forensics or cloud backup).

For maximum privacy across modes, we recommend:
1. Using separate devices for local vs. API research
2. Using only one mode consistently 
3. Enabling automatic style normalization (Stealth Mode)

Local query metadata (timing, frequency) may still pose privacy 
risks even without document content leakage."
```

**Acceptance Criteria:**
- [ ] Legal review completed
- [ ] ToS updated and published
- [ ] User notification sent (email/in-app)
- [ ] Document filed for compliance audit

**Owner:** Legal + Product  
**Review:** Security Team

---

### 1B: In-App Warning System ⏱️ 2-3 hours

**Implementation:** Add warning modal when user switches modes

```python
# Location: core/orchestrator.py or core/intent.py

class ModeWarning:
    @staticmethod
    def should_warn_mode_switch(current_mode, previous_mode, switch_count):
        """Determine if user should see mode-switch warning"""
        if current_mode == previous_mode:
            return False
        if switch_count >= 3:  # Warn after 3 switches
            return True
        return False
    
    @staticmethod
    def get_warning_message(target_mode):
        if target_mode == "local":
            return (
                "⚠️ You're switching to Local Mode\n\n"
                "Local Mode keeps your PDFs on-device (zero-disclosure).\n"
                "However, frequent mode switching can reveal which topics "
                "you research privately through writing style analysis.\n\n"
                "💡 Recommendation: For maximum privacy, use dedicated mode "
                "(only Local OR only API) or separate device profiles."
            )
        else:
            return (
                "ℹ️ You're switching to API Mode\n\n"
                "API mode sends queries to Gemini for better reasoning.\n"
                "Your writing style may be detectable across modes.\n\n"
                "💡 Tip: Use different wording/devices if privacy is critical."
            )
```

**Acceptance Criteria:**
- [ ] Warning displays on 3rd mode switch
- [ ] Warning includes actionable recommendations
- [ ] Can be dismissed and not shown again (user preference)
- [ ] Analytics track dismissal rate
- [ ] A/B test effectiveness (does warning change behavior?)

**Owner:** UI/UX + Backend  
**Metrics:** Dismissal rate, mode-switch frequency before/after

---

### 1C: Support Documentation ⏱️ 1 hour

**Create:** `STYLOMETRY_FAQ.md` for support team

```markdown
# Stylometry & Privacy - Support FAQ

## Q: What is stylometry?
A: Stylometry is the analysis of writing style patterns (vocabulary, 
   sentence structure, punctuation) to identify authors. Even different 
   questions about the same topic share consistent stylistic patterns.

## Q: Does this mean local mode isn't private?
A: No. Local mode IS fully private for PDF content (zero-disclosure). 
   The risk is *behavioral privacy* — an attacker can infer which 
   topics a user researches privately vs. casually.

## Q: Should users stop using local mode?
A: No. Local mode is still the best option for sensitive PDFs. 
   The recommendation is to use ONE mode consistently or separate devices.

## Q: How do we mitigate this?
A: Three layers:
   1. Style normalization (automatic, reduces 18.5%)
   2. Semantic paraphrasing (coming next month)
   3. Separate device profiles (zero-linkable)

## Q: Is this a security vulnerability?
A: It's a privacy property edge case. Not exploitable locally, 
   only exploitable if both API and local queries are compromised.

## Q: What should I tell users?
A: "We discovered a privacy property we could improve. We're fixing it 
   proactively, and here are three ways to protect yourself today."
```

**Acceptance Criteria:**
- [ ] Team reads and understands FAQ
- [ ] Support trained on talking points
- [ ] Escalation path defined (privacy@company)
- [ ] Response template created for user inquiries

**Owner:** Product Support + Security  

---

## Phase 2: SHORT-TERM (Next Week) - Basic Defenses

### 2A: Style Normalization Implementation ⏱️ 4-6 hours dev + 2 hours testing

**What It Does:** Reduces stylometric similarity from 0.8456 → 0.6888 (18.5% reduction)

**Implementation:** Add to query processing pipeline

```python
# File: core/style_defense.py

import re

class StyleNormalizer:
    """Apply consistent style transformations to reduce stylometric signatures"""
    
    @staticmethod
    def normalize(query: str, aggressive: bool = False) -> str:
        """
        Normalize query style for privacy
        
        Args:
            query: Original user query
            aggressive: Apply stronger transformations
            
        Returns:
            Style-normalized query
        """
        query = query.strip()
        
        # 1. Standardize capitalization
        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', query)
        normalized_sentences = []
        
        for sentence in sentences:
            if sentence.strip():
                # Capitalize first letter only
                normalized = sentence[0].upper() + sentence[1:].lower()
                normalized_sentences.append(normalized)
        
        query = ' '.join(normalized_sentences)
        
        # 2. Remove excessive punctuation
        query = re.sub(r'[!?]{2,}', '.', query)  # Multiple !! → single .
        query = re.sub(r'\.{2,}', '.', query)    # Multiple .. → single .
        
        # 3. Remove contractions (if aggressive)
        if aggressive:
            contractions = {
                r"\bdon't\b": "do not",
                r"\bcan't\b": "cannot",
                r"\bwon't\b": "will not",
                r"\bit's\b": "it is",
                r"\bthat's\b": "that is",
                r"\bwhat's\b": "what is",
            }
            for short, long in contractions.items():
                query = re.sub(short, long, query, flags=re.IGNORECASE)
        
        # 4. Ensure ends with period
        if not query.endswith(('.', '?', '!')):
            query += '.'
        
        # 5. Normalize whitespace
        query = re.sub(r'\s+', ' ', query).strip()
        
        return query
    
    @staticmethod
    def format_for_api(original_query: str, mode: str = "api") -> str:
        """Format query for API submission"""
        if mode == "api":
            # Apply normalization to reduce style
            return StyleNormalizer.normalize(original_query, aggressive=False)
        else:
            # Local mode: original intent matters more than privacy here
            return original_query

# Integration point
class OrchestrationPipeline:
    def process_query(self, query: str, target_mode: str):
        # ... existing code ...
        
        # Apply style normalization if user enabled Stealth Mode
        if self.user_settings.get("stealth_mode_enabled", False):
            query = StyleNormalizer.format_for_api(query, mode=target_mode)
        
        # Continue with LLM/API call
        # ... rest of pipeline ...
```

**Feature Flag:**
```python
# core/settings.py or environment
STEALTH_MODE_ENABLED = true  # Enable by default (opt-out)
STEALTH_MODE_AGGRESSIVE = false  # Don't enable aggressive mode yet
STEALTH_MODE_LOG_METRICS = true  # Track effectiveness
```

**Testing:**
```python
# File: tests/test_style_normalization.py

def test_style_normalization_reduces_similarity():
    from core.style_defense import StyleNormalizer
    from exp5_stylometry import StyleometricAnalyzer, StyleometricAnalyzer
    
    original = "What does differential privacy mean???"
    normalized = StyleNormalizer.normalize(original)
    
    assert normalized == "What does differential privacy mean?"
    
    # Verify similarity reduction
    analyzer = StyleometricAnalyzer()
    orig_features = analyzer.extract_features(original)
    norm_features = analyzer.extract_features(normalized)
    
    orig_vector = orig_features.to_vector()
    norm_vector = norm_features.to_vector()
    
    # Vectors should differ
    assert not np.allclose(orig_vector, norm_vector)

def test_normalized_queries_less_linkable():
    """Test that normalization reduces Exp5 stylometric attack effectiveness"""
    # Load test queries
    api_queries = [...]
    local_queries = [...]
    
    # Normalize local queries
    normalized_local = [StyleNormalizer.normalize(q) for q in local_queries]
    
    # Re-run stylometric attack
    results = analyzer.link_attack(api_vectors, normalized_vectors)
    
    # Verify improvement
    assert results['mean_max_similarity'] < 0.70
```

**Rollout Strategy:**
- [ ] Feature flag: default OFF (opt-in for brave users)
- [ ] Announce in release notes: "Introducing Stealth Mode (beta)"
- [ ] Collect metrics on adoption
- [ ] Monitor user feedback
- [ ] Flip to ON after 1 week of no complaints

**Acceptance Criteria:**
- [ ] Code reviewed by 2+ engineers
- [ ] Test coverage > 90%
- [ ] Performance impact < 5ms per query
- [ ] Documentation updated (in-app + help center)
- [ ] Metrics dashboard shows adoption rate
- [ ] Security review passed

**Owner:** Backend Engineering  
**Metrics:** Adoption rate, query latency, stylometric similarity reduction

---

### 2B: Research Planning Session ⏱️ 2 hours

**Participants:** Security, Product, Engineering, Research

**Agenda:**
1. **Review Experiment 5 findings** (30 min)
2. **Discuss defense priorities** (30 min)
3. **Allocate resources** (30 min)
4. **Set timeline** (30 min)

**Discussion Points:**
- ✅ Which strong defense to prioritize? (Semantic paraphrasing vs. Text DP)
- ✅ Budget for external security research?
- ✅ Timeline for next milestone?
- ✅ Risk tolerance for experimental defenses?

**Deliverable:** Defense prioritization matrix

---

## Phase 3: MEDIUM-TERM (Weeks 2-4) - Strong Defenses

### 3A: Semantic Paraphrasing Research ⏱️ 20-30 research hours

**Goal:** Implement LLM-based query paraphrasing that changes vocabulary while preserving intent

**Approach:**

```python
# File: core/paraphrase_defense.py

from gemini_llm import GeminiLLM

class SemanticParaphraser:
    """Paraphrase queries while preserving intent but changing style"""
    
    def __init__(self):
        self.llm = GeminiLLM()
        self.prompt_template = """
        Rephrase this query to change the writing style significantly while 
        preserving the exact intent and meaning. Use different vocabulary, 
        different sentence structure, different length. Make it completely 
        unrecognizable as coming from the same person.
        
        Original: {original}
        Paraphrased:
        """
    
    async def paraphrase(self, query: str) -> str:
        """Generate paraphrased version of query"""
        prompt = self.prompt_template.format(original=query)
        paraphrased = await self.llm.generate(prompt)
        return paraphrased.strip()
    
    async def paraphrase_with_confidence(self, query: str) -> dict:
        """Paraphrase and verify intent preservation"""
        paraphrased = await self.paraphrase(query)
        
        # Verify intent is preserved (use embedding similarity)
        intent_preserved = await self._verify_intent(query, paraphrased)
        
        if intent_preserved < 0.8:
            # Intent lost, try again
            return await self.paraphrase_with_confidence(query)
        
        return {
            "original": query,
            "paraphrased": paraphrased,
            "intent_similarity": intent_preserved,
            "success": True
        }
    
    async def _verify_intent(self, original: str, paraphrased: str) -> float:
        """Verify that paraphrasing preserved intent"""
        # Use embeddings to measure semantic similarity
        orig_embedding = await self.llm.embed(original)
        paraph_embedding = await self.llm.embed(paraphrased)
        
        similarity = cosine_similarity([orig_embedding], [paraph_embedding])[0][0]
        return float(similarity)
```

**Research Questions:**
1. What paraphrasing prompts best preserve intent while changing style?
2. What semantic similarity threshold ensures intent is preserved?
3. How much stylometric reduction does paraphrasing achieve?
4. What's the latency cost? (Extra LLM call per query)
5. Can we batch paraphrases off-device?

**Experimental Protocol:**
```
1. Generate 100 human-written test queries
2. Paraphrase each query (10 different prompts)
3. Measure:
   - Intent preservation (embedding similarity)
   - Stylometric reduction (Exp 5 attack effectiveness)
   - Latency (ms per paraphrase)
   - User preference (A/B test original vs. paraphrased style)
4. Optimize prompts based on results
5. Select top 3 prompts for production
```

**Timeline:**
- Week 2-3: Design & implement paraphraser
- Week 3-4: Run experiments (100 queries)
- Week 4: Optimize & prepare for rollout

**Success Criteria:**
- [ ] Intent preservation > 0.85 (embedding similarity)
- [ ] Stylometric similarity < 0.65 (below vulnerability threshold)
- [ ] Latency < 500ms per paraphrase
- [ ] User preference neutral or positive vs. original

**Owner:** Research + ML Engineering  
**Budget:** Research time (30 hours)

---

### 3B: Text Differential Privacy Research ⏱️ 30-40 research hours

**Goal:** Study formal privacy guarantees for query transformation

**Approach:** Apply DP mechanisms to text features

```python
# File: core/text_dp.py

import numpy as np
from scipy.stats import laplace_gen

class TextDifferentialPrivacy:
    """Apply differential privacy to text features"""
    
    def __init__(self, epsilon: float = 1.0, delta: float = 1e-6):
        """
        Args:
            epsilon: Privacy budget (smaller = more private)
            delta: Negligible probability of fail
        """
        self.epsilon = epsilon
        self.delta = delta
    
    def perturb_word_frequencies(self, query: str) -> str:
        """
        Add DP noise to word frequencies in query
        
        Approach:
        1. Extract word frequencies from query
        2. Add Laplace noise proportional to epsilon
        3. Reconstruct query from noisy frequencies
        """
        words = query.lower().split()
        word_counts = {}
        for word in words:
            word_counts[word] = word_counts.get(word, 0) + 1
        
        # Add Laplace noise to each word count
        # Sensitivity of count: 1 (adding/removing one word)
        scale = 1.0 / self.epsilon
        
        noisy_counts = {}
        for word, count in word_counts.items():
            noise = laplace_gen.rvs(scale=scale)
            noisy_counts[word] = max(0, int(count + noise))
        
        # Reconstruct query (order randomized)
        reconstructed = []
        for word, count in noisy_counts.items():
            reconstructed.extend([word] * count)
        
        np.random.shuffle(reconstructed)
        return ' '.join(reconstructed)
    
    def perturb_sentence_structure(self, query: str) -> str:
        """
        Add DP noise to sentence structure
        
        Approach:
        1. Extract syntactic features (avg_sentence_length)
        2. Add noise to this feature
        3. Reconstruct with noisy structure
        """
        # This is more complex (requires NLP)
        # Placeholder for research
        pass
    
    def theoretical_privacy_bound(self) -> dict:
        """Return formal privacy guarantees"""
        return {
            "epsilon": self.epsilon,
            "delta": self.delta,
            "guarantee": f"(ε,δ)-differentially private with ε={self.epsilon}, δ={self.delta}",
            "interpretation": "Random words changed by 1/epsilon factor",
        }
```

**Research Questions:**
1. Which text features can be perturbed while preserving utility?
2. What DP noise scales achieve <0.65 stylometric similarity?
3. What epsilon/delta values are necessary?
4. How does DP-perturbed text affect LLM comprehension?
5. Can we parallelize DP computation?

**Experimental Protocol:**
```
1. Design DP mechanisms for 5 text features:
   - Word frequency distribution
   - Sentence length
   - Vocabulary diversity
   - Punctuation patterns
   - Capitalization ratio

2. For each mechanism:
   - Run Exp 5 attack (measure similarity reduction)
   - Measure utility loss (LLM comprehension)
   - Calculate privacy bounds (ε, δ)

3. Optimize for privacy-utility frontier

4. Select best mechanism for production
```

**Timeline:**
- Week 2: Literature review (existing text DP work)
- Week 3: Design mechanisms
- Week 3-4: Run experiments
- Week 4: Analyze results & write technical memo

**Success Criteria:**
- [ ] Formal (ε, δ) privacy proof documented
- [ ] Stylometric similarity < 0.65 at ε=1.0
- [ ] Utility loss < 10% (LLM comprehension)
- [ ] Computational overhead < 100ms per query

**Owner:** Research + Theory  
**Budget:** Research time (40 hours) + external review (~$5K)

---

## Phase 4: LONG-TERM (Weeks 4-6 & Beyond) - Architecture Solutions

### 4A: Multi-Device Profile Support 🔓 ZERO-LINKABLE SOLUTION

**Why This Is Best:** Different devices = different IP, truly unlinkable

```python
# File: core/device_profiles.py

class DeviceProfile:
    """Manage isolated query streams by device"""
    
    def __init__(self, profile_id: str, device_id: str, mode: str):
        self.profile_id = profile_id
        self.device_id = device_id
        self.mode = mode  # "local" or "api" (locked per device)
        self.created_at = datetime.now()
    
    def lock_mode(self):
        """Prevent mode switching on this device"""
        self.mode_locked = True
    
    def get_warning_if_switching(self) -> Optional[str]:
        """Return warning if user tries to switch modes on locked device"""
        if self.mode_locked:
            return (
                f"This device is locked to {self.mode.upper()} mode.\n"
                "To switch modes, use a different device or create a new profile."
            )
        return None

class OrchestrixProfileManager:
    """Manage multiple isolated device profiles"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.profiles = {}
    
    def create_profile(self, mode: str, ip_address: str) -> DeviceProfile:
        """Create new isolated profile for a device"""
        profile = DeviceProfile(
            profile_id=uuid.uuid4(),
            device_id=ip_address,  # Track by IP
            mode=mode
        )
        profile.lock_mode()  # Lock to single mode
        self.profiles[profile.profile_id] = profile
        return profile
    
    def get_query_profile(self, device_ip: str) -> Optional[DeviceProfile]:
        """Get profile for current device, or suggest creating new one"""
        for profile in self.profiles.values():
            if profile.device_id == device_ip:
                return profile
        return None
    
    def suggest_new_profile(self, new_mode: str) -> str:
        """Suggest using different device for new mode"""
        return (
            f"For maximum privacy when using {new_mode.upper()} mode, "
            f"use a different device or create a new Orchestrix profile.\n\n"
            f"Current device is set up for: {self._get_existing_profiles()}"
        )
```

**Feature Benefits:**
- ✅ **Zero linkability:** Different IP addresses = no linking possible
- ✅ **Explicit user choice:** Users decide to separate modes
- ✅ **Best privacy:** Combined with zero-disclosure = two-layer protection
- ✅ **Clear mental model:** "Device A = local mode only"

**User Experience:**
```
User has 2 devices:
├─ Laptop (192.168.1.100) 
│  └─ Profile: LOCAL mode only
│     └─ Locked to: "Research PDFs safely"
│
└─ Desktop (192.168.1.101)
   └─ Profile: API mode only
      └─ Locked to: "Ask questions with Gemini"

Benefit: No stylometric linking possible (different IPs)
```

**Implementation:**
- Week 5: Design UI/UX for multi-profile setup
- Week 5-6: Implement profile management
- Week 6: User testing & refinement

**Owner:** Product + Engineering

---

### 4B: Homomorphic Encryption (Long-term Research)

**Concept:** Encrypt queries before sending to API, process encrypted

**Why Challenging:**
- 100-1000x latency overhead
- Limited FHE libraries for text
- High computational cost

**Status:** Research only, 3-6 month minimum timeline

---

## Summary Decision Matrix

### Choose Based On Timeline & Resources:

| Defense | Linkability Reduction | Implementation Effort | Timeline | Cost | Primary Benefit |
|---------|----------------------|----------------------|----------|------|------------------|
| **Style Normalization** | -18.5% | 4-6 hours | This week | Free | Immediate partial protection |
| **Semantic Paraphrasing** | -40-50% (est) | 20-30 hours | Weeks 2-3 | Low ($0, using Gemini) | Strong style change, preserves intent |
| **Text DP** | -30-60% (est) | 30-40 hours | Weeks 2-4 | Medium ($5K research) | Formal privacy proof |
| **Multi-Device Profiles** | -100% (zero-linkable) | 8-12 hours | Weeks 4-6 | Free | Best user experience, truly unlinkable |
| **Homomorphic Encryption** | -100% (encrypted) | 200+ hours | 3-6 months | High ($50K+) | Strongest but expensive |

---

## Recommended Rollout Strategy

### Week 1 (This Week): Foundation
```
Priority 1:
├─ Update privacy ToS ✅
├─ Add in-app mode-switch warning ✅
├─ Brief support team ✅
└─ Deploy style normalization (opt-in) ✅

Linkability reduction: -18.5%
User impact: Low (documentation only)
```

### Week 2: Research Spin-Up
```
Priority 2:
├─ Start semantic paraphrasing research
├─ Start text DP research
├─ Begin user education campaign
└─ Monitor style normalization adoption

Linkability reduction: Still -18.5% (research ongoing)
```

### Week 3: Semantic Paraphrasing Beta
```
Priority 3:
├─ Complete paraphrasing prototype
├─ Run Exp 5-style evaluation
├─ Release as "Stealth Mode Pro" (beta)
└─ Collect user feedback

Linkability reduction: -40-50% (estimated)
User impact: Medium (extra processing)
```

### Weeks 4-6: Multi-Device Profiles
```
Priority 4:
├─ Launch multi-device profile support
├─ Users can lock devices to single mode
├─ Marketing: "Maximum Privacy Mode"
└─ Deprecate single-profile limitation

Linkability reduction: -100% (zero-linkable)
User impact: High (new UX feature)
```

---

## Success Metrics

### Track These Numbers:

| Metric | Target | Owner | Frequency |
|--------|--------|-------|-----------|
| **Stylometric similarity** | < 0.65 | Research | Weekly |
| **Stealth Mode adoption** | > 30% | Product | Weekly |
| **User satisfaction** | > 4.0/5 | Support | Monthly |
| **Privacy ToS reads** | > 80% | Analytics | One-time |
| **Mode-switch warning dismissals** | < 30% | Analytics | Weekly |
| **Security audit pass** | 100% | Security | Quarterly |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| **Performance degradation** | Medium | Medium | A/B test latency impact, feature flag |
| **User confusion** | Low | Low | Clear documentation + in-app help |
| **Semantic paraphrasing fails intent** | Low | Medium | Validation testing with 100 queries |
| **Text DP noise too aggressive** | Medium | Low | Tuning epsilon values |
| **Users resist multi-device UX** | Medium | Medium | User testing + feedback loops |

---

## Next Action: Team Alignment

### Schedule: Defense Planning Meeting

**Attendees:**
- Security Lead
- Product Manager  
- Engineering Lead (Backend)
- Research Lead
- UX/Product Designer

**Duration:** 2 hours

**Agenda:**
1. **Review Exp 5 (20 min):** Key findings + severity
2. **Review Defense Options (30 min):** Tradeoffs for each
3. **Make Decisions (30 min):** Which defenses + timeline
4. **Assign Resources (20 min):** Owner + timeline for each
5. **Communication Plan (20 min):** How to message to users

**Required Decisions:**
- [ ] **Commit to style normalization?** (Yes/No)
- [ ] **Prioritize semantic paraphrasing or text DP?** (Choice)
- [ ] **Timeline for multi-device profiles?** (Date)
- [ ] **Budget for external security research?** ($K)
- [ ] **Communication strategy?** (Proactive/Reactive)

---

## Files to Share in Meeting

📄 **For Executives:**
- `FINAL_RESEARCH_SUMMARY.md` (ROI perspective)
- This roadmap (action items)

📄 **For Security Team:**
- `EXPERIMENT_5_CRITICAL_BRIEFING.md` (technical details)
- `exp5_stylometry_analysis.md` (formal analysis)

📄 **For Developers:**
- `exp5_stylometry.py` (attack code)
- Proposed code snippets (style_defense.py, etc.)

---

## Success Criteria for Roadmap

✅ **Roadmap is successful if:**
1. Team commits to timeline (meeting decision)
2. Style normalization deployed (by end of week 1)
3. User warnings visible (by end of week 1)
4. Strong defense chosen (semantic paraphrase or text DP by week 2)
5. Multi-device profiles launched (by week 6)
6. Final stylometric similarity < 0.65 (by week 6)
7. Zero security incidents attributed to stylometry (ongoing)

---

**Roadmap Status:** ✅ READY FOR TEAM REVIEW  
**Next Step:** Schedule 2-hour planning meeting  
**Decision Deadline:** End of business tomorrow  

---

Generated: March 21, 2026  
Prepared for: Leadership, Security, Product, Engineering
