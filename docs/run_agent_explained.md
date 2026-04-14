# Understanding the `run_agent` Function: A Step-by-Step Guide

This document walks you through the `run_agent` function from Session 3 — the
core "agent loop" that lets Claude autonomously query a FHIR server to answer
your clinical questions. Every section explains one piece of the code in plain
English, then shows you the corresponding code with inline comments.

---

## 1. What Is an Agent?

When you make a single API call to an LLM like Claude, you send a prompt and get
back one response. That's great for answering questions from the model's own
knowledge, but it can't **do** anything — it can't look up data, call APIs, or
run code.

An **agent** solves this by putting the LLM in a loop:

1. You ask a question.
2. The LLM decides it needs to call a tool (like searching a database).
3. Your code executes that tool and sends the result back to the LLM.
4. The LLM either calls another tool or gives you a final answer.

This loop continues until the LLM has enough information to answer, or until a
safety limit is reached. The key insight is that **the LLM decides which tools
to call and in what order** — you don't have to write that logic yourself.

---

## 2. Function Signature — The Inputs

```python
def run_agent(question, system_prompt=SYSTEM_PROMPT, tools=tools,
              available_functions=available_functions, max_steps=25):
    """Run the tool-use agent loop."""
```

| Parameter             | What it is                                                                                       | Default                |
|-----------------------|--------------------------------------------------------------------------------------------------|------------------------|
| `question`            | The clinical question you want answered (a plain-English string).                                | *(required)*           |
| `system_prompt`       | Instructions that tell Claude what it is, what data is available, and how to behave.             | `SYSTEM_PROMPT`        |
| `tools`               | The list of tool **schemas** — JSON descriptions of each tool that Claude can see and choose from. | `tools`              |
| `available_functions` | A Python dictionary mapping tool names (strings) to actual Python functions your code can call.  | `available_functions`  |
| `max_steps`           | A safety limit — the maximum number of loop iterations before the agent is forced to stop.       | `25`                   |

**Why separate `tools` and `available_functions`?** Claude sees the `tools`
schemas (JSON descriptions of what each tool does and what arguments it takes).
Your Python code uses `available_functions` to actually *execute* those tools.
They need to match up — every name in `tools` should have a corresponding entry
in `available_functions`.

---

## 3. Initialization — Setting Up the Loop

```python
    # Print the question so you can see what the agent is working on
    print(f"\U0001f916 AGENT QUESTION: {question}\n")
    print("=" * 70)

    # Start the conversation with the user's question
    messages = [{"role": "user", "content": question}]

    # Keep a log of every tool call the agent makes (for analysis later)
    tool_calls_log = []

    # Count how many times we've gone through the loop
    step = 0
```

Three things are set up before the loop begins:

- **`messages`** — A list that holds the entire conversation history. It starts
  with just the user's question. As the loop runs, assistant responses and tool
  results get appended here. This is how Claude "remembers" what it has already
  done — every API call sends the full conversation so far.

- **`tool_calls_log`** — A simple list that records which tools were called and
  with what arguments. This isn't used by the agent itself — it's for *you* to
  inspect afterward (the "tool call trace" you see in the notebook).

- **`step`** — A counter that tracks how many loop iterations have occurred, so
  we can enforce the `max_steps` safety limit.

---

## 4. The Loop — Why `while` with a Step Limit?

```python
    while step < max_steps:
        step += 1
```

The agent uses a `while` loop instead of a `for` loop because **we don't know
in advance how many steps the agent will need**. A simple question might take
3 steps; a complex comparison might take 15.

The `max_steps` guard ensures the loop always terminates. Without it, a confused
model could keep calling tools forever (and running up your API bill). The
default of 25 is generous — most questions finish in 5-15 steps.

---

## 5. Calling Claude — The API Request

```python
        response = client.messages.create(
            model=MODEL,                    # Which Claude model to use
            max_tokens=4096,                # Maximum length of Claude's response
            system=system_prompt,           # The system instructions
            tools=tools,                    # The tool schemas Claude can choose from
            messages=messages,              # The full conversation history so far
        )
```

Each iteration of the loop makes one API call to Claude. Notice that we send the
**entire `messages` list** every time. This is how Claude knows:

- What the original question was
- Which tools it has already called
- What results those tools returned

Claude reads all of this and decides what to do next: call another tool, or give
a final answer.

The response comes back as an object with a `content` list. Each item in
`content` is a "block" — either a **text block** (Claude's words) or a
**tool_use block** (Claude requesting that we call a specific tool).

---

## 6. Checking for Tool Use — Is Claude Done?

```python
        # Filter response blocks to find any tool_use requests
        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

        if not tool_use_blocks:
            # No tool calls — Claude is giving its final answer
```

This is the key decision point. After each API call, we check: **did Claude ask
to use any tools?**

- **If no** → Claude has enough information and is providing a final text answer.
  We extract that text and return it (see next section).
- **If yes** → Claude wants to call one or more tools. We need to execute them
  and feed the results back (see sections 8-10).

---

## 7. Extracting the Final Answer — The Exit Condition

```python
        if not tool_use_blocks:
            # No tool calls means Claude is done — extract the text answer
            final_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    final_text += block.text

            print(f"\n{'=' * 70}")
            print(f"\u2705 FINAL ANSWER (after {step} steps):\n")
            print(final_text)

            # Return three things:
            #   1. The answer text
            #   2. The log of all tool calls made
            #   3. The full message history
            return final_text, tool_calls_log, messages
```

When Claude decides it's done, it sends back only text blocks (no `tool_use`
blocks). We concatenate all the text blocks into `final_text` and return it.

The function returns three values:

1. **`final_text`** — The answer to your question.
2. **`tool_calls_log`** — A record of every tool call, useful for understanding
   the agent's strategy.
3. **`messages`** — The complete conversation history, useful for debugging.

---

## 8. Recording the Assistant's Response — Conversation Memory

```python
        # Serialize assistant content for message history
        assistant_content = []
        for block in response.content:
            if block.type == "text":
                assistant_content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                assistant_content.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })
        messages.append({"role": "assistant", "content": assistant_content})
```

Before we execute the tools Claude requested, we need to record Claude's
response in the `messages` list. This is crucial for the conversation to make
sense on the next iteration.

**Why serialize?** The API returns Python objects (with attributes like
`block.text`), but the `messages` list needs plain dictionaries. This loop
converts each block into a dictionary with the right format.

**Why include tool_use blocks?** When we send tool results back to Claude in the
next step, Claude needs to see its own tool requests to understand which results
correspond to which requests. Each tool_use block has a unique `id` that links
it to its result.

---

## 9. Executing Tool Calls — Running the Actual Functions

```python
        # Execute each tool call
        tool_results = []
        for block in tool_use_blocks:
            fn_name = block.name       # e.g., "search_conditions"
            fn_args = block.input      # e.g., {"code": "44054006", "max_results": 50}

            # Print what's happening so you can follow along
            args_str = ", ".join(f"{k}={v!r}" for k, v in fn_args.items())
            print(f"\U0001f527 Step {step}: {fn_name}({args_str})")

            # Log the call for later analysis
            tool_calls_log.append({
                "step": step,
                "function": fn_name,
                "arguments": fn_args,
            })

            # Look up the actual Python function and call it
            try:
                result = available_functions[fn_name](**fn_args)
            except Exception as e:
                result = {"error": str(e)}

            # Package the result for Claude
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,       # Links this result to Claude's request
                "content": json.dumps(result, default=str),  # Convert to JSON string
            })
```

This is where the "agent" part really happens. For each tool Claude requested:

1. **Extract the function name and arguments** from Claude's response. Claude
   chose these based on the tool schemas you provided.

2. **Look up the real Python function** in `available_functions`. For example,
   if `fn_name` is `"search_conditions"`, this retrieves the `search_conditions`
   function you defined earlier.

3. **Call the function** with `**fn_args` (keyword argument unpacking). The
   `try/except` catches any errors (like network timeouts) so the agent can keep
   going rather than crashing.

4. **Package the result** as a `tool_result` dictionary. The `tool_use_id` field
   links this result back to the specific tool_use request from Claude, so
   Claude knows which result goes with which request.

---

## 10. Feeding Results Back — The `tool_result` Message

```python
        messages.append({"role": "user", "content": tool_results})
```

This single line is easy to miss, but it's essential. After executing all the
tool calls, we add the results to the `messages` list as a **"user" role
message**.

**Why "user" and not "tool" or "system"?** This is how the Anthropic API is
designed. Tool results are sent as user messages with a special `tool_result`
content type. Claude knows to interpret these as tool outputs, not as something
the human typed.

After this line, the loop goes back to Step 5 — Claude receives the full
conversation (including the tool results we just added) and decides what to
do next.

---

## 11. Safety Valve — The `max_steps` Guard

```python
    # This runs only if the while loop exits without returning
    print(f"\n\u26a0\ufe0f Reached max steps ({max_steps})")
    return "Agent reached step limit.", tool_calls_log, messages
```

If the loop runs `max_steps` times without Claude giving a final answer, we
stop and return a warning. This prevents:

- **Infinite loops** from confused models
- **Excessive API costs** from runaway agents
- **Long waits** during class time

The default limit of 25 steps is rarely hit in practice. If you see this
warning, the question may be too broad, or the agent may be stuck in a
pattern (calling the same tool repeatedly without making progress).

---

## 12. Visual Summary — The Agent Loop

```
  ┌──────────────────────────────────────────────────────────────┐
  │                     YOUR QUESTION                            │
  │           "Compare HbA1c between Type 1 and Type 2"          │
  └──────────────────────────┬───────────────────────────────────┘
                             │
                             ▼
              ┌──────────────────────────┐
              │   messages = [question]  │
              │   step = 0               │
              └────────────┬─────────────┘
                           │
          ┌────────────────▼────────────────┐
          │                                 │
          │    step < max_steps?             │
          │                                 │◄──────────────────────┐
          └────────────┬────────────────────┘                      │
                  yes  │                                           │
                       ▼                                           │
          ┌────────────────────────────┐                           │
          │  Call Claude API with      │                           │
          │  full messages history     │                           │
          └────────────┬───────────────┘                           │
                       │                                           │
                       ▼                                           │
          ┌────────────────────────────┐                           │
          │  Any tool_use blocks       │                           │
          │  in response?              │                           │
          └──────┬───────────┬─────────┘                           │
                 │           │                                     │
             no  │       yes │                                     │
                 │           ▼                                     │
                 │  ┌────────────────────────┐                     │
                 │  │ Record assistant       │                     │
                 │  │ response in messages   │                     │
                 │  └───────────┬────────────┘                     │
                 │              │                                  │
                 │              ▼                                  │
                 │  ┌────────────────────────┐                     │
                 │  │ Execute each tool call │                     │
                 │  │ (Python functions)     │                     │
                 │  └───────────┬────────────┘                     │
                 │              │                                  │
                 │              ▼                                  │
                 │  ┌────────────────────────┐                     │
                 │  │ Append tool_results    │                     │
                 │  │ to messages            │─────────────────────┘
                 │  └────────────────────────┘
                 │
                 ▼
          ┌────────────────────────────┐
          │  Extract text answer       │
          │  Return (answer, log,      │
          │         messages)          │
          └────────────────────────────┘
```

**The loop in one sentence:** Send Claude the conversation so far, check if it
wants to call tools, execute those tools and add the results to the
conversation, then repeat — until Claude responds with just text (the final
answer) or the step limit is reached.

---

## 13. Understanding the Two Roles: "assistant" vs "user"

The `messages` list is a strict back-and-forth between two roles:

- **`"role": "assistant"`** — Claude's turns. Everything Claude says or requests
  (its thinking-out-loud text *and* its tool call requests) is recorded under
  this role.

- **`"role": "user"`** — everything that isn't Claude. This includes the human's
  original question *and* tool results from your Python code.

That second part is the unintuitive bit. Tool results don't come from a human —
they come from your code calling `search_conditions` or `get_patient`. But the
Anthropic API doesn't have a third "tool" role. It models conversation as a
strict alternation: user → assistant → user → assistant → ... So tool results
get sent as `"role": "user"` messages with a special `"type": "tool_result"` tag
that tells Claude "this is data from a tool you called, not something the human
typed."

Here's what the alternation looks like in practice:

```
messages[0]  role: user       ← The human's question
messages[1]  role: assistant  ← Claude says "I'll search for conditions" + tool_use request
messages[2]  role: user       ← Tool result from search_conditions (not the human!)
messages[3]  role: assistant  ← Claude says "Now let me get that patient" + tool_use request
messages[4]  role: user       ← Tool result from get_patient (not the human!)
messages[5]  role: assistant  ← Claude's final text answer
```

Only `messages[0]` was actually typed by a human. Every other "user" message is
your code feeding tool results back to Claude. Claude can tell the difference
because real human messages have plain string content, while tool results have
the `"type": "tool_result"` structure with a `tool_use_id` that links back to
the specific tool request.

---

## 14. Worked Example — "Find a Type 2 diabetes patient and check their HbA1c"

Let's trace through a real run. The question is simple enough that it finishes
in **4 steps**: three tool calls, then a final answer. We'll show exactly what
the `messages` list looks like at each point.

**The question:**

```
"Find a patient with Type 2 diabetes and tell me their most recent HbA1c."
```

### Before the loop

```python
messages = [
    {"role": "user", "content": "Find a patient with Type 2 diabetes and tell me their most recent HbA1c."}
]
step = 0
```

One message. Claude hasn't seen it yet.

---

### Step 1 — Claude calls `search_conditions`

We send `messages` to the API. Claude reads the question, decides it needs to
find Type 2 diabetes patients, and responds with a `tool_use` block:

```
Claude's response:
  [text]    "I'll start by searching for patients with Type 2 diabetes."
  [tool_use] id="toolu_01A", name="search_conditions", input={"code": "44054006"}
```

**No final answer yet** (there's a `tool_use` block), so we:

1. **Record the assistant's response** in messages (Section 8):

```python
messages = [
    {"role": "user", "content": "Find a patient with Type 2 diabetes..."},
    {"role": "assistant", "content": [
        {"type": "text", "text": "I'll start by searching for patients with Type 2 diabetes."},
        {"type": "tool_use", "id": "toolu_01A", "name": "search_conditions",
         "input": {"code": "44054006"}}
    ]}
]
```

2. **Execute the tool** — call `search_conditions(code="44054006")`. The FHIR
   server returns 632 matching conditions. The first result includes
   `patient_reference: "Patient/19c64d7ed3e-9d367f0d-2a6e-4055-85d5-5080b2a5d1a8"`.

3. **Feed the result back**:

```python
messages = [
    {"role": "user", "content": "Find a patient with Type 2 diabetes..."},
    {"role": "assistant", "content": [...]},       # Claude's tool request
    {"role": "user", "content": [                   # Tool result (note: "user" role!)
        {"type": "tool_result", "tool_use_id": "toolu_01A",
         "content": "{\"total\": 632, \"results\": [{\"code\": \"44054006\", \"display\": \"Type 2 diabetes mellitus\", \"patient_reference\": \"Patient/19c64d7ed3e-...\", ...}]}"}
    ]}
]
```

Three messages now. Back to the top of the loop.

---

### Step 2 — Claude calls `get_patient`

Claude sees the search results and picks a patient ID to look up:

```
Claude's response:
  [tool_use] id="toolu_02B", name="get_patient",
             input={"patient_id": "19c64d7ed3e-9d367f0d-2a6e-4055-85d5-5080b2a5d1a8"}
```

We record, execute, and feed back. The function returns:

```json
{"id": "19c64d7ed3e-...", "name": "Patient Synthetic5", "gender": "female", "birthDate": "1972-05-05"}
```

Messages list now has **5 entries** (original question, assistant, tool result,
assistant, tool result).

---

### Step 3 — Claude calls `search_observations`

Claude now knows the patient. It needs their HbA1c:

```
Claude's response:
  [tool_use] id="toolu_03C", name="search_observations",
             input={"patient_id": "19c64d7ed3e-...", "loinc_code": "4548-4"}
```

We execute `search_observations(...)`. The FHIR server returns:

```json
{"total": 1, "results": [{"code": "4548-4", "display": "Hemoglobin A1c",
  "value": 6.72, "unit": "%", "date": "2026-02-01"}]}
```

Messages list: **7 entries**.

---

### Step 4 — Claude gives the final answer

Claude now has everything it needs. This time, the response contains **only text
blocks** — no `tool_use`:

```
Claude's response:
  [text] "I found a patient with Type 2 diabetes:

          **Patient:** Patient Synthetic5
          **Gender:** Female
          **Date of Birth:** 1972-05-05

          **Most Recent HbA1c:** 6.72% (measured 2026-02-01)

          This HbA1c is below the 7.5% threshold for poor glycemic control,
          suggesting this patient's diabetes is reasonably well managed."
```

`tool_use_blocks` is empty, so we hit the exit condition (Section 7). The
function prints the answer and returns:

```python
return final_text, tool_calls_log, messages
#      ^^^^^^^^^^  ^^^^^^^^^^^^^^^  ^^^^^^^^
#      The answer   3 tool calls    7 messages + this final response
```

---

### What the student sees in the notebook

```
🤖 AGENT QUESTION: Find a patient with Type 2 diabetes and tell me their most recent HbA1c.

======================================================================
🔧 Step 1: search_conditions(code='44054006')
🔧 Step 2: get_patient(patient_id='19c64d7ed3e-9d367f0d-2a6e-4055-85d5-5080b2a5d1a8')
🔧 Step 3: search_observations(patient_id='19c64d7ed3e-9d367f0d-2a6e-4055-85d5-5080b2a5d1a8', loinc_code='4548-4')

======================================================================
✅ FINAL ANSWER (after 4 steps):

I found a patient with Type 2 diabetes:
...
```

Three tool calls, four loop iterations (the fourth produces the final text),
and the `messages` list grew from 1 entry to 8 entries over the course of the
run.

---

## The Complete Function

For reference, here is the entire `run_agent` function as it appears in the
notebook, without interruption:

```python
def run_agent(question, system_prompt=SYSTEM_PROMPT, tools=tools,
              available_functions=available_functions, max_steps=25):
    """Run the tool-use agent loop."""
    print(f"\U0001f916 AGENT QUESTION: {question}\n")
    print("=" * 70)

    messages = [{"role": "user", "content": question}]
    tool_calls_log = []
    step = 0

    while step < max_steps:
        step += 1
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=system_prompt,
            tools=tools,
            messages=messages,
        )

        # Check for tool use
        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

        if not tool_use_blocks:
            # Final text response
            final_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    final_text += block.text
            print(f"\n{'=' * 70}")
            print(f"\u2705 FINAL ANSWER (after {step} steps):\n")
            print(final_text)
            return final_text, tool_calls_log, messages

        # Serialize assistant content for message history
        assistant_content = []
        for block in response.content:
            if block.type == "text":
                assistant_content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                assistant_content.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })
        messages.append({"role": "assistant", "content": assistant_content})

        # Execute each tool call
        tool_results = []
        for block in tool_use_blocks:
            fn_name = block.name
            fn_args = block.input

            args_str = ", ".join(f"{k}={v!r}" for k, v in fn_args.items())
            print(f"\U0001f527 Step {step}: {fn_name}({args_str})")

            tool_calls_log.append({
                "step": step,
                "function": fn_name,
                "arguments": fn_args,
            })

            try:
                result = available_functions[fn_name](**fn_args)
            except Exception as e:
                result = {"error": str(e)}

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(result, default=str),
            })

        messages.append({"role": "user", "content": tool_results})

    print(f"\n\u26a0\ufe0f Reached max steps ({max_steps})")
    return "Agent reached step limit.", tool_calls_log, messages
```
