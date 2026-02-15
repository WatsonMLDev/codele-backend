// ─────────────────────────────────────────────
// Codele — BAML Client Configuration
// ─────────────────────────────────────────────

// Generator: tells baml-cli where to output the Python client
generator target {
  output_type "python/pydantic"
  output_dir  "../baml_client"
  version     "0.218.1"
  default_client_mode "sync"
}

// Gemini client via Google AI (fast & cheap)
client<llm> GeminiFlash {
  provider "google-ai"
  options {
    model "gemini-3-flash-preview"
    api_key env.GOOGLE_API_KEY
    generationConfig {
      temperature 0.7
      maxOutputTokens 8192
    }
  }
}
