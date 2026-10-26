# Registro técnico — 26/10/2026

Fonte de referência: pacote local `robo_2026-10-26.zip` e `robo_2026-10-26.md`, analisados em 26/10.

## Situação
- Recuperação rápida (BT + PoseProgressChecker 6 s): aplicada no robô.
- Alinhador v3.10 (START/FINISH com ângulo de chegada e aceitação de chegada a até 10 cm): instalado, ainda sem prova completa.
- Giro rápido (RotationShim 0,40 rad/s + polígonos do Collision Monitor): aplicado, gerou vai-e-volta na prova2.
- Correção do giro (`rotate_to_heading_once: true` e freio `-1.2`): preparada, **ainda não aplicada fisicamente**.
- Zonas de velocidade: simulação apenas, não aplicar sem calibração de odometria.

## Provas
- **Prova1:** 11/11 etapas, tarefa terminada em 4min25s. Distâncias finais das mesas: WS_1 8,7 cm, WS_3 7,1 cm, WS_2 8,9 cm, WS_1 8,2 cm. FINISH travou (tolerância angular, colisões/canto), intervenção manual.
- **Prova2:** cerca de 45 s de alternância entre shim e DWB, devido ao replanejamento e `rotate_to_heading_once: false`. Correção ainda depende de teste físico.
- **Testes locais do pacote:** `teste_patches.py`, `teste_v310.py`, `teste_encosto_no.py` e `teste_no_ros_inercia.py` executados em cópia isolada. Passaram os cenários nominais, com o cenário de bloqueio da travessia falhando de modo esperado.

## Próximo teste
1. Aplicar `patches/corrigir_giro_shim.py` no computador do robô **após verificar caminho/estado atual e backup**.
2. Compilar `robo_navigation` e reiniciar componentes relevantes.
3. Testar apenas **START → WS_1**, com supervisão e gravação.
4. Se houver apenas um giro e avanço, gravar **prova3** integral.
5. Em conflito do shim com DWB, usar `--desfazer` (correção e giro) e regressar à configuração anterior.

## Integração do pacote completo
Os arquivos originais do pacote de 26/10 devem entrar em diretório próprio `historico/2026-10-26/` na branch `desenvolvimento-20261026-provas-alinhador-v310`, sem substituir automaticamente a árvore de produção; o `nav2_params.yaml` do ZIP é **referência**, não instrução de sobrescrita. A cópia integral ainda depende de enviar os arquivos do ambiente local para esta branch.

Documentos: `README.md` e `resultados/RESULTADOS.md` no pacote de 26/10.
