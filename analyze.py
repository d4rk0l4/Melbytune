"""Análise rápida do PC pro botão "Analisar PC": só lê, não muda nada."""
import cleaner
import startup
import tweaks

# item: {"level": "bad" | "warn" | "good", "text": str, "page": nome da página que resolve}


def run_analysis(scan=None):
    items = []

    def add(level, text, page):
        items.append({"level": level, "text": text, "page": page})

    # espaço em disco
    try:
        if scan and scan.get("disk_total_gb"):
            free, total = scan["disk_free_gb"], scan["disk_total_gb"]
            pct = free / total * 100
            if pct < 10 or free < 15:
                add("bad", f"Pouco espaço livre no disco {scan['disk_drive']} ({free:.0f} GB livres).", "Limpeza")
            elif pct < 20:
                add("warn", f"O disco {scan['disk_drive']} está ficando cheio ({free:.0f} GB livres).", "Limpeza")
    except Exception:
        pass

    # memória
    try:
        if scan and scan.get("ram_gb") and scan["ram_gb"] < 8:
            add("warn", f"Só {scan['ram_gb']:g} GB de RAM: feche programas pesados e limite a inicialização.", "Inicialização")
    except Exception:
        pass

    # temporários
    try:
        size = sum(s for _, _, s in cleaner.scan())
        if size > 3 * 2 ** 30:
            add("warn", f"{cleaner.fmt(size)} de arquivos temporários podem ser limpos.", "Limpeza")
    except Exception:
        pass

    # inicialização
    try:
        n = sum(1 for e in startup.list_entries() if e.enabled)
        if n > 8:
            add("warn", f"{n} programas abrem junto com o Windows. Desligar os que você não usa acelera o boot.", "Inicialização")
    except Exception:
        pass

    # ajustes de jogo ainda desligados
    try:
        off = [t for t in tweaks.TWEAKS if t.category == "Jogos" and not tweaks.is_applied(t)]
        if len(off) >= 3:
            add("warn", f"{len(off)} ajustes pra jogos ainda estão desligados.", "Desempenho")
    except Exception:
        pass

    # Defender
    try:
        import security
        st = security.status()
        if st is not None and not st.get("RealTimeProtectionEnabled", True):
            add("bad", "A proteção em tempo real do Windows Defender está desligada.", "Segurança")
    except Exception:
        pass

    bad = sum(1 for i in items if i["level"] == "bad")
    if bad:
        head = "Atenção necessária"
    elif items:
        head = "Sistema bom, dá pra melhorar"
    else:
        head = "Sistema saudável"
    return {"head": head, "ok": not items, "items": items}
