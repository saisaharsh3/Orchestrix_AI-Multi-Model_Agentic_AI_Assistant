## Orchestrix AI: Multi-Model Agentic Assistant

Orchestrix AI is a versatile, agentic AI assistant designed to bridge the gap between local LLMs and cloud-based APIs while offering real-time web access, document intelligence (RAG), and browser automation.

Whether you need to chat with a local Ollama model for privacy or use Gemini for complex reasoning, Orchestrix manages the state and tools to get the job done.

## Key Features
- Hybrid Intelligence: Seamlessly toggle between Local LLMs (via Ollama) and Cloud APIs (Gemini) with simple slash commands.

- Smart RAG (Retrieval-Augmented Generation): Load and index PDFs on the fly to chat with your local documents using a vector-based store.

- Web & News Integration: Real-time information gathering through automated web, news, and Wikipedia searches.

- Agentic Browser Automation: Integrated intent detection for:

- YouTube: Open and search videos directly.

- BookMyShow: Multi-step conversational booking flow for movies.

- Email Management: Intent-based email drafting and sending with a confirmation safety loop.

- Multimodal Input: Native support for Voice-to-Text and Text-to-Speech (TTS) for hands-free interaction.

## FactLock System
- A core pillar of Orchestrix AI is the FactLock engine—a specialized agentic layer designed to eliminate hallucinations and ensure every response is anchored in evidence.

- Evidence-Based Grounding: Before a response is delivered, FactLock cross-references generated claims against your indexed PDFs (via RAG) or verified web sources.

- Confidence Scoring: Every output is assigned a "Grounding Score." If the model attempts to "hallucinate" information not found in the source, FactLock triggers a clarification or a "Missing Info" warning.

- Source Attribution: FactLock automatically extracts and links citations, ensuring that every factual assertion can be traced back to its origin in your documents or the web.

## System Architecture
-**Orchestrix is built on a modular "Orchestrator" pattern:**

- Main Entry (main.py): The terminal-based UI and state manager for model selection and voice toggles.

- Orchestrator (core/orchestrator.py): The brain of the system. It routes user input through various "Intent Detectors" (Email, Web, Automation) before deciding whether to use RAG or Web Search.

-Vector Store (rag/vector_store.py): Handles PDF ingestion and semantic search.

-Tooling: A robust suite of tools for web scraping, searching, and automation.
