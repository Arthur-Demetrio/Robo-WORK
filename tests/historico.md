# Histórico consolidado de testes — observações anteriores

> Síntese retrospectiva de conversas e diagnósticos. Datas e métricas precisam ser reconciliadas com os logs originais no notebook. Uma alteração de parâmetro **não equivale** a resultado validado.

| Data (2026) | Cenário | Observação | Estado |
|---|---|---|---|
| 18/09 | Mecanum em piso | Após correção física, deslocamento lateral funcionou; rotação de 90° permaneceu incompleta em algumas tentativas | Parcial |
| 05–07/10 | Nav2/corredores | Trajetos com progresso positivo; houve goal failed e dúvida sobre folga traseira real versus RViz | Misto; rever logs |
| 09/10 | Parâmetros de controle | Giro final aparentou mais rápido; percurso em zigue-zague no corredor | Ajustes pendentes |
| 10/10 | DDS sem Wi-Fi | Uso forçado de UDPv4 associado à perda de tópicos; configuração foi revertida | Reverificar offline |
| 13–14/10 | Recuperação em quinas | Relatados 6 goals concluídos, 2 escapes laterais, 47 'No valid trajectories', 18 'Failed to make progress' e 103 STOP do Collision Monitor | Resultados relatados, não reproduzidos |
| 13–14/10 | Spin progressivo | Comando angular registrado; em testes o robô não girou, com bloqueio VelocityPolygonStop | Falha em investigação |
| 15–16/10 | Bancada e exploração | Discussão de estratégia sem mapa prévio e identificação de bancada por múltiplas observações | Planejamento, **não teste físico validado** |
| 21/10 | Travessia LiDAR com alinhador v3.4 | Ida: 3 medições e alinhamento ~5 s; volta: 1 medição e alinhamento ~1 s; ambas as travessias ~7 s; sem bloqueios observados | Melhor resultado relatado até a data; conferir bags para validação |

## Referência do teste de travessia de 21/10/2026

- Código: commit [`5576380`](https://github.com/OttavioSilva/Robo-WORK/commit/5576380), integrado pelo [PR #7](https://github.com/OttavioSilva/Robo-WORK/pull/7).
- Arquivos alterados: alinhador v3.4, parâmetros Nav2/Collision Monitor, árvore de comportamento, geometria e log do smart_spin, medição de escape por `/odom`.
- Medições e tempos informados pelo responsável pelo teste; bags e logs não foram reanalisados neste registro.
- Próxima validação: repetir ida e volta de diferentes posições e orientações e verificar consistência do alinhamento, folgas e bloqueios.

## Interpretação
Os números acima foram relatados em sessões passadas e não representam comparativo controlado. Conferir período amostral, parâmetros e condições físicas antes de traçar indicadores. Evitar extrapolar sucesso de um cenário para competição.

## Registro de novos testes
Usar o [modelo](../docs/modelo-teste.md), anexando links para evidências e commit testado. Nome recomendado: `AAAA-MM-DD_cenario_numero.md`.
