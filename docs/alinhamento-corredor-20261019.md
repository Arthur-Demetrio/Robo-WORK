# Geometry — alinhamento antes do corredor (19/10/2026)

**Branch de teste:** `feature/corredor-alinhamento-20261019`. Nada foi alterado em `main`, na BT ou no Collision Monitor em execucao.

## Implementado
- `geometry_corridor_geometry.py`: examina o caminho global no mapa do SLAM, procura paredes dos dois lados e calcula eixo, largura aproximada e uma posicao de alinhamento FORA do corredor. Se nao houver observacao suficiente, nao inventa ponto nem executa navegacao.
- `geometry_corridor_staging.py`: usa o planner do Nav2, mostra o ponto de alinhamento e salva JSON. **Padrao: so previa**. Com `--execute-stage`, confirma e manda o Nav2 navegar somente ate o ponto. Com `--continue-to-goal`, exige uma segunda confirmacao apos verificar a pose, para tentar a travessia pelo Nav2 normal.
- `geometry_collision_watch.py`: grava diretamente mudancas do `CollisionMonitorState`, comandos de entrada/saida e tamanho do poligono visualizado, em CSV. Nao publica velocidades.
- `geometry_set_deadband.py`: validacao e aplicacao REVERSIVEL da zona morta linear [0.005, 0.005] mantendo 0.015 angular; salva backup do YAML e requer restart do Nav2.
- `tests/test_corridor_geometry.py`: casos sinteticos de corredor reto, corredor girado, area aberta sem corredor, mapa desconhecido e disco de giro obstruido.

## Instalacao: baixar sem mudar a branch atual no ThinkPad

```bash
cd ~/Robo-WORK
git fetch origin feature/corredor-alinhamento-20261019
REF=origin/feature/corredor-alinhamento-20261019
mkdir -p ~/robo_jazzy_ws/scripts ~/robo_jazzy_ws/tests
for f in geometry_corridor_geometry.py geometry_corridor_staging.py geometry_collision_watch.py geometry_set_deadband.py; do
    git show "$REF:scripts/$f" > ~/robo_jazzy_ws/scripts/"$f"
done
git show "$REF:tests/test_corridor_geometry.py" > ~/robo_jazzy_ws/tests/test_corridor_geometry.py
python3 -m compileall -q ~/robo_jazzy_ws/scripts/geometry_corridor*.py ~/robo_jazzy_ws/scripts/geometry_collision_watch.py ~/robo_jazzy_ws/scripts/geometry_set_deadband.py
python3 -m unittest discover -s ~/robo_jazzy_ws/tests -p 'test_corridor_geometry.py' -v
```

Esse processo nao da checkout nem altera `~/Robo-WORK/src`.

## Persistir deadband — com Nav2 parado

```bash
python3 ~/robo_jazzy_ws/scripts/geometry_set_deadband.py
python3 ~/robo_jazzy_ws/scripts/geometry_set_deadband.py --apply
```

Aplique somente se o preview mostrar o YAML correto. Depois reinicie o Nav2 e confirme:

```bash
ros2 param get /velocity_smoother deadband_velocity
```

Nao altere a zona morta angular sem uma calibracao fisica separada.

## Primeiro teste: preview da posicao de alinhamento

Ligue hardware, SLAM, Nav2 e Collision Monitor. No RViz escolha a ferramenta **Publish Point** para identificar as coordenadas de uma posicao DO OUTRO LADO do corredor; anote x e y. NAO envie ainda um Nav2 Goal concorrente.

```bash
source /opt/ros/jazzy/setup.bash
source ~/robo_jazzy_ws/install/setup.bash
export ROS_DOMAIN_ID=0
python3 ~/robo_jazzy_ws/scripts/geometry_corridor_staging.py \
  --goal-x X_REAL --goal-y Y_REAL
```

Substitua `X_REAL` e `Y_REAL` pelos numeros medidos no RViz. Se o mapa nao mostrar duas paredes confiaveis, a deteccao recusa a manobra. Nenhum motor e acionado no preview.

## Teste supervisionado: aproximacao, sem entrar no corredor

Apenas apos conferir no RViz o ponto calculado e sua folga real, robô fisicamente supervisionado, sem outra meta ativa:

```bash
python3 ~/robo_jazzy_ws/scripts/geometry_corridor_staging.py \
  --goal-x X_REAL --goal-y Y_REAL --execute-stage
```

O programa pede `ALINHAR` e envia SOMENTE essa meta ao Nav2. Verifica os ciclos de vida do Collision Monitor, smoother e BT. Ao chegar mede erro de posicao/rumo com TF. Se a pose for inadequada, termina, sem tentar a passagem.

## Teste opcional: etapa final, com confirmacao separada

```bash
python3 ~/robo_jazzy_ws/scripts/geometry_corridor_staging.py \
  --goal-x X_REAL --goal-y Y_REAL --execute-stage --continue-to-goal
```

Exige confirmacao inicial `ALINHAR` e, APOS alinhar, `ATRAVESSAR`. A passagem utiliza a BT/Nav2 atuais e Collision Monitor ativo; **nao substitui recuperacao**. Interrompa imediatamente caso se aproxime de obstaculos. Nunca teste sem supervisao e mecanismo de corte de energia ao alcance.

## Diagnostico concomitante

```bash
python3 ~/robo_jazzy_ws/scripts/geometry_collision_watch.py
```

O monitor mostra `STOP` e dados de entrada/saida; o nome do poligono principal pode permanecer `VelocityPolygonStop`. A geometria publicada pode ser vazia quando o comando esta parado. O monitor nao presume o nome interno do subpoligono.

## Limites atuais

- O procedimento exige SLAM parcialmente construido e uma rota global viavel. **Nao identifica corredores antes de observa-los**.
- Usa mapa de ocupacao; atualizacao do mapa e costmaps podem divergir. Uma area aparentemente livre no SLAM nao e comprovacao optica instantanea.
- O circulo de 53 cm em torno da posicao intermediaria e uma verificacao conservadora de espaco mapeado, nao um certificado de segurança.
- `Retreat & Align` existente continua **diagnostico**. Nenhuma re automatica, escape lateral ou microgiro bruto foi ligado a BT: o LiDAR dianteiro possui regioes traseiras ocluidas e ja houve contato fisico na quina.
- Nao foi modificada a BT atual `navigate_to_pose_corridor.xml`, nem o footprint, nem os poligonos de Collision Monitor ou seus topicos.
- Se o detector falhar, recolha mapa/RViz e registre a recusa; nao diminua a margem apenas para forcar uma manobra.

## Reverter

- Scripts: podem ser removidos do workspace; nao alteram nada fora dele.
- Deadband: copie de volta `nav2_params.yaml.bak_deadband_...` e reinicie o Nav2.
- Branch GitHub isolada; nenhum merge e necessario para testar.
