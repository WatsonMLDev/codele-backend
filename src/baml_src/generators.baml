// ─────────────────────────────────────────────
// Codele — BAML AI Agent Definitions
// ─────────────────────────────────────────────

// ── Data Types (Matches Frontend Schema) ────

enum TestCaseType {
  Basic
  Edge
  Logic
  Conciseness
}

class TestCaseSchema {
  type          TestCaseType @description("Category of the test case")
  hint          string   @description("A helpful hint shown to the user if they fail this case")
  input         string   @description("Input arguments as a JSON string, e.g. '[1, 2]'")
  expected      string   @description("Expected return value as a JSON string, e.g. '3'")

  // For the 'conciseness' type only
  max_lines     int?     @description("Max lines allowed (only if type is 'conciseness')")
}

class ProblemSchema {
  id            string   @description("Date in YYYY-MM-DD format for this problem")
  title         string   @description("Short, catchy problem title")
  difficulty    string   @description("One of: Easy, Medium, Hard")
  description   string   @description("Full problem statement in Markdown")
  starter_code  string   @description("Python function signature and boilerplate")
  test_cases    TestCaseSchema[] @description("Exactly 6 test cases for this problem")
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
    THEME: {{ theme }}
    START DATE (Monday): {{ start_date }}

    Generate exactly 7 problems, one per day (Monday through Sunday).
    Assign consecutive dates starting from the start_date (YYYY-MM-DD).

    DIFFICULTY PROGRESSION:
    - Monday & Tuesday: Easy
    - Wednesday & Thursday: Medium
    - Friday & Saturday: Hard
    - Sunday: Medium (but with a special twist — see below)

    DESCRIPTION RULES:
    1. Keep descriptions concise and well-structured in Markdown.
    2. Include exactly 1 example (MAX 2 if the problem truly requires it).
    3. The example MUST use the same input/output as the FIRST 'Basic' test case.
       This way the player can verify their approach immediately.
    4. Format examples as:
       ```
       Input: <input>
       Output: <output>
       ```

    TEST CASE RULES:
    1. Generate exactly 6 test cases per problem.
    2. The FIRST test case MUST be type='Basic' — this is the example shown
       in the description.
    3. Cases 2-5: Mixed types (Basic, Edge, Logic).
    4. Case 6: ALWAYS type='Conciseness' with a 'max_lines' limit.
       This challenges the player to write the shortest possible solution.
    5. 'hint': Short, actionable debugging hint
       (e.g., "Check how you handle empty arrays").
    6. 'input': JSON string of the input arguments.
    7. 'expected': JSON string of the expected return value.

    CODE RULES:
    1. 'starter_code': Must be valid Python with a function signature and docstring.

    NEGATIVE RAG — These titles already exist and MUST NOT be reused:
    {{ existing_titles }}

    For each problem provide:
    - A unique, creative title (not in the existing_titles list)
    - A concise Markdown description with 1 example (see rules above)
    - Starter code in Python
    - Exactly 6 test cases
    - Relevant topic tags

    {{ ctx.output_format }}
  "#
}
