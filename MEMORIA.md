# Memória de desenvolvimento

Este arquivo registra o que foi feito, como foi feito e o que ainda precisa ser melhorado no projeto.

## 2026-07-21 - Tema premium com botão fixo na barra lateral

### ✅ O que foi entregue
- Implementado um botão de alternância de tema fixo na barra lateral com ícone visual, permitindo mudar rapidamente entre modo claro e escuro.
- O tema escuro passou a usar uma paleta mais refinada e contrastada, com melhor diferenciação entre fundo, cards e elementos de navegação.
- A página de configurações foi simplificada para destacar o novo fluxo de tema sem duplicar o controle visual.

### ✅ Validação
- Testes de regressão adicionados e executados com sucesso para a alternância do tema.
- Compilação do módulo principal concluída sem erros.

## 2026-07-21 - Ajustes visuais nas ferramentas e nos cards do dashboard

### ✅ O que foi entregue
- Os botões da guia Ferramentas passaram a ter um visual mais próximo de botões tradicionais, com borda e destaque visual melhores.
- Os cards do dashboard agora recebem um contorno mais evidente no modo escuro, melhorando a identificação visual das blocagens principais.
- A abertura das ferramentas do Windows foi validada por teste automatizado para garantir que o fluxo continua chamando o utilitário correto.

### ✅ Validação
- Testes de regressão executados com sucesso para a abertura das ferramentas e para o novo estilo dos botões.
- Compilação do módulo principal concluída sem erros.


### ✅ O que foi entregue
- Implementado um botão de alternância de tema fixo na barra lateral com ícone visual, permitindo mudar rapidamente entre modo claro e escuro.
- O tema escuro passou a usar uma paleta mais refinada e contrastada, com melhor diferenciação entre fundo, cards e elementos de navegação.
- A página de configurações foi simplificada para destacar o novo fluxo de tema sem duplicar o controle visual.

### ✅ Validação
- Testes de regressão adicionados e executados com sucesso para a alternância do tema.
- Compilação do módulo principal concluída sem erros.

## 2026-07-21 - Guia de Hardware com atualização e exportação

### ✅ O que foi entregue
- Criada a guia de Hardware na interface com coleta detalhada de dados do computador para análise.
- Adicionados os botões "Atualizar lista" e "Salvar lista" para renovar os dados e exportá-los em JSON.
- A página passou a exibir informações mais completas de CPU, RAM, armazenamento, GPU, placa-mãe, sistema e sensores.

### ✅ Validação
- Teste de regressão adicionado para validar os botões e o salvamento da lista de hardware.
- Compilação do módulo principal concluída sem erros.

## 2026-07-21 - Limpeza segura com opções adicionais de Windows

### ✅ O que foi entregue
- Adicionadas novas opções de limpeza na central de manutenção para:
  - instalações antigas do Windows;
  - abertura da ferramenta Limpeza de Disco do Windows;
  - backup do registro do Windows para revisão manual.
- Itens sensíveis agora ficam desmarcados por padrão, reduzindo o risco de perda de arquivos ou credenciais.
- Os backups automáticos continuam sendo criados para as pastas limpas, com retenção de 30 dias.

### ✅ Validação
- Testes de regressão adicionados e executados com sucesso para as novas opções de limpeza.

## 2026-07-16 - Ajuste visual e rolagem da área de programas

### ✅ O que foi entregue
- Adicionada rolagem por roda do mouse na área de programas da guia Aplicativos.
- A lista passou a usar um painel branco com destaque azul, alinhado ao visual das demais guias.
- A barra de rolagem foi estilizada para combinar com a paleta azul do projeto.
- A atualização da scroll region foi refinada para evitar travamentos visuais ao renderizar a lista.

### ✅ Validação
- Teste de regressão adicionado para garantir a rolagem por mouse na área de programas.
- Execução de testes relacionada concluída com sucesso.

## 2026-07-16 - Interatividade de programas: desinstalar e abrir local

### ✅ O que foi entregue
- **Filtro de Drivers/Serviços como botão toggle**:
  - Botão "🔧 Mostrar Drivers/Serviços" que alterna entre mostrar lista completa e filtrada
  - Quando ativado, mostra "✓ Drivers/Serviços Ocultos"
  - Carrega e exibe a lista apropriada dinamicamente
  
- **Menu de contexto (clique direito)** em cada programa com opções:
  - 🗑 **Desinstalar programa**: Executa UninstallString do registro
  - 📂 **Abrir Local de Instalação**: Abre Explorer na pasta do programa
  - 📋 **Copiar Nome**: Copia nome do programa para clipboard
  - Opções desabilitadas (gray) quando não disponíveis (sem UninstallString ou InstallLocation)

- **Captura de informações adicionais** do registro:
  - `UninstallString`: Comando para desinstalar
  - `InstallLocation`: Caminho de instalação
  - Agora retornados pelo `InstalledProgramsService`

- **Dica visual de interatividade**: 
  - Texto cinzento abaixo da versão indicando "clique direito para desinstalar ou abrir local"

- **Métodos novos**:
  - `_show_program_context_menu()`: Cria e exibe menu de contexto
  - `_uninstall_program()`: Executa desinstalação
  - `_open_program_location()`: Abre pasta no Windows Explorer
  - `_copy_to_clipboard()`: Copia nome para clipboard
  - `_toggle_driver_filter()`: Alterna filtro drivers/serviços
  - Atualização de `_load_installed_programs()`: Carrega lista completa e filtra conforme necessário

### ✅ Validação
- Compilação: ✓ main.py e programs_service.py compilaram sem erros
- Testes: ✓ 16 testes passaram (test_maintenance_center.py + test_email_service.py)

### 📋 Detalhes Técnicos
- `InstalledProgramsService.get_installed_programs()`: Retorna também uninstall_string e install_location
- `InstalledProgramsService.uninstall_program()`: Usa subprocess para executar UninstallString
- `InstalledProgramsService.open_install_location()`: Usa os.startfile() no Windows
- Menu criado dinamicamente com tk.Menu() e renderizado onde o clique direito ocorreu
- Dicionário `self.programs_data` armazena uninstall_string e install_location de cada programa

## 2026-07-16 - Melhoria visual da página de Aplicativos e filtro inteligente

### ✅ O que foi entregue
- **Filtro inteligente automático**: Drivers e serviços do Windows são automaticamente removidos da lista de programas.
  - Padrões excluídos: nvidia, amd, intel, drivers, services, windows components, dotnet, vcredist, etc.
- **Visual aprimorado dos cards**: 
  - Cada programa agora exibe em um card elegante com nome (bold) e versão (cinza menor)
  - Checkbox visual melhorado com cores apropriadas
  - Borda sutil entre itens para melhor separação
  - Informações padronizadas (nome do programa e versão)
- **Contador de programas**:
  - Exibe quantidade total de programas disponíveis
  - Atualiza dinamicamente durante filtro de busca
  - Mostra quantos programas correspondem ao filtro
- **Melhoria na seção de selecionados**:
  - Lista numerada (1, 2, 3...) ao invés de apenas separada por quebras
  - Exibe ✓ e contador no início da lista
  - Mensagem "➜ Nenhum programa selecionado" quando vazio
- **Melhor descrição na página**: Menciona que drivers e serviços são automaticamente filtrados

### ✅ Validação
- Compilação: ✓ main.py compilou sem erros
- Testes: ✓ 16 testes passaram (test_maintenance_center.py + test_email_service.py)
- Funcionalidades não afetadas: ✓ Tests confirmam funcionamento

### 📋 Detalhes Técnicos
- Função `_is_windows_driver_or_service()`: Verifica padrões em nomes de programas para excluir drivers/serviços
- `_display_programs()`: Renderiza cards com layout melhorado, informações de versão, contador vazio
- `_apply_programs_filter()`: Atualiza contador e lista de filtrados
- `_load_installed_programs()`: Carrega programas filtrados + atualiza contador inicial
- `_update_selected_programs()`: Lista numerada com total selecionado

## 2026-07-16 - Implementação de gerenciamento de aplicativos instalados

### ✅ O que foi entregue
- Criada a página **"Aplicativos"** na navegação lateral, listando todos os programas instalados no Windows.
- Implementado filtro de programas em tempo real com campo de entrada e botão "Aplicar Filtro".
- Adicionado sistema de seleção com checkboxes para cada programa instalado.
- Criada visualização dos programas selecionados em tempo real na página.
- Adicionado botão "Limpar Seleção" para reset rápido.
- Integrada a persistência da seleção de programas em `report_settings` (salvo via `ReportSettingsManager`).
- Expandido o módulo `report.py` para incluir uma seção "APLICATIVOS SELECIONADOS" nos relatórios gerados.
- Integrada a passagem de programas selecionados pelo fluxo de manutenção até a geração do relatório.
- Adicionado suporte opcional a `selected_programs` no `MaintenanceCoordinator.run_maintenance()`.

### ✅ Validação
- Todos os módulos compilaram sem erros: `main.py`, `modules/report.py`, `modules/maintenance.py`.
- Aplicação iniciou com sucesso e não apresentou erros no carregamento da página de Aplicativos.
- Estrutura de persistência funcional: programas selecionados são salvos em `report_settings` e podem ser carregados na próxima sessão.

### 📋 Detalhes Técnicos
- **Serviço**: `InstalledProgramsService` (já existente) enumera programas do Windows Registry.
- **UI Page**: `_build_programs_page()` cria interface com Canvas scrollável para listar checkboxes.
- **Métodos auxiliares**:
  - `_load_installed_programs()`: carrega programas do serviço.
  - `_display_programs()`: renderiza checkboxes na UI.
  - `_apply_programs_filter()`: filtra programas por texto digitado.
  - `_update_selected_programs()`: atualiza lista e persiste em `report_settings`.
  - `_clear_selected_programs()`: limpa todas as seleções.
- **Report Integration**: seção "APLICATIVOS SELECIONADOS" adicionada em `report.py`, exibida entre "Resumo da Limpeza" e "RESULTADO".

## 2026-07-16 - Implementação completa do módulo de envio por e-mail

### ✅ O que foi entregue
- Criado um módulo independente de e-mail com a classe `EmailService`, responsável por carregar/salvar configuração, validar dados, formatar bytes, gerar assunto/corpo, testar envio, registrar log e verificar conexão.
- Integrado o fluxo de manutenção ao novo serviço, preservando o comportamento anterior e passando a tratar falhas de forma padronizada sem travar a interface.
- Expandida a página de configurações com campos seguros para API Key principal e reserva, remetente, destinatário, personalização de assunto/corpo, opção de envio automático, salvamento local para reenvio posterior e histórico recente.
- Adicionado teste automatizado cobrindo validação, formatação, fallback para API reserva, fila local e teste temporário do relatório.
- Implementado fallback de envio direto via API HTTP da Resend quando a biblioteca Python não está disponível, resolvendo o bloqueio de envio em ambientes sem a dependência instalada.

### ✅ Validação
- `pytest -q tests/test_email_service.py` passou com 7 testes.
- A suíte completa atingiu 54 testes aprovados e 1 falha relacionada ao ambiente Tk/Tcl ausente para a execução de testes de interface.

## 2026-07-15 - Correção do envio de relatório por e-mail

### ✅ O que foi ajustado
- Substituída a implementação antiga de e-mail por uma integração direta com a API da Resend usando o módulo padrão `urllib`.
- Ajustado o payload do anexo para o formato esperado pela API, com conteúdo em Base64.
- Adicionado o campo de remetente nas configurações de relatório e propagado esse valor para o fluxo de manutenção.
- Incluído teste de regressão cobrindo o uso do remetente configurado no envio automático.

### ✅ Validação
- `pytest -q tests/test_maintenance_center.py` passou com 4 testes.
- Correção no coletor de manutenção para usar os mesmos dados normalizados do dashboard inicial.
- Alterado o nome do relatório para usar apenas a data (`%Y-%m-%d`) para evitar acúmulo de relatórios do mesmo dia.
- Adicionado botão "Enviar Relatório" na aba de limpeza para enviar manualmente o último relatório gerado.
- Corrigido o formato do payload da API Resend:
  - Campo `"to"` agora é uma lista: `["email@example.com"]`
  - Campo `"html"` mudou para `"text"` para texto plano
  - Conteúdo do anexo em Base64 (correto)
- Adicionadas validações e mensagens de erro descritivas:
  - Avisa quando API Key não está configurada
  - Avisa quando email destinatário/remetente não estão configurados
  - Fornece instruções de como preencher as configurações
  - Recarrega as configurações do arquivo antes de enviar
- Adicionado link de referência na aba Configurações: https://resend.com/api-keys

## 2026-07-08

### O que foi feito
- Estrutura inicial do projeto criada em Python.
- Interface principal construída com Tkinter.
- Módulo de diagnóstico implementado para coletar dados básicos do sistema.
- Módulo de firewall implementado com funções para consultar estado, ativar/desativar e liberar portas.
- Módulo de limpeza criado para remover arquivos temporários e caches de aplicativos.
- Arquivo README criado com instruções de uso.

### Como foi feito
- A interface foi criada com Tkinter para funcionar como um utilitário desktop simples.
- O módulo de diagnóstico usa a biblioteca psutil para coletar CPU, RAM, disco e informações básicas do sistema.
- O firewall foi implementado com chamadas para o comando netsh do Windows.
- A limpeza usa arquivos temporários comuns do sistema e pastas de cache do usuário.

### Observações
- A versão inicial é funcional, mas ainda pode ser aprimorada.
- Ações de firewall podem exigir permissão administrativa.
- A limpeza deve ser usada com cuidado em ambientes onde arquivos temporários possam ser importantes.

### Próximos passos
- Melhorar o módulo de diagnóstico para ficar mais parecido com o Speccy.
- Adicionar suporte para GPU e placa-mãe.
- Melhorar a experiência visual da interface.
- Adicionar exportação dos dados para arquivo.

### Atualizações recentes
- Interface reorganizada para um painel moderno com navegação lateral.
- Dashboard agora exibe métricas essenciais em cards compactos de CPU, RAM, SSD e sistema.
- Página de detalhes redesenhada com seções expansíveis para facilitar a leitura.
- A coleta de hardware permanece intacta; apenas a apresentação foi atualizada.
- O card de sistema passou a mostrar a versão do Windows e o status de atualizações diretamente na interface.

### Pesquisa de bibliotecas para temperatura e saúde do SSD
- A biblioteca psutil pode ler temperatura da CPU quando o sistema expõe sensores, mas em muitos PCs Windows isso pode retornar N/A.
- A biblioteca pySMART foi testada como opção para leitura de SMART do SSD.
- Para que a leitura de SSD funcione de verdade, normalmente é necessário ter o utilitário smartctl instalado via smartmontools.
- A implementação atual faz a leitura de forma opcional, retornando N/A quando o sensor ou o backend não estiver disponível.

## 2026-07-10 - CHECKPOINT: Refatoração Dashboard e Fluxo de Dados Unificado

### ✅ O que foi completado
- **Dashboard Refatorado**: Interface transformada de layout tabbed para sidebar/dashboard moderno
- **Fluxo de Dados Unificado**: Implementação de arquitetura "single source of truth" (`self.data`)
- **Arquitetura de Widget Permanente**: Build phase única + Update phase contínua (sem destruição/recriação)
- **Sincronização Completa**: Mini-cards e main-cards sempre mostram dados idênticos
- **Testes Implementados**: 9/9 testes passando (regressão + unified data flow)

### 🏗️ Como foi implementado
- 5 builder methods criados: `_build_quick_metrics_frame()`, `_build_dashboard_cpu_card()`, `_build_dashboard_ram_card()`, `_build_dashboard_ssd_card()`, `_build_dashboard_system_card()`
- 5 update methods criados: `_update_quick_metrics()`, `_update_cpu_card()`, `_update_ram_card()`, `_update_ssd_card()`, `_update_system_card()`
- 1 método genérico para rows: `_update_rows_by_frames()` usa frame references pré-armazenadas
- Fluxo: `collect_hardware()` → `self.data = data` → `_render_dashboard(data)` → todos componentes atualizam sincronizados
- Referências permanentes armazenadas durante build: `self.quick_metrics`, `self.cpu_row_frames`, `self.ram_row_frames`, `self.ssd_row_frames`, `self.system_row_frames`

### 📊 Resultados obtidos
- ✅ Dashboard não treme ao atualizar (widgets mantêm referências)
- ✅ Mini-cards e main-cards sincronizados: CPU Temp "61°C" (mini) vs "61.2°C" (main) = mesma fonte
- ✅ Sem dados "Não disponível" quando informações existem
- ✅ Interface responsiva e estável
- ✅ Código limpo com single entry point para atualizações (`_render_dashboard()`)

### 📝 Arquivos criados/modificados
- `main.py`: Refatoração completa (build + update methods)
- `tests/test_unified_data_flow.py`: 5 novos testes de integração
- `tests/test_dashboard_refresh.py`: Regressão (widget count)
- `IMPLEMENTATION_SUMMARY.md`: Documentação da arquitetura nova

### ⚠️ Limpeza técnica pendente (OPCIONAL)
- Funções antigas não removidas: `_ensure_dashboard_structure()`, `_create_dashboard_card_state()`, `_update_dashboard_card_state()`, `_update_metric_widget()`, duplicate `_render_quick_status()`, duplicate `_render_info_page()`, estado antigo `self.dashboard_widget_states`
- Estas NÃO afetam funcionalidade, apenas clutter. Remover se necessário em futuro cleanup.

---

## 🔄 PRÓXIMAS FUNCIONALIDADES (A Implementar)

### 1. Dashboard - Coleta Automática
- [x] Carregar dados ao iniciar aplicativo (sem clique no botão "Atualizar")
- [x] Mostrar indicador "🔄 Coletando informações do sistema..."
- [x] Executar em thread background para não congelar UI
- [x] Atualizar todos os components automaticamente
- [x] Mensagem "✔ Dados atualizados com sucesso"

**Status**: ✅ COMPLETADO (2026-07-10)  
**Testes**: 6 novos testes passando  
**Como funciona**: Método `_run_initial_diagnostics()` agendado 300ms após UI renderizar

### 2. Dashboard - Atualização em Segundo Plano
- [x] Desabilitar botão Atualizar durante coleta
- [x] Mostrar indicador 🔄 "Coletando informações..."
- [x] Reabilitar quando terminar

**Status**: ✅ COMPLETADO (2026-07-10)  
**Testes**: 15 novos testes passando  
**Como funciona**: Animação de status com frames (pontos progressivos) + botão muda texto durante coleta

### 3. Dashboard - Atualização Periódica
- [ ] Adicionar configuração de intervalo automático
- [ ] Opções: 30s, 1m, 2m, 5m, 10m, Desativado
- [ ] Armazenar em settings
- [ ] Usar Thread para não travar UI
- [ ] Atualizar sem perder estado da interface

### 4. Firewall - Gerenciador Completo
- [ ] Listar portas abertas em tabela com: Porta, Protocolo, Processo, PID, Executável, Endereço Local, Remoto, Estado, Perfil, Regra
- [ ] Botão "Atualizar Lista"
- [ ] Ações por porta: Liberar, Bloquear, Remover Regra
- [ ] Cores por estado: LISTENING 🟢, ESTABLISHED 🔵, TIME_WAIT 🟡, CLOSE_WAIT 🟠, Erro 🔴

### 5. Firewall - Liberar Porta (Fluxo Completo)
- [ ] Validar entrada (porta + protocolo + nome)
- [ ] Verificar se porta já existe
- [ ] Se existir: perguntar "Deseja atualizar?"
- [ ] Se não: criar regra
- [ ] Confirmar sucesso: "✔ Porta X liberada com sucesso"
- [ ] Atualizar lista automaticamente

### 6. Firewall - Bloquear Porta
- [ ] Selecionar e bloquear porta
- [ ] Criar regra de bloqueio
- [ ] Atualizar lista
- [ ] Mensagem de sucesso

### 7. Firewall - Remover Regra
- [ ] Botão para excluir regra
- [ ] Atualizar lista
- [ ] Mensagem: "✔ Regra removida com sucesso"

### 8. Firewall - Pesquisa e Filtros
- [ ] Busca instantânea por: porta, processo, PID, nome, protocolo
- [ ] Filtros: Todos, TCP, UDP, LISTENING, ESTABLISHED, CLOSE_WAIT, TIME_WAIT, Somente Liberadas, Somente Bloqueadas

### 9. Firewall - Aba "Regras"
- [ ] Segunda aba: "Regras do Firewall"
- [ ] Listar: Nome, Porta, Protocolo, Status, Data Criação, Última Alteração
- [ ] Ações: Editar, Excluir, Ativar, Desativar

### 10. Firewall - Exportação
- [ ] Botão: Exportar Regras
- [ ] Formatos: CSV, JSON, TXT

### 11. Firewall - Log de Operações
- [ ] Painel inferior com histórico
- [ ] Registrar: Data, Hora, Operação, Resultado
- [ ] Exemplo: "17:30 - Porta 8080 liberada. ✔"

### 12. Firewall - Verificação Admin
- [ ] Verificar privilégios antes de operações
- [ ] Mensagem: "Esta operação requer permissões de administrador"
- [ ] Não permitir ação sem admin

### 13. UX - Responsividade
- [ ] Nenhuma operação deve travar interface
- [ ] Todas tarefas firewall em thread background
- [ ] Indicadores visuais durante processamento
- [ ] Desabilitar apenas botão da operação atual

## 2026-07-10 - Correção de estabilidade do firewall e inicialização

### ✅ O que foi ajustado
- Corrigido o problema de decodificação de saída do `netsh`/`netstat` ao usar `encoding='utf-8'` e `errors='replace'` no módulo de firewall.
- Ajustadas as ações de firewall para evitar exceções ao atualizar a interface a partir de threads em segundo plano.
- Adicionado teste de regressão para garantir que o módulo continue usando codificação segura.
- Redesenhado o dashboard para aproveitar melhor a largura disponível do conteúdo, deixando os cards mais compactos, alinhados e ocupando o espaço do painel sem áreas vazias.

### ✅ Validação
- `py -3 -m unittest tests.test_firewall_encoding` passou.
- `py -3 -m unittest discover -s tests` passou com 31 testes.
- A aplicação foi iniciada sem traceback relacionado ao firewall ou à inicialização.

## 2026-07-10 - Restauração da coleta automática do dashboard

### ✅ O que foi ajustado
- O fluxo de startup passou a usar a rota rápida do host .NET para preencher o dashboard logo no início.
- Foi adicionado um helper dedicado `_collect_hardware_payload()` para garantir que a coleta inicial use o caminho mais confiável e faça fallback para o collector tradicional se necessário.
- O timeout da coleta de placa-mãe foi reduzido para evitar travamentos na abertura do app.

### ✅ Validação
- `py -3 -m unittest tests.test_auto_initial_collection tests.test_background_update_ui tests.test_unified_data_flow tests.test_dashboard_refresh -v` passou com 28 testes.
- A coleta inicial agora retorna um payload válido em aproximadamente 3,7s no ambiente atual.
- Ajustes de dashboard aplicados para exibir mais detalhes nos cards e melhorar a quebra de texto nas linhas de informação.

## 2026-07-14 - Correção de diagnóstico de CPU

### ✅ O que foi ajustado
- Corrigido o processamento de sensores de CPU para priorizar leitura agregada de uso em vez de cargas por núcleo.
- Ajustada a seleção de temperatura do processador para preferir o sensor de pacote/CPU principal em vez de um núcleo isolado.
- O diagnóstico passou a usar o mesmo critério de seleção em múltiplas rotas de coleta do projeto.

### ✅ Validação
- `pytest -q` passou com 41 testes.

## 2026-07-15 - Documentação de publicação e guia do projeto

### ✅ O que foi ajustado
- Criada uma página de documentação detalhada em [docs/index.md](docs/index.md) com explicações sobre o funcionamento do projeto, instalação, uso das abas e solução de problemas.
- Atualizado o [README.md](README.md) para servir como landing page mais clara e profissional para o repositório.
- Documentado o fluxo de uso principal da aplicação para facilitar a adoção por novos usuários.
