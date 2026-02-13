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
  expected      string   @description("Expected return value as JSON string. For 'Conciseness' tests, this is the max line count as a string, e.g. '10'.")
}

class ProblemSchema {
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
    You are a coding-education curriculum designer for a daily coding challenge app.

    The following themes have been used RECENTLY and must NOT be repeated:
    {{ recent_themes }}

    Pick ONE new theme for the next batch of daily problems.

    Themes can be ANYTHING creative and engaging:
    - Classic algorithm/DS topics: "Two Pointers", "Binary Search", "Graph BFS/DFS",
      "Dynamic Programming", "Sliding Window", "Greedy Algorithms"
    - Real-world scenarios: "Building a Shopping Cart", "Social Network Analysis",
      "File System Operations", "API Rate Limiting"
    - Holiday/seasonal: "Valentine's Day Puzzles", "Spooky Halloween Code",
      "New Year Countdown Challenges"
    - Conceptual: "Thinking in Recursion", "The Art of Caching",
      "Data Cleanup & Validation", "String Wizardry"

    Be creative but keep it relevant to coding practice.
    Respond with ONLY the theme name, nothing else.
    {{ ctx.output_format }}
  "#
}


// ── Function: Generate a Week of Problems ───

function GenerateProblemBatch(
  theme: string,
  count: int,
  existing_titles: string[]
) -> ProblemSchema[] {
  client GeminiFlash

  prompt #"
    You are an expert competitive-programming problem author.
    THEME: {{ theme }}

    Generate exactly {{ count }} problems for this theme.
    Do NOT assign dates — just generate the problems in order.

    DIFFICULTY PROGRESSION:
    - Monday & Tuesday: Easy
    - Wednesday & Thursday: Medium
    - Friday & Saturday: Hard
    - Sunday: Medium (but with a special twist — see below)

    DESCRIPTION RULES:
    1. Follow this exact structure for every description:
       a. **Define the concept** in 1-2 plain sentences. Assume the player
          is an intermediate developer — explain any non-obvious terms.
       b. **State the task**: "Given X, return Y." Be precise about types.
       c. **Clarifying notes** (optional): 1-2 short sentences ONLY if
          there is a subtle constraint the player must know.
       d. **One example** with Input, Output, and a brief Explanation.
    2. Keep it SHORT. No walls of text. No multiple examples.
    3. The example MUST use the same input/output as the FIRST 'Basic'
       test case so the player can verify immediately.
    4. Format the example exactly like this (plain text, no code fences):

       Example:
       Input: nums = [1,3,2,2,5,2,3,7]
       Output: 5

       Explanation: The longest harmonious subsequence is [3,2,2,2,3].

    5. Here are GOOD description styles to emulate:
       - "A harmonious array is an array where the difference between its
         maximum value and its minimum value is exactly 1. Given an integer
         array nums, return the length of its longest harmonious subsequence."
       - "Given an array of characters chars, compress it by replacing
         consecutive repeating characters with the character followed by
         the count. Return the new length of the array. If a character
         appears only once, just keep the character (no count)."

    TEST CASE RULES:
    1. Generate exactly 6 test cases per problem.
    2. The FIRST test case MUST be type='Basic' — this is the example shown
       in the description.
    3. Cases 2-5: Mixed types (Basic, Edge, Logic).
    4. Case 6: ALWAYS type='Conciseness'.
       For this test, 'expected' must be a string of the maximum allowed
       line count (e.g. "10" or "15"). The 'input' should describe what
       the conciseness check evaluates. Do NOT use a separate max_lines field.
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
