"""Inventory of installed coding-agent tooling (Claude Code, Antigravity, Cursor, Codex,
Gemini CLI), plus a search of the Claude Code plugin marketplaces on disk.

  python inventory.py [project_dir]          what is installed (user + project scope)
  python inventory.py --catalog WORD [WORD]  Claude Code marketplace plugins matching any word

Standard library only. Agents that aren't installed are reported as "not found".
"""
import json
import re
import sys
from pathlib import Path

HOME = Path.home()
CLAUDE = HOME / ".claude"
PLUGINS = CLAUDE / "plugins"


UNREADABLE = []  # config files that exist but couldn't be parsed — their "-" lines are unknown, not empty


def load(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except OSError:
        return {}
    except ValueError:
        data = None
    if isinstance(data, dict):
        return data
    if str(path) not in UNREADABLE:
        UNREADABLE.append(str(path))
    return {}


def names(value):
    """Keys of a config object; anything else (list, string, null) counts as empty."""
    return list(value) if isinstance(value, dict) else []


def frontmatter(skill_md):
    try:
        text = skill_md.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.S)
    out = {}
    for line in (m.group(1) if m else "").splitlines():
        k, _, v = line.partition(":")
        if v and not line.startswith(" "):
            out[k.strip()] = v.strip().strip("\"'")
    return out


def short(s, n=110):
    s = " ".join((s or "").split())
    return s if len(s) <= n else s[: n - 1] + "…"


def skills_in(folder):
    return sorted(p.parent.name for p in Path(folder).glob("*/SKILL.md"))


def show(label, items):
    print(f"  {label}: {', '.join(items) or '-'}")


def toml_tables(path, prefix):
    """Names under [prefix.<name>] / [[prefix.<name>]] in a TOML file, without a TOML parser."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError:
        return []
    names = re.findall(rf"^\s*\[\[?{re.escape(prefix)}\.(\"[^\"]+\"|[^\].]+)", text, re.M)
    return sorted({n.strip('"') for n in names})


def hook_events(path):
    """Event names in a hooks.json, whether nested under "hooks" or at the top level."""
    data = load(path)
    return sorted(names(data.get("hooks", data)))


def shared(project):
    print("Sections below cover every agent found on this machine. Audit only the one you are")
    print("running in; if it has no section, this script doesn't cover it — never use another's.\n")
    print("== SHARED SKILLS (.agents/skills — read by Antigravity, Cursor, Codex, Gemini CLI) ==")
    show("user ~/.agents/skills", skills_in(HOME / ".agents" / "skills"))
    show("project .agents/skills", skills_in(project / ".agents" / "skills"))

    print(f"\n== PROJECT CONTEXT ({project}) ==")
    names = ("CLAUDE.md", "AGENTS.md", "AGENTS.override.md", "GEMINI.md", ".cursorrules",
             ".github/copilot-instructions.md", ".mcp.json")
    show("files", [n for n in names if (project / n).is_file()])
    print("  loads by default: Claude Code → CLAUDE.md · Codex, Cursor → AGENTS.md · Gemini CLI → GEMINI.md"
          " · Antigravity → AGENTS.md or GEMINI.md, .agents/rules/*.md")


def claude_code(project):
    print("\n== CLAUDE CODE ==")
    if not CLAUDE.is_dir() and not (project / ".claude").is_dir():
        print("  not found")
        return
    for d in sorted((CLAUDE / "skills").glob("*/SKILL.md")):
        print(f"  skill: {d.parent.name} — {short(frontmatter(d).get('description'))}")

    on = {}
    for f in ("settings.json", "settings.local.json"):
        ep = load(CLAUDE / f).get("enabledPlugins")
        if isinstance(ep, dict):
            on.update(ep)
    for key, installs in load(PLUGINS / "installed_plugins.json").get("plugins", {}).items():
        if not (isinstance(installs, list) and installs and isinstance(installs[-1], dict)
                and installs[-1].get("installPath")):
            continue
        path = Path(installs[-1]["installPath"])
        meta = load(path / ".claude-plugin" / "plugin.json")
        state = "on " if on.get(key) else "off"
        print(f"  plugin [{state}] {key} — {short(meta.get('description'), 90)}")
        sk = skills_in(path / "skills")
        if sk:
            print(f"        skills: {', '.join(sk)}")
        mcp = load(path / ".mcp.json")
        mcp = mcp.get("mcpServers", mcp)
        if mcp:
            print(f"        mcp: {', '.join(mcp)}")

    cfg = load(HOME / ".claude.json")
    show("mcp (user)", names(cfg.get("mcpServers", {})))
    show("mcp (local, this project)", names(cfg.get("projects", {}).get(project.as_posix(), {}).get("mcpServers", {})))
    show("mcp (project .mcp.json)", names(load(project / ".mcp.json").get("mcpServers", {})))
    print("  claude.ai connectors: not on disk — read them from your own tool list")

    user = load(CLAUDE / "settings.json")
    show("hooks (user)", names(user.get("hooks", {})))
    off = [k for k, v in user.get("skillOverrides", {}).items() if v == "off"]
    print(f"  skills turned off (user): {len(off)}")

    proj = project / ".claude"
    if not proj.is_dir():
        print("  project: no .claude/ dir — no project skills, agents, hooks or overrides")
        return
    show("project skills", skills_in(proj / "skills"))
    show("project agents", sorted(p.stem for p in (proj / "agents").glob("*.md")))
    for f in ("settings.json", "settings.local.json"):
        s = load(proj / f)
        if s.get("hooks"):
            show(f"project hooks ({f})", names(s["hooks"]))
        for key in ("enabledPlugins", "skillOverrides"):
            if s.get(key):
                print(f"  project {key} ({f}): {s[key]}")


def codex(project):
    print("\n== CODEX ==")
    user, proj = HOME / ".codex", project / ".codex"
    if not user.is_dir() and not proj.is_dir():
        print("  not found")
        return
    show("skills (~/.codex/skills, legacy location)", skills_in(user / "skills"))
    show("mcp (user config.toml)", toml_tables(user / "config.toml", "mcp_servers"))
    show("mcp (project .codex/config.toml)", toml_tables(proj / "config.toml", "mcp_servers"))
    for label, d in (("user", user), ("project", proj)):
        events = hook_events(d / "hooks.json") + toml_tables(d / "config.toml", "hooks")
        show(f"hooks ({label})", sorted(set(events)))
    show("global AGENTS.md", ["~/.codex/AGENTS.md"] if (user / "AGENTS.md").is_file() else [])
    print("  project hooks load only when the project .codex/ layer is trusted")


def cursor(project):
    print("\n== CURSOR ==")
    user, proj = HOME / ".cursor", project / ".cursor"
    if not user.is_dir() and not proj.is_dir():
        print("  not found")
        return
    show("skills (user ~/.cursor/skills)", skills_in(user / "skills"))
    show("skills (project .cursor/skills)", skills_in(proj / "skills"))
    show("mcp (user ~/.cursor/mcp.json)", names(load(user / "mcp.json").get("mcpServers", {})))
    show("mcp (project .cursor/mcp.json)", names(load(proj / "mcp.json").get("mcpServers", {})))
    show("hooks (user)", hook_events(user / "hooks.json"))
    show("hooks (project)", hook_events(proj / "hooks.json"))
    show("project rules (.cursor/rules)", sorted(p.name for p in (proj / "rules").glob("*")))
    print("  also reads .claude/skills and .codex/skills; user rules live in app settings, not on disk")


def gemini(project):
    print("\n== GEMINI CLI ==")
    user, proj = HOME / ".gemini", project / ".gemini"
    if not user.is_dir() and not proj.is_dir():
        print("  not found")
        return
    show("skills (user ~/.gemini/skills)", skills_in(user / "skills"))
    show("skills (project .gemini/skills)", skills_in(proj / "skills"))
    for label, d in (("user", user), ("project", proj)):
        s = load(d / "settings.json")
        show(f"mcp ({label} settings.json)", names(s.get("mcpServers", {})))
        show(f"hooks ({label} settings.json)", names(s.get("hooks", {})))
    for label, d in (("user", user), ("project", proj)):
        for m in sorted((d / "extensions").glob("*/gemini-extension.json")):
            meta = load(m)
            print(f"  extension ({label}): {meta.get('name', m.parent.name)} — {short(meta.get('description'), 90)}")
            if meta.get("mcpServers"):
                print(f"        mcp: {', '.join(meta['mcpServers'])}")
            sk = skills_in(m.parent / "skills")
            if sk:
                print(f"        skills: {', '.join(sk)}")
    show("global GEMINI.md", ["~/.gemini/GEMINI.md"] if (user / "GEMINI.md").is_file() else [])


def antigravity(project):
    print("\n== ANTIGRAVITY ==")
    gem, proj = HOME / ".gemini", project / ".agents"
    cfg, cli = gem / "config", gem / "antigravity-cli"
    if not any(d.is_dir() for d in (cfg, cli, gem / "antigravity")) and not proj.is_dir():
        print("  not found")
        return
    show("skills (app/IDE ~/.gemini/config/skills)", skills_in(cfg / "skills"))
    show("skills (IDE legacy ~/.gemini/antigravity/skills)", skills_in(gem / "antigravity" / "skills"))
    show("skills (CLI ~/.gemini/antigravity-cli/skills)", skills_in(cli / "skills"))
    for plugins in (cfg / "plugins", cli / "plugins"):
        for p in sorted(d for d in plugins.glob("*") if d.is_dir()):
            meta = load(p / "plugin.json")
            print(f"  plugin: {meta.get('name', p.name)} — {short(meta.get('description'), 90)}")
            sk = skills_in(p / "skills")
            if sk:
                print(f"        skills: {', '.join(sk)}")
    show("mcp (global ~/.gemini/config/mcp_config.json)", names(load(cfg / "mcp_config.json").get("mcpServers", {})))
    show("mcp (project .agents/mcp_config.json)", names(load(proj / "mcp_config.json").get("mcpServers", {})))
    for label, f in (("global", cfg / "hooks.json"), ("project", proj / "hooks.json")):
        hooks = load(f)
        show(f"hooks ({label})", [f"{name}: {', '.join(k for k in h if k != 'enabled')}"
                                  for name, h in hooks.items() if isinstance(h, dict)])
    show("global rules (~/.gemini/config/rules)", sorted(p.name for p in (cfg / "rules").glob("*.md")))
    show("project rules (.agents/rules)", sorted(p.name for p in (proj / "rules").glob("*.md")))
    print("  app MCP servers are managed in Settings > Customizations, not on disk")


def catalog(words):
    installed = set(load(PLUGINS / "installed_plugins.json").get("plugins", {}))
    alts = "|".join(re.escape(w) for w in words) if words else r"\w+"
    pat = re.compile(rf"\b({alts})\b", re.I)
    found = False
    for mp in sorted((PLUGINS / "marketplaces").glob("*/.claude-plugin/marketplace.json")):
        found = True
        market = mp.parent.parent.name
        for p in load(mp).get("plugins", []):
            if not isinstance(p, dict) or not p.get("name"):
                continue
            if pat.search(f"{p.get('name')} {p.get('description', '')}"):
                key = f"{p['name']}@{market}"
                tag = "INSTALLED " if key in installed else ""
                print(f"  {tag}{key} [{p.get('category', '-')}] — {short(p.get('description'), 160)}")
    if not found:
        print("  no Claude Code marketplaces on disk — search the web instead")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    args = sys.argv[1:]
    if args[:1] == ["--catalog"]:
        catalog(args[1:])
    else:
        project = Path(args[0] if args else ".").resolve()
        for section in (shared, claude_code, antigravity, cursor, codex, gemini):
            try:
                section(project)
            except Exception as e:  # one malformed config must not hide every other agent
                print(f"  !! INCOMPLETE SECTION — stopped early ({type(e).__name__}: {e}); inspect this agent's config by hand")
        if UNREADABLE:
            print("\n!! INCOMPLETE INVENTORY — these config files exist but couldn't be parsed, so their")
            print("!! entries above show '-' even if tools are configured. Read them by hand before reporting:")
            for f in UNREADABLE:
                print(f"!!   {f}")
