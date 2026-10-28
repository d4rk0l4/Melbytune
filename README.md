# MelbyTune

Otimizador de PC pessoal (Windows 10/11). Tema escuro com amarelo.

## Pra quem só quer usar (sem Python)
Peça o `MelbyTune.exe` pronto. Dois detalhes normais pra app sem assinatura digital:
- O Windows pode mostrar "O Windows protegeu seu PC": clique em **Mais informações > Executar assim mesmo**.
- O antivírus pode reclamar (falso positivo comum em .exe feito com PyInstaller). Se acontecer, libere o arquivo.

O app pede permissão de administrador ao abrir. É necessário pra mexer em chaves do sistema.

## Gerar o .exe (só quem faz o app precisa de Python)
O .exe precisa ser gerado no **Windows**. Duas formas:

**A) No seu PC:** instale o Python, dê duplo clique em `build.bat`. O arquivo sai em `dist\MelbyTune.exe`.

**B) Pelo GitHub (sem instalar nada):** suba esta pasta num repositório, vá em
Actions > Build MelbyTune > Run workflow. Quando terminar, baixe o `MelbyTune.exe` em "Artifacts".

## Rodar direto pelo código
```
pip install -r requirements.txt
python main.py
```

## O que tem
- **Painel**: CPU, RAM, disco e GPU (GPU só NVIDIA, via nvidia-smi) em tempo real
- **Ajustes**: 12 ajustes (jogos, privacidade, sistema). Cada um mostra o comando e pode ser desfeito
- **Limpeza**: temporários, relatórios de erro, cache de shaders e lixeira
- **Debloat**: remove apps pré-instalados de uma lista segura; dá pra tentar reinstalar
- **Placas de vídeo**: comparador local (edite os valores em `gpus.py`)
- **Sistema**: ponto de restauração, plano de energia, "restaurar tudo"

## Como a reversão dos ajustes funciona
Antes de mudar qualquer chave, o app salva o valor original em
`%APPDATA%\MelbyTune\backup.json`. Desligar o ajuste restaura esse valor
(ou apaga a chave, se ela não existia).

## Adicionar um ajuste novo
Em `tweaks.py`, adicione um `Tweak(...)` na lista `TWEAKS`. Ele aparece sozinho na aba Ajustes.
Pra adicionar app no Debloat, inclua `("NomeDoPacote", "Rótulo")` em `debloat.py`.
