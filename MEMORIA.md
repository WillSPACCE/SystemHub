# Memória de desenvolvimento

Este arquivo registra o que foi feito, como foi feito e o que ainda precisa ser melhorado no projeto.

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
