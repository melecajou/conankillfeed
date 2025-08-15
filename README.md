# Conan Exiles Killfeed Bot

Este é um bot do Discord baseado em Python, projetado para monitorar os **backups do banco de dados** de um servidor de Conan Exiles e anunciar as mortes de jogadores em um canal específico do Discord. Ele consulta os eventos de morte diretamente do banco de dados do jogo, o que o torna preciso e eficiente.

O bot suporta múltiplos servidores (por exemplo, Exiled Lands e Isle of Siptah) e publica as mortes em canais separados.

## Funcionalidades

- Notificações de morte em tempo real extraídas diretamente do banco de dados do jogo.
- Identifica se o assassino foi um jogador ou um NPC.
- Suporte para múltiplos servidores/mapas com canais de Discord dedicados.
- Configuração simples através de um único arquivo.
- Rastreia o último evento lido para evitar mensagens duplicadas após reinicializações.

## Pré-requisitos

- Python 3.6 ou superior.
- Biblioteca `discord.py` (`pip install discord.py`).
- Um Bot do Discord e seu Token. [Guia para criar um Bot](https://discordpy.readthedocs.io/en/stable/discord.html)
- Acesso direto ao diretório `Saved` do servidor Conan Exiles, onde os backups do banco de dados (`game_backup_*.db`) são armazenados.
- Um arquivo de banco de dados `spawns.db` (não incluído) que mapeia IDs de NPCs para seus nomes.

## Instalação e Configuração

1.  **Clone o Repositório**
    ```bash
    git clone https://github.com/melecajou/conankillfeed.git
    cd conankillfeed
    ```

2.  **Instale as Dependências**
    ```bash
    pip install discord.py
    ```

3.  **Crie o Arquivo de Configuração**
    Copie o arquivo de exemplo para criar seu próprio arquivo de configuração.
    ```bash
    cp config.py.example config.py
    ```

4.  **Edite o Arquivo `config.py`**
    Abra o arquivo `config.py` e preencha as variáveis com suas informações.

    - `KILLFEED_BOT_TOKEN`: O token do seu bot do Discord. **Mantenha isso em segredo!**
    - `KILLFEED_CHANNEL_ID`: O ID do canal do Discord para onde as mortes do mapa principal (Exiled Lands) serão enviadas.
    - `SIPTAH_KILLFEED_CHANEL_ID`: O ID do canal para as mortes do mapa de Siptah.
    - `CONAN_SAVED_PATH`: O caminho absoluto para o diretório `Saved` da instalação do seu servidor principal.
      - Exemplo: `/home/steam/conan_exiles/ConanSandbox/Saved/`
    - `SIPTAH_SAVED_PATH`: O caminho absoluto para o diretório `Saved` do seu servidor de Siptah.
    - `LAST_EVENT_TIME_FILE`: Caminho para o arquivo que armazena o timestamp do último evento lido para o servidor principal. Pode deixar o padrão.
    - `SIPTAH_LAST_EVENT_TIME_FILE`: Caminho para o arquivo de timestamp do servidor de Siptah. Pode deixar o padrão.
    - `SPAWNS_DB_PATH`: Caminho para o banco de dados `spawns.db`. Este arquivo é necessário para identificar os NPCs.

    **Como obter um ID de Canal do Discord:**
    - No Discord, vá para `Configurações de Usuário` > `Avançado` e ative o `Modo de Desenvolvedor`.
    - Clique com o botão direito no canal de texto desejado e selecione `Copiar ID do Canal`.

## Executando o Bot

Depois de configurar, você pode iniciar o bot com o seguinte comando:

```bash
python3 killfeed_bot.py
```

Para manter o bot funcionando 24/7, é altamente recomendável executá-lo em uma sessão de terminal persistente usando ferramentas como `screen` ou `tmux`.

### Exemplo com `screen`:

```bash
# Inicia uma nova sessão chamada 'killfeed'
screen -S killfeed

# Inicia o bot dentro da sessão
python3 killfeed_bot.py

# Para sair da sessão sem parar o bot, pressione Ctrl+A e depois D.
# Para retornar à sessão, use:
screen -r killfeed
```

## Como Funciona

O bot verifica periodicamente o diretório `Saved` do servidor em busca do backup de banco de dados mais recente (`game_backup_*.db` ou `dlc_siptah_backup_*.db`). Ele então se conecta a este banco de dados em modo somente leitura e consulta a tabela `game_events` por novos eventos de morte (eventType 103) desde a última verificação. Se um NPC for o assassino, o bot usa o banco de dados `spawns.db` para encontrar e exibir o nome do NPC.
