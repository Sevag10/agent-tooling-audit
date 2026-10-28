# agent-tooling-audit

An [Agent Skill](https://agentskills.io) that audits a project's AI tooling. It answers *"what should my coding agent's setup look like for this repo?"*

It starts from what you **already have** installed (skills, plugins, extensions, MCP servers, hooks) and searches for new tooling only where there's a real gap. That avoids the two usual mistakes: recommending things you already own, and never looking past them.

Works with **Claude Code, Codex, Cursor and Gemini CLI**. Any other agent that reads `SKILL.md` can follow the steps too; it just won't get an automatic inventory.

## Install

The skill is the whole repo. Clone it into your agent's skills folder:

| Agent | Command |
|---|---|
| Codex, Cursor, Gemini CLI | `git clone https://github.com/Sevag10/agent-tooling-audit ~/.agents/skills/agent-tooling-audit` |
| Claude Code | `git clone https://github.com/Sevag10/agent-tooling-audit ~/.claude/skills/agent-tooling-audit` |

To install it for a single project, clone it into that repo's `.agents/skills/` (or `.claude/skills/` for Claude Code).

Needs Python 3.8+. The script uses only the standard library.

## Use

Open your agent in a project and ask something like:

- "What should I use for this project?"
- "Is my agent setup right for this repo?"
- "What am I missing?"

The agent will:

1. **Take inventory** by running `scripts/inventory.py`, which reads each installed agent's config: skills, plugins/extensions with on/off state, MCP servers, hooks, and the project's context files (`CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `.cursor/rules`, …).
2. **Profile the project** from its manifest, CI and existing hooks, and flag context files that the agent you're using won't load.
3. **Search for gaps** in local Claude Code plugin marketplaces (`inventory.py --catalog <words>`) and on the web. It reads third-party code before recommending it.
4. **Check fit**: tooling that's enabled but irrelevant here costs context on every turn, so it suggests per-project switches.
5. **Look for project-specific automations**, such as formatter/linter/test hooks, guards for secrets and production databases, and custom skills.

You get a short report with five sections: **Already covered · Turn on / off here · Install · Build · Skip**. Install and Build list at most 3 items each. Nothing is installed or changed until you approve.

### Running the script yourself

```bash
python scripts/inventory.py /path/to/project
python scripts/inventory.py --catalog stripe neon expo
```

## Where it looks

| Agent | Skills | MCP servers | Hooks |
|---|---|---|---|
| Shared | `~/.agents/skills`, `.agents/skills` | `.mcp.json` | – |
| Claude Code | `~/.claude/skills`, plugins, `.claude/skills` | `~/.claude.json`, plugins | `settings.json` |
| Codex | `~/.codex/skills` (legacy) | `config.toml` `[mcp_servers.*]` | `hooks.json`, `config.toml` `[hooks]` |
| Cursor | `~/.cursor/skills`, `.cursor/skills` | `mcp.json` | `hooks.json` |
| Gemini CLI | `~/.gemini/skills`, `.gemini/skills`, extensions | `settings.json`, extensions | `settings.json` |

Agents change their config layouts often. If a path is out of date, please open an issue or PR.

## Credits

`references/hooks-patterns.md` and `references/subagent-templates.md` come unmodified from Anthropic's [`claude-code-setup`](https://github.com/anthropics/claude-plugins-official/tree/main/plugins/claude-code-setup) plugin (Apache-2.0). See [NOTICE](NOTICE).

## License

[Apache-2.0](LICENSE)
