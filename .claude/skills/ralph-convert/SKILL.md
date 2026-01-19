---
name: ralph-convert
description: "Convert PRDs to ralph.json format for autonomous agent execution. Use when you have an existing PRD and need to convert it to Ralph's JSON format. Triggers on: convert this prd, turn this into ralph format, create ralph.json from this, ralph json, convert to ralph."
---

# Ralph PRD Converter

Converts existing PRDs to the `ralph.json` format that Ralph uses for autonomous execution with true dependency modeling.

---

## The Job

Take a PRD (markdown file or text) and convert it to `ralph.json` in your ralph directory.

---

## Output Format

```json
{
  "version": "1.0",
  "project": "[Project Name]",
  "feature": "[Feature description from PRD title/intro]",
  "branch": "ralph/[feature-name-kebab-case]",
  "created": "[ISO timestamp]",
  "status": "in_progress",
  
  "tasks": [
    {
      "id": "T001",
      "title": "[Task title]",
      "description": "[What this task accomplishes]",
      "type": "schema|backend|ui|test|docs|refactor",
      "dependsOn": [],
      "acceptanceCriteria": [
        "Criterion 1",
        "Criterion 2",
        "Typecheck passes"
      ],
      "status": "open",
      "completedAt": null,
      "notes": ""
    }
  ],
  
  "discovered": [],
  
  "patterns": [],
  
  "context": {
    "techStack": [],
    "keyFiles": [],
    "conventions": []
  }
}
```

---

## Task Size: The Number One Rule

**Each task must be completable in ONE Ralph iteration (one context window).**

Ralph spawns a fresh agent instance per iteration with no memory of previous work. If a task is too big, the LLM runs out of context before finishing and produces broken code.

### Right-sized tasks:
- Add a database column and migration
- Add a UI component to an existing page
- Update a server action with new logic
- Add a filter dropdown to a list

### Too big (split these):
- "Build the entire dashboard" → Split into: schema, queries, UI components, filters
- "Add authentication" → Split into: schema, middleware, login UI, session handling
- "Refactor the API" → Split into one task per endpoint or pattern

**Rule of thumb:** If you cannot describe the change in 2-3 sentences, it is too big.

---

## Task Types

Assign one of these types to each task:

| Type | Description | Examples |
|------|-------------|----------|
| `schema` | Database migrations, schema changes | Add column, create table, add index |
| `backend` | Server logic, APIs, actions | Server actions, API routes, services |
| `ui` | Frontend components, pages | Components, layouts, styling |
| `test` | Tests | Unit tests, integration tests, e2e |
| `docs` | Documentation | README updates, API docs, comments |
| `refactor` | Code improvements | Extract function, rename, reorganize |

**Execution priority when multiple tasks are ready:**
1. `schema` (database first)
2. `backend` (then server logic)
3. `ui` (then interface)
4. `test` (then tests)
5. `docs` / `refactor` (last)

---

## Dependencies:

**New format (dependency-based):**
```json
{ "id": "T002", "dependsOn": ["T001"] }  // Needs T001
{ "id": "T003", "dependsOn": ["T001"] }  // Also needs T001, NOT T002
```
Benefit: T002 and T003 can run in parallel (or whichever is picked first).

### Dependency rules:

1. **Schema tasks** usually have `dependsOn: []` (no dependencies)
2. **Backend tasks** depend on schema tasks they use
3. **UI tasks** depend on backend tasks they call AND schema they read
4. **Test tasks** depend on the code they test
5. **Multiple dependencies are allowed:** `"dependsOn": ["T001", "T002"]`

### Common patterns:

```
T001 (schema) ─────┬───→ T003 (ui: display)
                   │
T002 (backend) ────┴───→ T004 (ui: edit) ───→ T005 (test)
     ↑
     └── dependsOn: ["T001"]
```

---

## Acceptance Criteria: Must Be Verifiable

Each criterion must be something Ralph can CHECK, not something vague.

### Good criteria (verifiable):
- "Add `status` column to tasks table with default 'pending'"
- "Filter dropdown has options: All, Active, Completed"
- "Clicking delete shows confirmation dialog"
- "Typecheck passes"
- "Tests pass"

### Bad criteria (vague):
- ❌ "Works correctly"
- ❌ "User can do X easily"
- ❌ "Good UX"
- ❌ "Handles edge cases"

### Always include based on task type:

| Task Type | Required Criteria |
|-----------|-------------------|
| All tasks | "Typecheck passes" |
| `test` | "All tests pass" |
| `ui` | "Verify in browser using dev-browser skill" |
| `backend` with logic | "Tests pass" (if testable) |

---

## Conversion Rules

1. **Each user story / requirement becomes one or more tasks**
2. **IDs**: Sequential (T001, T002, etc.)
3. **Type**: Infer from content (schema/backend/ui/test/docs/refactor)
4. **dependsOn**: Model actual dependencies, not just sequential order
5. **All tasks**: `status: "open"`, `completedAt: null`, `notes: ""`
6. **branch**: Derive from feature name, kebab-case, prefixed with `ralph/`
7. **Always add**: "Typecheck passes" to every task's acceptance criteria

---

## Splitting Large PRDs

If a PRD has big features, split them into properly-typed tasks with dependencies:

**Original:**
> "Add user notification system"

**Split into:**
```json
{
  "tasks": [
    {
      "id": "T001",
      "title": "Add notifications table",
      "type": "schema",
      "dependsOn": []
    },
    {
      "id": "T002", 
      "title": "Create notification service",
      "type": "backend",
      "dependsOn": ["T001"]
    },
    {
      "id": "T003",
      "title": "Add notification bell icon to header",
      "type": "ui",
      "dependsOn": ["T001"]
    },
    {
      "id": "T004",
      "title": "Create notification dropdown panel",
      "type": "ui",
      "dependsOn": ["T002", "T003"]
    },
    {
      "id": "T005",
      "title": "Add mark-as-read functionality",
      "type": "ui",
      "dependsOn": ["T002", "T004"]
    },
    {
      "id": "T006",
      "title": "Add notification preferences page",
      "type": "ui",
      "dependsOn": ["T002"]
    }
  ]
}
```

Notice: T003 and T006 don't depend on each other—they can execute in parallel.

---

## Populating Context

Ask the user or infer from the PRD:

### techStack
```json
"techStack": ["Next.js 14", "TypeScript", "Drizzle ORM", "Tailwind CSS"]
```

### keyFiles
```json
"keyFiles": [
  "lib/db/schema.ts - Database schema",
  "lib/actions/ - Server actions",
  "components/ui/ - Reusable components"
]
```

### conventions
```json
"conventions": [
  "Use server actions for mutations",
  "Run typecheck before committing",
  "Use shadcn/ui components where available"
]
```

**If unknown, leave empty arrays** — Ralph will populate these during execution as it discovers patterns.

---

## Example Conversion

**Input PRD:**
```markdown
# Task Status Feature

Add ability to mark tasks with different statuses.

## Requirements
- Toggle between pending/in-progress/done on task list
- Filter list by status
- Show status badge on each task
- Persist status in database
```

**Output ralph.json:**
```json
{
  "version": "1.0",
  "project": "TaskApp",
  "feature": "Task status tracking with visual indicators and filtering",
  "branch": "ralph/task-status",
  "created": "2025-01-19T10:00:00Z",
  "status": "in_progress",
  
  "tasks": [
    {
      "id": "T001",
      "title": "Add status column to tasks table",
      "description": "Database migration to add status field for tracking task progress",
      "type": "schema",
      "dependsOn": [],
      "acceptanceCriteria": [
        "Add status column: 'pending' | 'in_progress' | 'done'",
        "Default value is 'pending'",
        "Migration runs without errors",
        "Typecheck passes"
      ],
      "status": "open",
      "completedAt": null,
      "notes": ""
    },
    {
      "id": "T002",
      "title": "Create updateTaskStatus server action",
      "description": "Backend function to change task status with validation",
      "type": "backend",
      "dependsOn": ["T001"],
      "acceptanceCriteria": [
        "updateTaskStatus(taskId, newStatus) exists in lib/actions/tasks.ts",
        "Validates status is one of allowed values",
        "Returns updated task object",
        "Typecheck passes"
      ],
      "status": "open",
      "completedAt": null,
      "notes": ""
    },
    {
      "id": "T003",
      "title": "Display status badge on task cards",
      "description": "Visual indicator showing current task status",
      "type": "ui",
      "dependsOn": ["T001"],
      "acceptanceCriteria": [
        "Each task card shows colored status badge",
        "Badge colors: gray=pending, blue=in_progress, green=done",
        "Typecheck passes",
        "Verify in browser using dev-browser skill"
      ],
      "status": "open",
      "completedAt": null,
      "notes": ""
    },
    {
      "id": "T004",
      "title": "Add status dropdown to task rows",
      "description": "Allow users to change task status directly from the list",
      "type": "ui",
      "dependsOn": ["T002", "T003"],
      "acceptanceCriteria": [
        "Dropdown appears on each task row",
        "Shows current status as selected",
        "Selecting status calls updateTaskStatus",
        "UI updates optimistically",
        "Typecheck passes",
        "Verify in browser using dev-browser skill"
      ],
      "status": "open",
      "completedAt": null,
      "notes": ""
    },
    {
      "id": "T005",
      "title": "Add status filter to task list",
      "description": "Filter dropdown to show only tasks with selected status",
      "type": "ui",
      "dependsOn": ["T003"],
      "acceptanceCriteria": [
        "Filter dropdown: All | Pending | In Progress | Done",
        "Filter persists in URL params",
        "Empty state when no tasks match",
        "Typecheck passes",
        "Verify in browser using dev-browser skill"
      ],
      "status": "open",
      "completedAt": null,
      "notes": ""
    },
    {
      "id": "T006",
      "title": "Add status filter tests",
      "description": "Unit tests for status filtering logic",
      "type": "test",
      "dependsOn": ["T005"],
      "acceptanceCriteria": [
        "Test: 'all' filter returns all tasks",
        "Test: status filter returns only matching",
        "Test: empty result shows empty state",
        "All tests pass"
      ],
      "status": "open",
      "completedAt": null,
      "notes": ""
    }
  ],
  
  "discovered": [],
  
  "patterns": [],
  
  "context": {
    "techStack": ["Next.js 14", "TypeScript", "Drizzle ORM", "Tailwind CSS"],
    "keyFiles": [
      "lib/db/schema.ts - Database schema",
      "lib/actions/tasks.ts - Task server actions",
      "components/tasks/task-card.tsx - Task display component"
    ],
    "conventions": [
      "Use server actions for mutations",
      "Run typecheck before committing"
    ]
  }
}
```

**Dependency graph for this feature:**
```
T001 (schema) ──┬──→ T002 (backend) ──┬──→ T004 (ui: dropdown)
                │                     │
                ├──→ T003 (ui: badge) ┘
                │         │
                │         └──→ T005 (ui: filter) ──→ T006 (test)
```

T002, T003, and T005 can all start once T001 completes—true parallelism.

---

## Archiving Previous Runs

**Before writing a new ralph.json, check if one exists from a different feature:**

1. Read current `ralph.json` if it exists
2. Check if `branch` differs from the new feature
3. If different:
   - Create archive folder: `archive/YYYY-MM-DD-feature-name/`
   - Copy current `ralph.json` to archive
   - Then write the new one

```bash
# Archive command
DATE=$(date +%Y-%m-%d)
FEATURE=$(jq -r '.branch' ralph.json | sed 's|^ralph/||')
mkdir -p archive/$DATE-$FEATURE
cp ralph.json archive/$DATE-$FEATURE/
```

---

## Checklist Before Saving

Before writing ralph.json, verify:

- [ ] **Previous run archived** (if ralph.json exists with different branch)
- [ ] Each task completable in one iteration (small enough)
- [ ] Each task has a `type` assigned
- [ ] Dependencies are accurate (not just sequential)
- [ ] No circular dependencies
- [ ] At least one task has `dependsOn: []` (entry point exists)
- [ ] Every task has "Typecheck passes" as criterion
- [ ] UI tasks have "Verify in browser using dev-browser skill"
- [ ] Test tasks have "All tests pass"
- [ ] Acceptance criteria are verifiable (not vague)
- [ ] `context` section populated (or empty arrays if unknown)

---

## Quick Reference: Task Template

```json
{
  "id": "T00X",
  "title": "[Short descriptive title]",
  "description": "[What this accomplishes - 1-2 sentences]",
  "type": "[schema|backend|ui|test|docs|refactor]",
  "dependsOn": ["T00Y", "T00Z"],
  "acceptanceCriteria": [
    "[Specific verifiable criterion]",
    "[Another criterion]",
    "Typecheck passes"
  ],
  "status": "open",
  "completedAt": null,
  "notes": ""
}
```