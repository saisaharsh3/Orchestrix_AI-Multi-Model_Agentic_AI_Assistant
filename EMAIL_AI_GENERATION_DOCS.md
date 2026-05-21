# AI Email Generation Feature

## Overview
Users can now request the AI to automatically generate professional email content by using the **"use ai"** keyword. When detected, the system generates a complete, ready-to-send email body based on the provided context instead of using raw user text.

## How It Works

### Without "use ai" (Original Behavior)
```
User: send email to john@example.com say hello how are you
Bot displays confirmation with email body: "hello how are you"
```

### With "use ai" (New Behavior)
```
User: send email to john@example.com use ai write about project deadline
Bot generates AI-powered professional email about project deadline
Bot displays confirmation with professionally written email body
```

## Supported Keywords
The system detects any of these variations:
- `use ai`
- `use ai to write`
- `ai write`
- `ai generate`
- `let ai write`
- `have ai write`
- `let ai compose`
- `have ai compose`
- `ai compose`
- `ai write about`

## Usage Examples

### Example 1: Simple AI Generation
```
User: send email to alice@example.com use ai write about quarterly meeting
Bot Result: AI generates professional email about the quarterly meeting
```

### Example 2: With Tone Specified
```
User: send email to bob@company.com use ai casual about catching up
Bot Result: AI generates friendly email in casual tone
```

### Example 3: Complex Topic
```
User: email team@department.com use ai professional about budget review and next steps
Bot Result: AI generates well-structured formal email covering budget review and next steps
```

### Example 4: Without AI (Original)
```
User: send email to john@example.com saying thanks for your help
Bot Result: Email body contains exactly: "thanks for your help"
```

## Technical Implementation

### Files Modified

**1. `tools/email_intent.py`**
- Added `AI_GENERATION_TRIGGERS` constant with all supported keyword variations
- Added `should_use_ai_generation(text: str) -> bool` function to detect AI generation request
- Added `use_ai` flag to `extract_email_fields()` result dictionary
- Cleans AI keywords from text before extraction to prevent interference with subject/body detection

**2. `core/orchestrator.py`**
- Updated email composition logic to check `use_ai` flag from extracted fields
- When `use_ai=True`: Always generates content via `build_email_body()` + LLM
- When `use_ai=False`: Uses existing logic (short body expansion or raw text)

### Workflow

```
User Input
    ↓
detect_email_intent() → Returns "send"
    ↓
extract_email_fields()
    ├─ should_use_ai_generation() → Checks for AI keywords
    ├─ Removes AI keywords from text
    ├─ Extracts: to, subject, body, tone
    └─ Adds: use_ai flag
    ↓
Check use_ai flag in orchestrator
    ├─ If TRUE → Call build_email_body() + generate_llm()
    └─ If FALSE → Use raw body text
    ↓
Display confirmation with AI-generated or raw content
    ↓
User confirms YES/NO
    ↓
Send email (if YES)
```

## Tone Support
Email tone is automatically detected from context. Supported tones:
- **professional** (default)
- **formal** (triggered by: formal, professional, official)
- **casual** (triggered by: friendly, casual, informal, warm)
- **urgent** (triggered by: urgent, asap, immediately, critical)
- **polite** (triggered by: polite, kind, gentle)

## Examples in Context

### Professional Tone (Auto-detected)
```
Input: send email to manager@company.com use ai write about project completion
Output: 
  Dear [Name],
  
  I wanted to inform you that the project has been successfully completed...
  
  Best regards,
  [Your Name]
```

### Casual Tone
```
Input: send email to friend@mail.com use ai friendly about weekend plans
Output:
  Hey [Name],
  
  Hope you're doing well! I was thinking about our weekend plans...
  
  Talk soon!
  [Your Name]
```

## Backward Compatibility
- Existing email commands WITHOUT "use ai" work exactly as before
- No breaking changes to current email functionality
- Users can still send raw text by omitting "use ai"

## Testing
A comprehensive test suite (`test_email_ai_generation.py`) validates:
- ✓ "use ai" keyword detection in various forms
- ✓ Email field extraction with use_ai flag
- ✓ Email intent detection still works
- ✓ Subject and body extraction not affected
- ✓ All 10+ keyword variations recognized

**All tests passing!** ✅

## Error Handling
- If recipient email not provided: Bot asks for recipient
- If both subject and body missing: Bot asks for message content
- If AI generation fails: Falls back to raw text (graceful degradation)

## Future Enhancements
1. Cache generated emails for quick resend
2. Email templates for common scenarios
3. Signature insertion
4. Attachment handling with AI context
5. Email scheduling
