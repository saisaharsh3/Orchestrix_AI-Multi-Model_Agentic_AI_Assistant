# Email Regeneration Feature

## How to Get a New Email Response

After the AI generates an email, if you **don't like it**, simply reply with one of these keywords:

### Regenerate Keywords
- `regenerate`
- `again`
- `different`
- `retry`
- `new`
- `try again`
- `regen`

## Example Workflow

### Step 1: Generate Email with AI
```
You: send email to john@example.com use ai saying i have interview tomorrow wish me all the best
Bot: [Generates professional email]
```

### Step 2: Don't Like It? Say Regenerate
```
You: regenerate
Bot: 🔄 New email generated:
    [Different version of the email]
    Reply YES to send, NO to cancel, or say REGENERATE for another version.
```

### Step 3: Keep Going Until Satisfied
```
You: different
Bot: 🔄 New email generated:
    [Another version]
    
You: regenerate again
Bot: 🔄 New email generated:
    [Yet another version]
```

### Step 4: Send When Happy
```
You: yes
Bot: ✅ Email sent to john@example.com
```

## Complete Example with Multiple Regenerations

```
User: send email to alice@company.com use ai about budget review

Bot: Confirm SEND:
     To: alice@company.com
     Subject: Budget Review
     
     Dear Alice,
     I wanted to discuss our upcoming budget review...
     
     Reply YES to send or NO to cancel. Say REGENERATE for a new version.

User: regenerate

Bot: 🔄 New email generated:
     To: alice@company.com
     Subject: Budget Review
     
     Hi Alice,
     I hope this message finds you well. I'd like to schedule a time...
     
     Reply YES to send, NO to cancel, or say REGENERATE for another version.

User: again

Bot: 🔄 New email generated:
     To: alice@company.com
     Subject: Budget Review
     
     Alice,
     Following up on our previous discussion regarding the Q2 budget...
     
     Reply YES to send, NO to cancel, or say REGENERATE for another version.

User: yes

Bot: ✅ Email sent to alice@company.com
```

## Important Notes

- ✅ **Regenerate works with:** AI-generated emails (using "use ai" keyword)
- ❌ **Regenerate does NOT work with:** Manual text emails (without "use ai")
- 💡 **Tip:** Each regeneration creates a different version based on your tone and subject
- 🔄 **No limit:** You can regenerate as many times as you want before sending

## Quick Comparison

### Without "use ai" (Can't Regenerate)
```
You: send email to bob@example.com say hello
Bot: [Uses your exact text "hello"]
You: regenerate
Bot: ℹ️ Regeneration only works with AI-generated emails. Try: 'send email to [recipient] use ai [topic]'
```

### With "use ai" (Can Regenerate)
```
You: send email to bob@example.com use ai saying hello
Bot: [AI generates professional email from "hello"]
You: regenerate
Bot: 🔄 [New version generated]
```

## Supported Email Commands

```
# AI-powered (can regenerate):
send email to name@example.com use ai write about [topic]
email name@example.com use ai professional about [topic]
send mail use ai compose about [topic]

# Manual text (can't regenerate):
send email to name@example.com say [your exact text]
email name@example.com saying [your exact text]
```
