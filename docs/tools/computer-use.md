# Computer use tool (summary)

Source: https://platform.claude.com/docs/en/agents-and-tools/tool-use/computer-use-tool (read 2026-11-06).

1. What it is: an Anthropic-defined client toolset. Claude gets screenshots and mouse and keyboard control of a desktop.
2. Toolset type: `computer_toolset_20260801` (Claude 5.5 and later). Older models use `computer_20251124` with a beta header.
3. Claude does not run actions. It returns `tool_use` blocks. Your code runs them.
4. It needs an API client loop: send request, run each action in order, return one `tool_result` per `tool_use`, repeat.
5. The loop ends when Claude returns no tool use, or at a max iteration count. Set that limit.
6. Action names: `screenshot`, `zoom`, `left_click`, `right_click`, `middle_click`, `double_click`, `triple_click`, `left_click_drag`, `mouse_move`, `left_mouse_down`, `left_mouse_up`, `cursor_position`, `scroll`, `type`, `key`, `hold_key`, `wait`.
7. Coordinates use screenshot pixels. Claude can batch actions. On a failure, stop and return `is_error: true` for the rest.
8. Safety: use a dedicated VM or container with minimal privileges. Keep sensitive data and logins out of it.
9. Safety: limit internet access to an allowlist. Ask a human to confirm purchases, consent, and terms of service.
10. Safety: webpage and image text can inject instructions. Classifiers scan screenshots, but keep a human in the loop.

Model-500 note: this suite does not call this API. Claude Code and Claude desktop control the screen through their own tools. Use this page only as background.
