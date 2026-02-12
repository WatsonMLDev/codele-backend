// ─────────────────────────────────────────────
// Codele — BAML AI Agent Definitions
// ─────────────────────────────────────────────

// ── Data Types ──────────────────────────────

class TestCaseSchema {
  input         string   @description("Input to pass to the solution function")
  expected_output string @description("Expected output from the solution")
  is_conciseness_check bool @description("True only for the Sunday conciseness test case")
  max_lines     int?     @description("Max allowed lines (only when is_conciseness_check is true)")
}

class ProblemSchema {
  id            string   @description("Date in YYYY-MM-DD format for this problem")
  title         string   @description("Short, catchy problem title")
  difficulty    string   @description("One of: Easy, Medium, Hard")
  description   string   @description("Full problem statement in Markdown")
  starter_code  string   @description("Boilerplate code given to the player")
  test_cases    TestCaseSchema[] @description("3-5 test cases for this problem")
  topics        string[] @description("Relevant topic tags")
}


// ── Function: Pick a Weekly Theme ───────────

function PickWeeklyTheme(recent_themes: string[]) -> string {
  client GeminiFlash

  prompt #"
    You are a coding-education curriculum designer.

    The following coding topics have been used RECENTLY and must NOT be repeated:
    {{ recent_themes }}

    Pick ONE new coding topic for this week's daily problems.
    The topic should be a well-known algorithmic or data-structure concept
    (e.g. "Two Pointers", "Binary Search", "Graph BFS/DFS", "Dynamic Programming",
    "Sliding Window", "Greedy Algorithms", "Backtracking", "Trie", "Union Find",
    "Monotonic Stack", "Bit Manipulation", "Topological Sort").

    Respond with ONLY the topic name, nothing else.
    {{ ctx.output_format }}
  "#
}


// ── Function: Generate a Week of Problems ───

function GenerateProblemBatch(
  theme: string,
  start_date: string,
  existing_titles: string[]
) -> ProblemSchema[] {
  client GeminiFlash

  prompt #"
    You are an expert competitive-programming problem author.

    THEME for this week: {{ theme }}
    START DATE (Monday): {{ start_date }}
    Generate exactly 7 problems, one per day (Monday through Sunday).
    Assign consecutive dates starting from the start_date (YYYY-MM-DD).

    DIFFICULTY PROGRESSION:
    - Monday & Tuesday: Easy
    - Wednesday & Thursday: Medium
    - Friday & Saturday: Hard
    - Sunday: Medium (but with a special twist — see below)

    SUNDAY SPECIAL RULE:
    The 7th problem (Sunday) MUST include a "Conciseness" test case.
    Instead of a performance check, set ONE test case with:
      is_conciseness_check = true
      max_lines = <a reasonable limit, e.g. 10-15>
    This challenges the player to write the shortest possible solution.

    NEGATIVE RAG — These titles already exist and MUST NOT be reused:
    {{ existing_titles }}

    For each problem provide:
    - A unique, creative title (not in the existing_titles list)
    - A clear Markdown description with examples
    - Starter code in Python with a function signature and docstring
    - 3-5 test cases with input/output pairs
    - Relevant topic tags

    {{ ctx.output_format }}
  "#
}
