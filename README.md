# SystemHub

SystemHub é um utilitário desktop para Windows desenvolvido em Python com uma interface moderna em Tkinter. O projeto reúne diagnóstico do sistema, gerenciamento de firewall e limpeza de arquivos temporários em um único painel, com foco em simplicidade, clareza e uso prático.

## O que você encontra aqui

- Dashboard com métricas de CPU, RAM, armazenamento e sistema
- Visualização de informações de hardware e ambiente Windows
- Gerenciamento de firewall com filtro e ações por porta
- Limpeza de arquivos temporários e caches comuns
- Exportação de regras do firewall para arquivos JSON, TXT e CSV

## Como usar

### 1. Instale as dependências

No terminal, na pasta do projeto:

```bash
py -3 -m pip install -r requirements.txt
```

### 2. Execute a aplicação

```bash
py -3 main.py
```

### 3. Navegue pelas páginas

- Dashboard: veja o estado atual do hardware
- Firewall: liste conexões e gerencie regras
- Cleanup: limpe arquivos temporários
- Settings: confira as preferências da interface

## Requisitos

- Python 3.10 ou superior
- Windows
- Permissões de administrador para algumas ações de firewall
- Dependências listadas em requirements.txt

## Recursos principais

### Dashboard

A página principal exibe em tempo real:

- sistema operacional e build
- CPU, uso, frequência e temperatura
- memória RAM total e em uso
- discos, espaço livre e saúde
- placa-mãe, BIOS e GPU quando disponível

### Firewall

Na aba Firewall, é possível:

- verificar se o firewall está ativo
- ativar ou desativar o firewall
- listar conexões ativas com protocolo, estado e PID
- filtrar por porta, processo, protocolo ou endereço
- liberar, bloquear e remover regras de portas
- exportar regras para arquivos

> Algumas operações podem exigir execução como administrador.

### Limpeza

A aba Cleanup tenta remover arquivos temporários e pastas de cache comuns no Windows, de forma conservadora e com foco em segurança.

## Estrutura do projeto

- main.py: ponto de entrada da aplicação
- modules/cleanup.py: limpeza de arquivos temporários
- modules/firewall.py: regras e conexões do firewall
- modules/diagnostics.py: coleta de informações do sistema
- modules/hardware_services.py: integração com bibliotecas de hardware
- tests/: testes automatizados das principais áreas

## Documentação completa

A documentação detalhada da aplicação está disponível em [docs/index.md](docs/index.md).

## Testes

Para rodar a suíte de testes:

```bash
pytest -q
```

## Observações importantes

- O projeto é pensado para uso prático em ambientes Windows.
- A limpeza é conservadora e pode ignorar arquivos protegidos.
- Ações mais sensíveis de firewall são melhores executadas com privilégios elevados.
