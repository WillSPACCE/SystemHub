# 🧰 SystemHub

SystemHub é um utilitário desktop para Windows desenvolvido em Python com uma interface moderna em Tkinter. O projeto reúne diagnóstico do sistema, gerenciamento de firewall e limpeza de arquivos temporários em um único painel, com foco em praticidade, organização e facilidade de uso.

![Status](https://img.shields.io/badge/Status-Em%20desenvolvimento-blue)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB)
![Windows](https://img.shields.io/badge/Plataforma-Windows-0078D6)

## ✨ O que é o projeto?

O SystemHub foi criado para centralizar tarefas comuns de manutenção e diagnóstico em um único ambiente visual. Em vez de abrir várias ferramentas, você pode:

- 📊 acompanhar o estado do hardware em tempo real;
- 🛡️ gerenciar regras e conexões do firewall;
- 🧹 limpar arquivos temporários e caches de forma mais controlada;
- 📁 exportar dados úteis para análise ou documentação.

## 🧭 O que cada parte faz

### 📊 Dashboard

A página inicial mostra um resumo rápido do computador:

- CPU, uso, frequência e temperatura
- Memória RAM total e utilizada
- Espaço em disco, saúde e desempenho geral
- Informações do sistema, placa-mãe, BIOS e GPU quando disponíveis

Essa seção é ideal para uma visão rápida do estado do equipamento.

### 🛡️ Firewall

Na aba Firewall, você pode:

- verificar se o firewall está ativo;
- ativar ou desativar o firewall;
- listar conexões ativas com protocolo, estado e PID;
- filtrar por porta, processo, endereço ou protocolo;
- liberar, bloquear ou remover regras de portas;
- exportar regras para arquivos JSON, TXT ou CSV.

> Algumas operações exigem permissões administrativas.

### 🧹 Central de Manutenção

A aba Limpeza agora funciona como uma Central de Manutenção profissional. Com um único clique, é possível:

- coletar dados iniciais do sistema;
- executar um checklist visual das etapas;
- limpar arquivos temporários e caches selecionados;
- rodar uma verificação rápida do Microsoft Defender;
- gerar um relatório técnico em TXT;
- salvar o histórico das execuções;
- enviar o relatório automaticamente por e-mail via Resend, quando configurado.

### ⚙️ Configurações

A página de configurações organiza as preferências da interface, ajudando a experiência a ficar mais consistente e simples.

A nova seção de Relatórios por E-mail permite configurar a API Resend principal e reserva, definir remetente e destinatário, personalizar assunto e corpo do e-mail, habilitar envio automático, salvar relatórios para envio posterior em caso de falha e acompanhar o histórico recente sem sair da aplicação. O envio agora tenta usar a biblioteca oficial quando disponível e, se não estiver presente, faz fallback direto para a API HTTP da Resend para manter o fluxo funcional.

## ▶️ Como usar

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

## 🧰 Requisitos

- Python 3.10 ou superior
- Windows
- Permissões de administrador para algumas ações de firewall
- Dependências listadas em requirements.txt

## 📦 Estrutura do projeto

- main.py: ponto de entrada da aplicação
- modules/cleanup.py: limpeza de arquivos temporários
- modules/firewall.py: regras e conexões do firewall
- modules/diagnostics.py: coleta de informações do sistema
- modules/hardware_services.py: integração com bibliotecas de hardware
- tests/: testes automatizados das principais áreas

## 📚 Documentação completa

A documentação detalhada da aplicação está disponível em [docs/index.md](docs/index.md).

## 🧪 Testes

Para rodar a suíte de testes:

```bash
pytest -q
```

## 🚀 Futuro: executável

Uma das próximas melhorias será a criação de um executável pronto para Windows, para que o projeto possa ser aberto sem precisar rodar o código manualmente via terminal.

Planejados para essa etapa:

- 📦 gerar um .exe para Windows;
- 🖱️ instalação mais simples para usuários finais;
- ⚡ abertura rápida do aplicativo sem dependências extras.

## ✅ Observações importantes

- O projeto é pensado para uso prático em ambientes Windows.
- A limpeza é conservadora e pode ignorar arquivos protegidos.
- Ações mais sensíveis de firewall funcionam melhor com privilégios elevados.
