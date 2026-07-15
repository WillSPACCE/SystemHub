# 🎯 PLANO DE IMPLEMENTAÇÃO - NOVAS FUNCIONALIDADES

**Data Início**: 2026-07-10  
**Checkpoint Anterior**: ✅ Dashboard Refatorado e Unificado  
**Próximo Checkpoint**: Após Fase 1 completa

---

## 📋 FASES DE IMPLEMENTAÇÃO

### ⭐ FASE 1: Dashboard Automático (Prioridade Máxima)

#### Objetivo
Carregar dados do hardware ao iniciar o aplicativo sem exigir clique no botão "Atualizar".

#### Tarefas
1. **Chamar coleta no `__init__` em background**
   - Arquivo: `main.py` → método `__init__`
   - Ação: Iniciar thread `run_diagnostics()` imediatamente após build da interface
   - Indicador: "Coletando informações do sistema..."
   - Após coleta: "✔ Dados atualizados com sucesso"

2. **Melhorar indicador visual durante coleta**
   - Adicionar label no header: `self.lbl_status`
   - Atualizar durante thread
   - Remover/Limpar após conclusão

3. **Não bloquear UI**
   - Já implementado via thread (verificar se está funcionando)
   - Thread deve completar sem congelar interface

4. **Validação**
   - Ao abrir app: dados já aparecem em mini-cards
   - Sem clique em "Atualizar"
   - Interface responsiva durante coleta

#### Código Estimado
- `_run_initial_diagnostics()`: thread setup
- `_update_status_label()`: feedback visual
- Modificar `__init__`: adicionar chamada inicial
- Modificar `run_diagnostics()`: suporte a indicador

#### Tempo Estimado: 30-45 min

---

### 🔄 FASE 2: Atualização em Segundo Plano

#### Objetivo
Feedback visual durante clique em "Atualizar" sem congelar interface.

#### Tarefas
1. **Desabilitar botão durante coleta**
   - `self.btn_atualizar.config(state="disabled")`
   - Mostrar 🔄 Coletando informações...
   - Reabilitar após conclusão

2. **Indicador visual melhorado**
   - Animação simples de spinner (ou "...")
   - Feedback de progresso

3. **Integração com coleta existente**
   - Usar thread já implementada
   - Adicionar callbacks antes/depois

#### Código Estimado
- Modificar callback do botão "Atualizar"
- Adicionar método `_show_loading()` e `_hide_loading()`

#### Tempo Estimado: 20-30 min

**Nota**: Usar mesma abordagem de indicador visual da Fase 1

---

### ⏰ FASE 3: Atualização Periódica Automática

#### Objetivo
Dashboard atualizar automaticamente em intervalo configurável (30s, 1m, 2m, 5m, 10m, Desativado).

#### Tarefas
1. **Dialog de Configurações**
   - Arquivo: `main.py` ou novo arquivo `config_dialog.py`
   - Checkbox: "Atualizar automaticamente"
   - Select: intervalo em segundos
   - Salvar em arquivo (`config.json` ou similar)

2. **Timer em thread**
   - Usar `threading.Timer` ou loop com `time.sleep()`
   - A cada intervalo: chamar `run_diagnostics()`
   - Não bloquear UI

3. **Persistência**
   - Salvar configuração em arquivo (JSON)
   - Restaurar ao iniciar app

4. **Parar/Iniciar**
   - Checkbox para ativar/desativar
   - Parar timer se desativado
   - Reiniciar se ativado

#### Código Estimado
- `SettingsDialog()`: nova classe com UI
- `_load_settings()`: ler config.json
- `_save_settings()`: escrever config.json
- `_start_auto_update()`: inicia timer
- `_stop_auto_update()`: para timer
- Threading manager para evitar múltiplos timers

#### Tempo Estimado: 1-1.5h

---

### 🔥 FASE 4: Firewall - Gerenciador Completo

#### Objetivo
Transformar aba Firewall em gerenciador funcional de portas abertas.

#### Tarefas Principais

##### 4.1 - Listagem de Portas Abertas
- **Fonte de Dados**: `netstat -an` ou biblioteca `psutil.net_connections()`
- **Tabela Columns**: Porta, Protocolo, Processo, PID, Executável, Endereço Local, Remoto, Estado, Perfil, Regra
- **Atualização**: Botão "Atualizar Lista"
- **Background**: Executar coleta em thread (não congelar UI)

##### 4.2 - Filtros e Pesquisa
- **Filtros**: Todos | TCP | UDP | LISTENING | ESTABLISHED | CLOSE_WAIT | TIME_WAIT | Somente Liberadas | Somente Bloqueadas
- **Pesquisa**: Busca instantânea por porta, processo, PID, protocolo
- **Atualização em Tempo Real**: Tabela atualiza enquanto digita

##### 4.3 - Cores por Estado
- LISTENING: 🟢 Verde
- ESTABLISHED: 🔵 Azul
- TIME_WAIT: 🟡 Amarelo
- CLOSE_WAIT: 🟠 Laranja
- Erro: 🔴 Vermelho

##### 4.4 - Ações por Porta
Para cada linha da tabela:
- **[Liberar]**: Cria regra de liberação no Firewall
- **[Bloquear]**: Cria regra de bloqueio
- **[Remover Regra]**: Remove regra existente
- Todas com confirmação e mensagem de sucesso

##### 4.5 - Verificação de Privilégios Admin
- Antes de qualquer ação: `ctypes.windll.shell32.IsUserAnAdmin()`
- Se não admin: Mostrar aviso "Requer permissões de administrador"
- Desabilitar botões até executar como admin

#### Código Estimado
- Nova classe `FirewallTab()` (ou expandir código existente)
- Métodos:
  - `_get_open_ports()`: coleta portas
  - `_populate_table()`: preenche tabela
  - `_filter_table()`: filtra por critério
  - `_search_table()`: pesquisa instantânea
  - `_liberar_porta()`: cria regra liberação
  - `_bloquear_porta()`: cria regra bloqueio
  - `_remover_regra()`: remove regra
  - `_check_admin()`: verifica privilégios
  - `_show_message()`: mensagem amigável

#### Tempo Estimado: 4-5h

---

### 📊 FASE 5: Firewall - Recursos Avançados

#### Objetivo
Completar gerenciador com funcionalidades profissionais.

#### Tarefas

##### 5.1 - Liberar Porta (Fluxo Completo)
```
Usuário preenche: Porta + Protocolo + Nome da Regra
↓
Validar dados (porta 1-65535, protocolo TCP/UDP)
↓
Verificar se porta já possui regra
↓
Se sim: "Essa porta já está liberada. Deseja atualizar?"
   - Sim → Atualizar regra
   - Não → Cancelar
↓
Se não: Criar regra
↓
Confirmar: "✔ Porta 25565 liberada com sucesso. Regra criada no Firewall."
↓
Atualizar lista automaticamente
```

##### 5.2 - Aba "Regras do Firewall"
- Segunda aba na seção Firewall
- Listar: Nome, Porta, Protocolo, Status (Ativa/Inativa), Data Criação, Última Alteração
- Ações: Editar, Excluir, Ativar, Desativar

##### 5.3 - Exportação
- Botão: "Exportar Regras"
- Formatos: CSV, JSON, TXT
- Dialog para escolher local

##### 5.4 - Log de Operações
- Painel inferior na aba Firewall
- Registrar: Data, Hora, Operação, Resultado
- Exemplo:
  ```
  17:30 - Porta 8080 liberada. ✔
  17:32 - Porta 3306 bloqueada. ✔
  17:40 - Regra removida. ✔
  ```
- Limpar log ou salvar em arquivo

#### Código Estimado
- Dialog nova: `LibrarPortaDialog()`, `ExportarDialog()`
- Métodos adicionais para validação, export, log
- Database/arquivo para armazenar histórico de operações

#### Tempo Estimado: 2-3h

---

## 📈 Arquitetura Proposta (Firewall)

```
FirewallTab (nova classe)
├── UI Layout
│   ├── Header (Botões: Atualizar, Liberar, Bloquear, Exportar)
│   ├── Filtros (Dropdown + Checkbox)
│   ├── Pesquisa (Entry + busca instantânea)
│   ├── Tabela de Portas (Treeview ou Canvas)
│   ├── Aba "Regras" (segunda aba)
│   └── Log de Operações (Painel inferior)
│
├── Data Layer
│   ├── _get_open_ports()
│   ├── _get_firewall_rules()
│   └── _get_process_name(pid)
│
├── Operations Layer
│   ├── _liberar_porta(port, protocol, rule_name)
│   ├── _bloquear_porta(port, protocol)
│   ├── _remover_regra(rule_name)
│   ├── _ativar_regra(rule_name)
│   ├── _desativar_regra(rule_name)
│   └── _exportar_regras(format, filepath)
│
└── UI Update Layer
    ├── _refresh_table()
    ├── _apply_filters()
    ├── _search_table()
    ├── _update_colors()
    ├── _log_operation()
    └── _show_confirmation()
```

---

## 🧵 Threading Strategy

Todas operações pesadas em thread:

```python
def _operation_async(self, func, on_complete=None):
    """Executa função em thread e callback ao completar"""
    def thread_worker():
        try:
            result = func()
            if on_complete:
                self.after(0, lambda: on_complete(result))
        except Exception as e:
            self.after(0, lambda: self._show_error(str(e)))
    
    thread = threading.Thread(target=thread_worker, daemon=True)
    thread.start()
```

---

## ✅ Checklist de Validação

### Dashboard Automático
- [ ] Dados aparecem sem clique em "Atualizar"
- [ ] Indicador "Coletando..." aparece e desaparece
- [ ] Interface não congela
- [ ] Mensagem de sucesso exibida

### Firewall
- [ ] Tabela popula com portas reais
- [ ] Filtros funcionam (TCP, UDP, estados)
- [ ] Pesquisa instantânea funciona
- [ ] Cores corretas por estado
- [ ] Botões Liberar/Bloquear funcionam
- [ ] Log registra operações
- [ ] Admin check funciona
- [ ] Exportação gera arquivo

---

## ⚠️ Dependências Externas Necessárias

| Recurso | Método | Status |
|---------|--------|--------|
| Coleta de Portas | `psutil.net_connections()` ou `netstat` | ✅ Existente |
| Firewall Windows | `netsh advfirewall` | ✅ Existente |
| Processos | `psutil.Process()` | ✅ Existente |
| Admin Check | `ctypes.windll.shell32.IsUserAnAdmin()` | ⏳ Novo |
| Threading | `threading` stdlib | ✅ Existente |

---

## 📝 Notas Importantes

1. **Executar como Admin**: Operações firewall precisam privilégios
2. **Tratamento de Erros**: Toda operação deve ter try/except com mensagem amigável
3. **Threading**: Nunca atualizar UI de thread diretamente, usar `self.after()`
4. **Segurança**: Validar inputs antes de passar para shell commands
5. **Performance**: Limitar refresh a 1x por segundo máximo
6. **Compatibilidade**: Windows only (já é o escopo do projeto)

---

**Documento criado**: 2026-07-10  
**Próxima ação**: Começar Fase 1 (Dashboard Automático)
