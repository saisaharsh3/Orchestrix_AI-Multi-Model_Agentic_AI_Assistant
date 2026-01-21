import ollama

def local_generate(prompt):
    res = ollama.chat(
        model="llama3:8b-instruct-q4_K_M",
        messages=[{"role": "user", "content": prompt}]
    )
    return res["message"]["content"]
