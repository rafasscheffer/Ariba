MONITOR ARIBA x SAP BUSINESS ONE - V3
=====================================

OBJETIVO
--------
Validar apenas os ultimos 90 dias e, depois disso, trabalhar para frente.

A validacao inicial faz DUAS coisas:
1. importa os pedidos/versoes do Ariba dos ultimos 90 dias;
2. confere TODOS os pedidos unicos desse periodo no SAP B1 por NumAtCard.

Isso garante que o painel operacional nao seja apenas uma lista recente:
ele passa a saber, para todo o periodo validado, quais pedidos ja estao
encerrados e quais ainda exigem acompanhamento.

REGRA DE ENCERRAMENTO
---------------------
Um pedido so sai do painel quando TODOS os DocNum relacionados estiverem
em uma destas posicoes:
- FATURADO
- EXPEDIDO

Qualquer outro status continua aparecendo.
Pedido que existe no Ariba mas nao existe no SAP tambem aparece.

ARQUIVOS GERADOS
----------------
reports\painel.html
    Painel visual operacional.

reports\auditoria_90_dias.csv
    TODOS os pedidos conferidos Ariba x SAP.
    Pode abrir diretamente no Excel.

reports\pedidos_em_acompanhamento.csv
    Apenas pedidos que ainda exigem atencao.
    Pode abrir diretamente no Excel.

reports\historico_ariba_90_dias.csv
    Todos os registros/versoes retornados pelo Ariba.

reports\resumo_validacao.txt
    Resumo simples em texto.

data\monitor.db
    Banco SQLite completo.

data\backups\
    Quando a validacao de 90 dias e refeita, o banco anterior e salvo aqui.

PRIMEIRA EXECUCAO
-----------------
1. Execute setup.bat
2. Preencha o .env
3. Execute testar_conexoes.bat
4. Execute validar_90_dias.bat

IMPORTANTE:
validar_90_dias.bat recria a base operacional a partir dos ultimos 90 dias,
mas antes salva o banco anterior em data\backups.

Depois da validacao:
5. Execute abrir_painel.bat
6. Execute abrir_relatorios.bat

ROTINA NORMAL
-------------
Depois da validacao inicial, use:
    executar_monitor.bat

Ele:
- consulta os ultimos 7 dias do Ariba;
- detecta pedidos novos e novas versoes;
- revisita todos os pedidos que ainda exigem acompanhamento;
- atualiza o SAP;
- regenera os CSVs, TXT e painel.

AGENDAMENTO
-----------
Depois de validar manualmente:
    instalar_tarefas.bat

Cria:
- uma tarefa ao entrar no Windows;
- uma tarefa diaria as 13:30.

SEGURANCA
---------
O programa somente consulta.
Nao grava no SAP.
Nao confirma pedidos no Ariba.
O .env nao deve ir para o Git.
