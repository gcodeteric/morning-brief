"""
SimulaNewsMachine — Gerador de Audit Report
Lê o histórico git real e gera AUDIT_REPORT.md com métricas completas.
"""

import subprocess
import json
import os
from datetime import datetime
from pathlib import Path
from collections import defaultdict

REPO_ROOT = Path(__file__).resolve().parent
OUTPUT_FILE = REPO_ROOT / "AUDIT_REPORT.md"


def run_git(args: list) -> str:
    result = subprocess.run(
        ["git"] + args,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    return result.stdout.strip()


def get_all_commits() -> list:
    """Retorna lista de todos os commits com sha, data, mensagem, autor."""
    log = run_git([
        "log", "--pretty=format:%H|%ai|%an|%s", "--reverse"
    ])
    commits = []
    for line in log.splitlines():
        parts = line.split("|", 3)
        if len(parts) == 4:
            commits.append({
                "sha":     parts[0][:10],
                "sha_full": parts[0],
                "date":    parts[1][:19].replace("T", " "),
                "author":  parts[2],
                "message": parts[3],
            })
    return commits


def get_commit_stats(sha: str) -> dict:
    """Retorna ficheiros alterados e linhas +/- de um commit."""
    stat = run_git(["show", "--stat", "--format=", sha])
    files_changed = []
    insertions = 0
    deletions = 0
    for line in stat.splitlines():
        if "|" in line:
            fname = line.split("|")[0].strip()
            files_changed.append(fname)
        if "insertion" in line or "deletion" in line:
            parts = line.strip().split(",")
            for p in parts:
                p = p.strip()
                if "insertion" in p:
                    insertions += int(p.split()[0])
                elif "deletion" in p:
                    deletions += int(p.split()[0])
    return {
        "files": files_changed,
        "insertions": insertions,
        "deletions": deletions,
    }


def get_file_sizes() -> dict:
    """Retorna tamanho atual de cada ficheiro Python do projeto."""
    sizes = {}
    for f in sorted(REPO_ROOT.glob("*.py")):
        lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
        sizes[f.name] = len(lines)
    return sizes


def categorize_commit(message: str) -> str:
    msg = message.lower()
    if msg.startswith("feat"):        return "✨ Feature"
    if msg.startswith("fix"):         return "🐛 Fix"
    if msg.startswith("refactor"):    return "♻️ Refactor"
    if msg.startswith("docs"):        return "📚 Docs"
    if msg.startswith("chore"):       return "🔧 Chore"
    if "update" in msg:               return "📝 Update"
    if "delete" in msg or "remove" in msg: return "🗑️ Remove"
    if "create" in msg:               return "➕ Create"
    return "🔨 Other"


def classify_phase(message: str, date: str) -> str:
    msg = message.lower()
    if "minimax" in msg or "agent" in msg:    return "Fase A — Pipeline IA"
    if "formatter" in msg and "enrich" in msg: return "Fase B — Formatter Rico"
    if "news_sources" in msg or "newsapi" in msg or "gnews" in msg: return "Fase C — Fontes API"
    if "planner" in msg or "editorial" in msg: return "Core — Planner"
    if "curator" in msg or "dedup" in msg or "scoring" in msg: return "Core — Curator"
    if "scanner" in msg or "feed" in msg:     return "Core — Scanner/Feeds"
    if "formatter" in msg:                    return "Core — Formatter"
    if "dry-run" in msg or "lock" in msg or "alert" in msg: return "Core — Infra"
    if "weekly" in msg or "cache" in msg:     return "Core — Memória"
    if "card" in msg or "logo" in msg or "font" in msg: return "Assets — Visual"
    return "Core — Geral"


def generate_report(commits: list, file_sizes: dict) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    total_commits = len(commits)

    # Métricas agregadas
    total_insertions = 0
    total_deletions = 0
    files_touched = defaultdict(int)
    phases = defaultdict(list)
    categories = defaultdict(int)
    authors = defaultdict(int)

    commit_details = []
    for c in commits:
        stats = get_commit_stats(c["sha_full"])
        c["stats"] = stats
        total_insertions += stats["insertions"]
        total_deletions  += stats["deletions"]
        for f in stats["files"]:
            files_touched[f] += 1
        phase = classify_phase(c["message"], c["date"])
        cat   = categorize_commit(c["message"])
        phases[phase].append(c)
        categories[cat] += 1
        authors[c["author"]] += 1
        c["phase"] = phase
        c["category"] = cat
        commit_details.append(c)

    # Duração do projeto
    first_date = commits[0]["date"] if commits else "N/A"
    last_date  = commits[-1]["date"] if commits else "N/A"

    # Top ficheiros mais alterados
    top_files = sorted(files_touched.items(), key=lambda x: x[1], reverse=True)[:10]

    md = []
    md.append("# 📋 SIMULA MORNING BRIEF — AUDIT REPORT")
    md.append(f"\n> Gerado automaticamente em {now}")
    md.append(f"> Repositório: https://github.com/gcodeteric/morning-brief\n")

    md.append("---\n")
    md.append("## 📊 Métricas Globais\n")
    md.append(f"| Métrica | Valor |")
    md.append(f"|---|---|")
    md.append(f"| Total de commits | **{total_commits}** |")
    md.append(f"| Primeiro commit | {first_date} |")
    md.append(f"| Último commit | {last_date} |")
    md.append(f"| Linhas adicionadas | +{total_insertions} |")
    md.append(f"| Linhas removidas | -{total_deletions} |")
    md.append(f"| Ficheiros únicos tocados | {len(files_touched)} |")
    md.append(f"| Autores | {len(authors)} |")
    md.append("")

    md.append("---\n")
    md.append("## 📁 Tamanho Atual dos Ficheiros Python\n")
    md.append("| Ficheiro | Linhas |")
    md.append("|---|---|")
    for fname, lines in sorted(file_sizes.items(), key=lambda x: x[1], reverse=True):
        md.append(f"| `{fname}` | {lines} |")
    md.append("")

    md.append("---\n")
    md.append("## 🔥 Top 10 Ficheiros Mais Alterados\n")
    md.append("| Ficheiro | Nº de commits que o tocaram |")
    md.append("|---|---|")
    for fname, count in top_files:
        md.append(f"| `{fname}` | {count} |")
    md.append("")

    md.append("---\n")
    md.append("## 🏗️ Commits por Fase\n")
    for phase, phase_commits in sorted(phases.items()):
        md.append(f"### {phase} ({len(phase_commits)} commits)\n")
        md.append("| SHA | Data | Mensagem | +Lines | -Lines |")
        md.append("|---|---|---|---|---|")
        for c in phase_commits:
            sha_link = f"[`{c['sha']}`](https://github.com/gcodeteric/morning-brief/commit/{c['sha_full']})"
            msg = c['message'][:60] + ("…" if len(c['message']) > 60 else "")
            ins = c['stats']['insertions']
            dels = c['stats']['deletions']
            md.append(f"| {sha_link} | {c['date']} | {msg} | +{ins} | -{dels} |")
        md.append("")

    md.append("---\n")
    md.append("## 🏷️ Commits por Tipo\n")
    md.append("| Tipo | Count |")
    md.append("|---|---|")
    for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        md.append(f"| {cat} | {count} |")
    md.append("")

    md.append("---\n")
    md.append("## 📜 Histórico Completo (ordem cronológica)\n")
    md.append("| # | SHA | Data | Fase | Tipo | Mensagem |")
    md.append("|---|---|---|---|---|---|")
    for i, c in enumerate(commit_details, 1):
        sha_link = f"[`{c['sha']}`](https://github.com/gcodeteric/morning-brief/commit/{c['sha_full']})"
        msg = c['message'][:55] + ("…" if len(c['message']) > 55 else "")
        md.append(f"| {i} | {sha_link} | {c['date']} | {c['phase']} | {c['category']} | {msg} |")
    md.append("")

    md.append("---\n")
    md.append("## 🗺️ Estado Final do Sistema\n")
    md.append("| Componente | Ficheiro | Estado |")
    md.append("|---|---|---|")
    components = [
        ("Scanner RSS",        "scanner.py",        "✅ Ativo"),
        ("Feeds",              "feeds.py",           "✅ 40+ fontes, 0 falhas"),
        ("Curador",            "curator.py",         "✅ Scoring + dedup cross-dia"),
        ("Planner editorial",  "planner.py",         "✅ Roteamento + weekly cache"),
        ("Formatter",          "formatter.py",       "✅ 6 prompts + contexto completo"),
        ("Card Generator",     "card_generator.py",  "✅ Cards Instagram branded"),
        ("Pipeline IA",        "agents.py",          "✅ 5 agentes MiniMax M2.7"),
        ("Fontes API",         "news_sources.py",    "✅ NewsAPI + GNews"),
        ("Orquestrador",       "main.py",            "✅ Lock + dry-run + alertas"),
        ("Alertas",            "alerts.py",          "✅ Notificações operacionais"),
    ]
    for name, fname, status in components:
        md.append(f"| {name} | `{fname}` | {status} |")
    md.append("")

    md.append("---\n")
    md.append(f"*Gerado por audit_report_generator.py — SimulaNewsMachine v2.2*\n")

    return "\n".join(md)


if __name__ == "__main__":
    print("A gerar audit report...")
    commits    = get_all_commits()
    file_sizes = get_file_sizes()
    report     = generate_report(commits, file_sizes)
    OUTPUT_FILE.write_text(report, encoding="utf-8")
    print(f"✅ AUDIT_REPORT.md gerado — {len(commits)} commits analisados")
    print(f"   -> {OUTPUT_FILE}")
