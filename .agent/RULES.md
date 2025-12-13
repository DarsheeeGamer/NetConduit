# Development Rules for Conduit Project

> [!CAUTION]
> These rules are **MANDATORY** and must be followed at all times without exception.

---

## Rule 1: Testing Before Claiming Completion

**NEVER** hallucinate or claim "It's done and implemented and working" without **TESTING** the implementation first and verifying it has no errors.

- Testing means doing **proper verification** to see if it works correctly
- Not over-testing, but sufficient testing to ensure functionality
- Must verify before reporting completion to user

---

## Rule 2: No False Hope

Everything stated **MUST always be TRUE**, not something false to give false hope.

- Accuracy and honesty in all communications
- Never overstate what has been accomplished
- Set realistic expectations

---

## Rule 3: Complete Working Implementations

Provide **proper working completed implementations**, not something claimed as "implemented" but is actually just comments and unimplemented stubs.

- No placeholder comments like "TODO: implement this"
- No unimplemented functions marked with comments
- Everything must be fully functional code

---

## Rule 4: Extensive Planning and Logical Thinking

When starting something, **plan extensively**, map everything out, and **logically THINK multiple times** before taking action to ensure correctness.

- Think through the approach thoroughly
- Map out all components and dependencies
- Verify the plan makes sense before implementation
- Double-check and triple-check before executing

---

## Rule 5: Git Commit History and User Availability

- User may not always be available - understand this and work accordingly
- When user is available, they will communicate
- **Maintain proper git commit history** with proper logs
- This ensures ability to **immediately REVERT** to previous state if something breaks
- Clean, descriptive commit messages are required

---

## Rule 6: Never Assume - Always Clarify

**NEVER EVER** do something without clarification.

- If you don't understand something, **DON'T ASSUME**
- **Ask the user** for clarification when they are available
- If user is not available, work on something else that you understand
- If you understand nothing, **STOP WORKING**

---

## Rule 7: This is a Real Production Project

**NEVER EVER** assume this project is not a real project.

- This **IS** and **WILL BE** a real literal **PRODUCTION PROJECT**
- Never leave logic, features, or code saying "In a real implementation..."
- Everything must be production-grade, real, and functional
- **Zero tolerance** for placeholder or mock implementations

---

## Rule 8: Dependency-First Development

When starting development, work on dependencies first:

**If X depends on Y, and Y depends on Z, and Z depends on nothing:**
- Work on **Z first**, then **Y**, then **X**

**If all components have dependencies:**
- Work on the one with the **least dependencies** but has the **most usage**
- Prioritize components that are imported and used the most

---

## Rule 9: Plan with Proper Diagrams

When planning, create **proper flowchart diagrams**.

- Visual representation of logic flow
- Clear component relationships
- Architecture diagrams where appropriate
- Use Mermaid or other diagram tools

---

## Rule 10: Comprehensive Task Lists with Links

When planning, create a **proper Task List** with:

- All features and details mentioned
- Link each task to its corresponding:
  - Graphs
  - Plans
  - Diagrams
  - Flowcharts
- Easy reference during implementation
- Clear traceability from task to design

---

## Rule 11: Never Forget These Rules

**NEVER EVER** forget these rules.

- Zero tolerance for violations
- Even the slightest deviation is unacceptable
- These rules must be followed at all times
- No exceptions

---

> [!IMPORTANT]
> Violation of any of these rules, even in the slightest, is **NOT TOLERATED**.
