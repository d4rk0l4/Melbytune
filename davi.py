"""Pacote 'Davi Zone': melhora leve pra notebook fraco (HP). Nada agressivo, nada de milagre."""
import cleaner
import debloat
import startup
import tweaks

# Só ajustes leves. Fica de fora: SysMain (ruim em HD), prioridade de jogo e plano de energia máximo.
TWEAK_IDS = ["bg_apps", "ads", "delivery_opt", "startup_delay", "menu_delay",
             "transparency", "animations", "game_dvr", "telemetry", "activity", "websearch"]

# Apps de inicialização que costumam pesar e não fazem falta no boot
STARTUP_JUNK = ("teams", "skype", "spotify", "adobe", "steam", "epicgames", "ituneshelper",
                "sunjava", "ccleaner", "utorrent", "bittorrent", "microsoftedgeautolaunch")


def run_pack(log):
    ok, msg = tweaks.create_restore_point()
    if ok:
        log("✔ Ponto de restauração criado.")
    else:
        log("• Não consegui criar o ponto de restauração "
            "(o Windows só deixa 1 a cada 24h, ou a Proteção do Sistema está desligada). Seguindo mesmo assim.")

    n = 0
    for t in tweaks.TWEAKS:
        if t.id in TWEAK_IDS:
            try:
                if not tweaks.is_applied(t):
                    tweaks.apply(t)
                    n += 1
            except Exception as e:
                log(f"• Falhou em '{t.name}': {e}")
    log(f"✔ Ajustes leves aplicados: {n}")

    freed = 0
    try:
        for _, path, _ in cleaner.scan():
            freed += cleaner.clean_folder(path)
        cleaner.empty_recycle_bin()
        log(f"✔ Limpeza: {cleaner.fmt(freed)} liberados (fora a lixeira)")
    except Exception as e:
        log(f"• Limpeza falhou: {e}")

    off = []
    try:
        for e in startup.list_entries():
            if e.enabled and any(k in e.name.lower() for k in STARTUP_JUNK):
                startup.set_enabled(e, False)
                off.append(e.name)
    except Exception as e:
        log(f"• Inicialização falhou: {e}")
    log("✔ Desligados na inicialização: " + (", ".join(off) if off else "nada pesado encontrado"))

    removed = []
    try:
        have = debloat.installed()
        labels = dict(debloat.APPS)
        for pkg in debloat.LEVE:
            if pkg in have and debloat.remove(pkg)[0]:
                removed.append(labels.get(pkg, pkg))
    except Exception as e:
        log(f"• Debloat falhou: {e}")
    log("✔ Apps inúteis removidos: " + (", ".join(removed) if removed else "nenhum (já estava limpo)"))

    log("")
    log("Pronto! Reinicie o notebook pra tudo fazer efeito.")
    log("Pra desfazer: aba Sistema > Restaurar tudo (ajustes) e aba Inicialização (programas).")
