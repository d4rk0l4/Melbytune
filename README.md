# MelbyTune — Seu PC. Seu ritmo.

Otimizador de PC pessoal (Windows 10/11). Preto, amarelo-mel e roxo.

## Pra quem só quer usar (sem Python)
Peça o `MelbyTune.exe` pronto. Dois detalhes normais pra app sem assinatura digital:
- O Windows pode mostrar "O Windows protegeu seu PC": clique em **Mais informações > Executar assim mesmo**.
- O antivírus pode reclamar (falso positivo comum em .exe feito com PyInstaller). Se acontecer, libere o arquivo.

O app pede permissão de administrador ao abrir. É necessário pra mexer em chaves do sistema.

## Gerar o .exe (só quem faz o app precisa de Python)
O .exe precisa ser gerado no **Windows**. Duas formas:

**A) Pelo GitHub (sem instalar nada):** a cada push na `main` o GitHub gera o `.exe` sozinho.
Vá em *Actions*, abra o último build e baixe `MelbyTune` em **Artifacts**.
(Também dá pra rodar na mão: Actions > Build MelbyTune > Run workflow.)

**B) No seu PC:** instale o Python e dê duplo clique em `build.bat`. O arquivo sai em `dist\MelbyTune.exe`.

## Rodar direto pelo código
```
pip install -r requirements.txt
python main.py
```

## O que tem
| Aba | O que faz |
|---|---|
| **Painel** | CPU, RAM, disco e GPU (GPU só NVIDIA) em tempo real |
| **Ajustes** | 20 ajustes em 4 grupos (Jogos, **Input lag**, Privacidade, Sistema). Cada um mostra o comando e desfaz |
| **Inicialização** | Liga/desliga os programas que abrem com o Windows (mesma chave do Gerenciador de Tarefas) |
| **Debloat** | Remove apps pré-instalados de uma lista segura; dá pra tentar reinstalar |
| **Instalar apps** | Marca vários e instala tudo de uma vez pelo winget; "atualizar todos os apps" |
| **Limpeza** | Temporários, **arquivos duplicados** (vão pra Lixeira) e **arquivos grandes** |
| **Segurança** | **Antivírus** (comanda o Microsoft Defender: análise rápida/completa/de pasta, ameaças) e **Reparar Windows** (DISM, SFC, CHKDSK) |
| **Ferramentas** | Teste de CPS, teste de monitor (pixel morto, cores, degradê), teste de velocidade, comparar placas |
| **Sistema** | Ponto de restauração, plano de energia, "restaurar tudo" |
| **Davi Zone** | Pacote pro notebook fraco: "Tentar melhorar o desempenho" + gerar ponto de restauração |

### Limites (importante)
- O **antivírus é o Microsoft Defender** que já vem no Windows. O MelbyTune só comanda ele. Com outro antivírus instalado, o Defender fica passivo.
- **Reparar Windows** conserta arquivos do *sistema* e erros de disco. Não recupera fotos/documentos seus corrompidos.
- **Input lag**: o efeito é pequeno e muda de PC pra PC. Não espere milagre.
- O **Davi Zone** faz melhorias leves. Notebook fraco continua fraco: o que mais resolve é SSD e mais RAM.

## Como a reversão dos ajustes funciona
Antes de mudar qualquer chave, o app salva o valor original em `%APPDATA%\MelbyTune\backup.json`.
Desligar o ajuste restaura esse valor (ou apaga a chave, se ela não existia).
"Restaurar tudo" (aba Sistema) desfaz todos os ajustes. Debloat e Inicialização têm os próprios botões.

## Mexer no código
- Novo ajuste: `tweaks.py`, adicione um `Tweak(...)` em `TWEAKS` (aparece sozinho na aba Ajustes).
- Novo app no Debloat: `debloat.py`. Novo app pra instalar: `installer.py` (id do winget).
- Valores das placas de vídeo: `gpus.py`.
- Logo e ícone: pasta `assets/` (troque `logo.png`, `icon.png` e `icon.ico`).
