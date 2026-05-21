# Email Regeneration with Context/Feedback

## Overview
When regenerating AI emails, you can now add **additional instructions or context** to guide the AI better. Instead of just requesting a new version, you can clarify what you want changed or added.

## How It Works

### Without Context (Simple Regeneration)
```
You: send email to john@example.com use ai about interview

Bot: [Generates professional email]

You: regenerate

Bot: 🔄 New email generated: [Different version]
```

### With Context (Guided Regeneration)  
```
You: send email to john@example.com use ai about interview

Bot: [Generates professional email, but it sounds generic]

You: regenerate - this is MY interview, not someone else's

Bot: 🔄 New email generated: [More personal version addressing your specific situation]
    📝 Feedback applied: this is MY interview, not someone else's
```

## Syntax Options

You can use any of these separators after the regenerate keyword:

| Separator | Example |
|-----------|---------|
| Dash `-` | `regenerate - add more enthusiasm` |
| Colon `:` | `regenerate: keep it brief` |
| Comma `,` | `regenerate, mention my experience` |
| No separator | `regenerate add technical skills` |

## Example Scenarios

### Scenario 1: Fix Generic Content
```
You: send email to alice@company.com use ai about quarterly meeting

Bot: [Generates:] "I am writing to discuss our upcoming quarterly meeting..."

You: regenerate - this is MY meeting, I should be greeting Alice, not vice versa

Bot: 🔄 New email generated:
    📝 Feedback applied: this is MY meeting, I should be greeting Alice, not vice versa
    
    [New version:] "Hi Alice, I wanted to reach out about our quarterly meeting..."
```

### Scenario 2: Add Specific Information
```
You: send email to bob@company.com use ai about project update

Bot: [Generic project update email]

You: regenerate - mention the 3 main deliverables: API, UI, and documentation

Bot: 🔄 New email generated:
    📝 Feedback applied: mention the 3 main deliverables: API, UI, and documentation
    
    [New version covers all three deliverables]
```

### Scenario 3: Adjust Tone
```
You: send email to manager@example.com use ai about deadline extension

Bot: [Formal, pleading tone]

You: regenerate - make it more confident, we have good reasons for the extension

Bot: 🔄 New email generated:
    📝 Feedback applied: make it more confident, we have good reasons for the extension
    
    [New version sounds more professional and assured]
```

### Scenario 4: Multiple Refinements
```
You: send email to recruiter@company.com use ai about job application

Bot: [Initial email generated]

You: regenerate - keep it shorter, just 2 paragraphs

Bot: 🔄 New email generated (shorter version)

You: regenerate - add a sentence about my passion for the role

Bot: 🔄 New email generated (shorter with passion statement)

You: regenerate - make it more formal

Bot: 🔄 New email generated (shorter, passionate, formal)

You: yes

Bot: ✅ Email sent
```

## Feedback Examples

| Issue | Feedback Command |
|-------|------------------|
| Generic/Impersonal | `regenerate - this is MY situation, make it personal` |
| Wrong Tone | `regenerate - too formal, keep it friendly` |
| Missing Info | `regenerate - add my 5 years of experience` |
| Too Long | `regenerate - keep it brief, 2-3 paragraphs max` |
| Too Short | `regenerate - expand with more details` |
| Wrong Focus | `regenerate - focus on my achievements not apologies` |
| Needs Emphasis | `regenerate - emphasize the urgency of this deadline` |
| Wrong Perspective | `regenerate - I should be asking them, not vice versa` |

## Supported Regeneration Keywords

You can use any of these keywords with context:
- `regenerate`
- `again`
- `different`
- `retry`
- `new`
- `regen`
- `try again`
- `again please`

**Examples:**
```
regenerate - add more enthusiasm
again - keep it brief
different: mention my background
retry, be more professional
new - make it personal
```

## Complete Workflow Example

```
👤 You: send email to sarah@startup.com use ai saying i want to work with your innovative team

⏳ Bot: Thinking...

📧 Bot: Confirm SEND:
        To: sarah@startup.com
        Subject: (no subject)
        
        Dear Sarah,
        I am writing to express my strong interest in working with your innovative team...
        
        Reply YES to send or NO to cancel. REGENERATE or REGENERATE [feedback] for a new version.

😞 You: regenerate - this sounds like a generic job email, make it personal about THEIR company

⏳ Bot: Thinking...

🔄 Bot: New email generated:
        📝 Feedback applied: this sounds like a generic job email, make it personal about THEIR company
        
        Hi Sarah,
        I've been following your company's work on AI-driven automation, and I'm genuinely excited about the direction...
        
        Reply YES to send, NO to cancel, or REGENERATE with more feedback for another version.

😊 You: regenerate - add that I have 3 years of machine learning experience

⏳ Bot: Thinking...

🔄 Bot: New email generated:
        📝 Feedback applied: add that I have 3 years of machine learning experience
        
        Hi Sarah,
        I've been following your company's work on AI-driven automation, and I'm genuinely excited about the direction...
        With 3 years of machine learning experience, I believe I can contribute significantly to your team's projects...
        
        Reply YES to send, NO to cancel, or REGENERATE with more feedback for another version.

✅ You: yes

✅ Bot: Email sent to sarah@startup.com
```

## Key Features

✅ **Guided Regeneration** - Provide specific feedback to improve content
✅ **Multiple Refinements** - Keep regenerating until it's perfect
✅ **Flexible Syntax** - Use dashes, colons, or just space as separators
✅ **Smart Parsing** - Feedback extracted and shown in confirmation
✅ **Context Awareness** - AI understands your specific situation, not generic scenario
✅ **No Limit** - Regenerate as many times as needed

## Tips & Tricks

### ✅ Good Feedback (Specific)
```
regenerate - make it clear this is MY interview, not asking someone else
regenerate - emphasize my experience with Python and cloud services
regenerate - focus on what value I bring, not what I'm asking for
```

### ❌ Vague Feedback (Less Effective)
```
regenerate - make it better
regenerate - different
regenerate - improve it
```

### 💡 Pro Tip: Be Descriptive
Instead of: `regenerate - tone it down`
Better: `regenerate - tone it down but keep confidence, too nervous sounds weak`

## What Happens Behind the Scenes

1. **Initial Generation**: `send email to [recipient] use ai [topic]`
   - System creates a prompt and LLM generates email

2. **Context Extraction**: `regenerate - [your feedback]`
   - System extracts your feedback after the keyword
   - Shows `📝 Feedback applied: [your feedback]`

3. **Enhanced Prompt**: 
   - Original context + your feedback sent to LLM
   - LLM generates new version incorporating your feedback

4. **Display**: Shows the new email with feedback noted

## Limitations

- ⚠️ Only works with **AI-generated emails** (using `use ai` keyword)
- ⚠️ Manual text emails cannot be regenerated
- ⚠️ Each regeneration costs API calls (uses Gemini/API)

## Related Commands

```
# Generate with AI
send email to [email] use ai [topic]

# Regenerate without feedback
regenerate

# Regenerate with feedback
regenerate - [your feedback]

# Cancel current draft
no / cancel

# Send confirmed email
yes / send / confirm
```
