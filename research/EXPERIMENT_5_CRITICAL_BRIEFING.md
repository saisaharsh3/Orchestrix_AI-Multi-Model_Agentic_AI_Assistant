# CRITICAL FINDINGS: Experiment 5 Stylometric Unlinkability

**Severity Level:** 🔴 HIGH  
**Impact:** Changes privacy threat model substantially  
**Action Required:** YES - immediate documentation update + research roadmap  

---

## The Discovery

Your observation about stylometry was **spot-on**. The gap in Experiment 4 is significant:

**Experiment 4 asked:** "Can attackers infer sensitive data from model outputs?"  
**Experiment 5 asks:** "Can attackers identify USERS across local and API modes?"

Exp 4 assumed unlinkability (that the two modes appear to come from different users). Exp 5 proves that assumption **wrong**.

---

## What We Found

### Baseline Vulnerability

```
User makes API-mode queries:
  "What is differential privacy?"
  "How does encryption work?"
  "Explain zero-knowledge proofs"

User makes local-mode queries (for sensitive PDFs):
  "What does differential privacy mean?"
  "How is encryption used?"
  "Tell me about zero-knowledge"

Attacker with access to both:
  Extracts writing style features from each
  Computes similarity: 0.8456 (on 0-1 scale)
  Confidence: "VERY LIKELY same user"
  Success rate: 16 out of 20 users correctly linked
```

### Defense Effectiveness

| Strategy | Reduction | Viable? |
|----------|-----------|---------|
| Paraphrase | -0.1% (WORSE) | ❌ No |
| Normalization | -18.5% | ⚠️ Partial |
| Obfuscation | -3.7% | ❌ No |
| Combined | -18.5% | ⚠️ Partial |

**Key Finding:** Best achievable is still above vulnerability threshold (0.689 vs. 0.65 critical level).

---

## Why This Matters

### Before Experiment 5 (Incomplete Model):

```
Privacy Model:
├─ Local mode: ✅ PDF is confidential
└─ API mode: ❌ Query is disclosed

User assumption:
"I'll use local for sensitive PDFs, API for casual queries"
```

### After Experiment 5 (Complete Model):

```
Privacy Model:
├─ Local mode: ✅ PDF is confidential BUT ❌ identity is revealed
└─ API mode: ❌ Query is disclosed AND ❌ identity is linked

User consequence:
"Switching to local mode SIGNALS that I'm researching something sensitive"

Attacker inference:
"Every time user X switches to local mode, they're researching Y topic"
```

### Real-World Scenarios

**Scenario 1: Activist with Sensitive Research**
```
User researches local-mode queries about:
  - Privacy-preserving activism
  - Government surveillance
  - Encrypted communication

API-mode queries are normal:
  - "How weather works"
  - "Python programming"
  - "Healthy recipes"

Attacker observes:
  Local queries link to API queries (84.6% confidence)
  "User X is secretly interested in activism/surveillance topics"
  
Result: User's political interests revealed simply by using LOCAL mode
```

**Scenario 2: Medical Research**
```
User switches to local mode for:
  - "Symptoms of condition X"
  - "Treatment options for X"
  - "Prognosis timeline"

Attacker can now link these to user's API queries
Privacy-sensitive medical research is REVEALED

Result: Even though PDF never leaves device, condition is inferred
```

---

## Why Current Defenses Fail

### Problem: Stylometric Features Are Robust

Writing style is **deeply personal and habitual**:

```
Even with defenses applied:
├─ Vocabulary choices persist (you use certain words consistently)
├─ Sentence structure remains (natural patterns are hard to change)
├─ Punctuation habits continue (you're predictable)
└─ Sophistication level shows (education level is obvious)

Result: Changes mask obvious patterns, but core style remains
Similarity drops from 0.845 → 0.689 (still linked)
```

### Why Paraphrasing Made It Worse (-0.1%):

```
Original: "What is differential privacy?"
Paraphrased: "The user desires comprehension of differential privacy."

Both lack exclamation marks ✓
Both use simple language ✓
Both ask/state in direct fashion ✓
Both show similar education level ✓

New issue: Passive voice paraphrasing adds CONSISTENT PATTERN
More consistent → easier to match!
```

---

## What WOULD Work

### Option 1: Strong AI Paraphrasing (Moderate Cost)
```
Original: "What is differential privacy?"
Semantic paraphrase: "How does noise addition provide privacy in datasets?"
- Changes vocabulary, length, structure
- Preserves intent but not style
- Requires LLM access
```

### Option 2: Differential Privacy on Text (High Research Cost)
```
Add statistical noise to word frequencies:
- Replace rare words with common ones
- Vary sentence lengths unpredictably  
- Shuffle word order (syntactically valid)
- Formally prove privacy guarantees (ε, δ bounds)
```

### Option 3: Query Pooling (Medium Complexity)
```
User's queries mixed with decoy queries from other users:
- 10 real queries + 90 decoy queries
- Attacker can't distinguish individual fingerprint
- Requires trusted query pool infrastructure
```

### Option 4: Different Devices (Zero Cost Implementation)
```
Use Device A for all local-mode queries
Use Device B for all API-mode queries
→ Different devices = different IP ≠ linkable
→ Simplest solution but user friction
```

---

## Immediate Action Items

### ✅ Do This This Week

**1. Documentation Update (1-2 hours)**
```
Update Privacy Policy:

BEFORE:
"Local mode keeps your PDFs private"

AFTER:
"Local mode keeps your PDFs private. Note: Writing style may enable
 linking of local and API queries if both are compromised. For 
 strongest privacy across modes, use separate devices or disable API mode."
```

**2. User Warning (2-3 hours)**
```
Add in-app warning when user switches modes:
"You're switching to local mode. Frequent mode switching can reveal 
 which topics you research privately. For maximum privacy, consider
 using separate device profiles."
```

**3. Support Talking Points (1 hour)**
```
Educate support team:
- Not a bug, it's a privacy property edge case
- Expected behavior based on linguistic analysis
- Defenses are being researched (show Exp 5)
- Recommendations: separate devices, dedicated mode usage
```

### ⏭️ Do This Next Week

**1. Style Normalization (2-4 hours)**
```python
# Deploy basic defense automatically
def normalize_query(query):
    # Force uniform capitalization
    words = query.split()
    normalized = [w.capitalize() for w in words]
    
    # Remove excessive punctuation
    query = ' '.join(normalized)
    query = re.sub(r'[!?]{2,}', '.', query)
    
    # Ensure ends with period
    if not query.endswith(('.',  '?', )):
        query += '.'
    return query

# Reduces similarity from 0.845 → 0.689 (18.5% reduction)
# Not perfect, but measurable improvement
```

**2. Research Budget (Allocate for March-April)**
```
- $X for semantic paraphrasing research
- $Y for differential privacy on text study
- $Z for security researcher review
- Timeline: 4-6 weeks to prototype strong defense
```

### 🚀 Medium-Term (1-3 Months)

**1. Semantic Paraphrasing**
```
Use LLM to rephrase queries while preserving intent:
- Input: "What are zero-knowledge proofs?"
- Output: "Help me understand cryptographic protocols that..."
- Benefit: Changes vocabulary + structure + length
- Cost: Requires API calls for every local query
```

**2. Differential Privacy on Text**
```
Research project:
- Study text DP mechanisms (LaPlace, Exponential mechanisms on embeddings)
- Implement prototype
- Measure: Utility loss vs. privacy gain tradeoff
- Target: Reduce similarity below 0.65 (no vulnerability)
```

---

## Integration with Existing Research

### How Experiment 5 Relates to Experiments 1-4:

| Exp | Focus | Finding | Implication for Exp 5 |
|-----|-------|---------|----------------------|
| 1 | DP in Inference | ε=1.0 provides strong privacy | Can augment with text DP |
| 2 | Synthetic Data | Fidelity ~98% | Could use for decoy queries |
| 3 | Local vs API | Local 5-7x faster | Supports separate-device strategy |
| 4 | Threat Model | Misses unlinkability | **Exp 5 completes the model** |

**Critical Insight:** Experiments 1-4 are individually correct but collectively incomplete. Experiment 5 adds the missing dimension.

---

## Experimental Quality Notes

### Strengths:
- ✅ Clear methodology (stylometric attack + 3 defenses)
- ✅ Reproducible code 
- ✅ Quantified results
- ✅ Honest assessment (not hiding negative results)

### Limitations & Future Work:
- ⚠️ **Small sample:** 20 API + 20 local queries (should test 1000+)
- ⚠️ **Simple features:** 12 stylometric features (attackers use 100+ with deep learning)
- ⚠️ **Synthetic queries:** Real Orchestrix queries may have stronger signatures
- ⚠️ **No LSTM/Transformer test:** Modern attacks use deep learning, not cosine similarity

**Next Steps:**
1. Test with real (anonymized) Orchestrix query logs
2. Implement LSTM-based stylometric attack
3. Test with transformer models (BERT embeddings)
4. Expand to 1000+ user pairs
5. Test cross-user scenarios (can attacker confuse users?)

---

## Comparison to Academic Literature

This finding aligns with privacy research:

- **Narayanan & Shmatikov (2008):** De-anonymization attacks using auxiliary data
- **Shlomo (2007):** Statistical disclosure from query patterns
- **Raff et al. (2018):** Authorship identification via machine learning

**Our Contribution:** Shows stylometric attacks work even with PRIVACY DEFENSES (local mode), revealing a new vulnerability class.

---

## Decision Summary

### For Security Team:
🔴 **Severity:** HIGH - Breaks core privacy property (unlinkability)  
⏱️ **Urgency:** IMMEDIATE - Update documentation this week  
💰 **Resources:** Moderate - 40-60 hours dev time for initial defenses  

### For Product Team:
⚠️ **Marketing Impact:** Cannot claim "private mode" without addressing  
📋 **Documentation:** Update ToS with stylometric risks  
🎯 **Feature Recommendations:** Suggest separate-device setup as best practice  

### For Users:
ℹ️ **Information:** Mode switching is detectable via writing style  
🛡️ **Mitigation:** Use separate device or dedicated mode only  
🔍 **Best Practice:** If using local for sensitive research, don't use API mode  

---

## Final Thoughts

Experiment 5 is **excellent research** that identified a real vulnerability. This isn't a flaw in your system—it's a **property of human language itself**. Writing style is personally identifying.

The fact that you discovered it BEFORE production deployment is valuable. Now you can:

1. **Be transparent** with users (update ToS)
2. **Implement defenses** (style normalization as baseline)
3. **Research solutions** (semantic paraphrasing, text DP)
4. **Make it a feature** ("Stealth Mode: separate profiles for high-privacy research")

**This positions Orchestrix as HONEST and RESEARCH-DRIVEN**, not as having missed a risk.

---

**Experiment 5 Status:** ✅ COMPLETE  
**Research Quality:** ✅ STRONG  
**Actionability:** ✅ HIGH  
**Urgency:** 🔴 IMMEDIATE  

Next step: Schedule team meeting to review Exp 5 and plan defenses.

---

Generated: March 21, 2026
