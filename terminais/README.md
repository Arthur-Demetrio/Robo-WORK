# Terminais do Robo-WORK — ROS 2 Jazzy

Referência dos comandos utilizados no projeto (outubro/2026). **Não executados nem conferidos contra o notebook atual nesta publicação.** 

## Como usar
Em cada terminal do Linux Mint, copie o bloco da etapa correspondente. Execute na ordem abaixo, conferindo se cada processo iniciou normalmente. **Não rode todos os comandos em um único terminal.** 

Também é possível baixar esta pasta com o repositório e executar os arquivos `.sh` individualmente com `bash terminais/01-hardware.sh` etc., a partir da raiz do repositório. Os scripts não estão marcados como executáveis, por isso use `bash`.

**Atenção:** iniciar interfaces de navegação não é autorização para movimentar o robô. Antes dos testes físicos, revisar segurança, áreas livres, parada de emergência e estado do Collision Monitor.

## Terminal 1 — Arduino Mega / ponte ROS 2 / IMU

```bash
source /opt/ros/jazzy/setup.bash
source ~/robo_jazzy_ws/install/setup.bash
export ROS_DOMAIN_ID=0
ros2 launch robo_hardware hardware.launch.py
```

Arquivo: [01-hardware.sh](./01-hardware.sh)

## Terminal 2 — LiDAR e filtro de scan

```bash
source /opt/ros/jazzy/setup.bash
source ~/robo_jazzy_ws/install/setup.bash
export ROS_DOMAIN_ID=0
ros2 launch robo_lidar lidar_filter.launch.py
```

Arquivo: [02-lidar.sh](./02-lidar.sh)

## Terminal 3 — Localização / odometria

```bash
source /opt/ros/jazzy/setup.bash
source ~/robo_jazzy_ws/install/setup.bash
export ROS_DOMAIN_ID=0
ros2 launch robo_localization localization.launch.py
```

Arquivo: [03-localizacao.sh](./03-localizacao.sh)

## Terminal 4 — SLAM / mapeamento

```bash
source /opt/ros/jazzy/setup.bash
source ~/robo_jazzy_ws/install/setup.bash
export ROS_DOMAIN_ID=0
ros2 launch robo_navigation mapping.launch.py use_sim_time:=false
```

Arquivo: [04-mapeamento.sh](./04-mapeamento.sh)

## Terminal 5 — Nav2 / navegação

```bash
source /opt/ros/jazzy/setup.bash
source ~/robo_jazzy_ws/install/setup.bash
export ROS_DOMAIN_ID=0
ros2 launch robo_navigation navigation.launch.py use_sim_time:=false autostart:=true
```

Arquivo: [05-navegacao.sh](./05-navegacao.sh)

## Terminal 6 — Visualização RViz

```bash
source /opt/ros/jazzy/setup.bash
source ~/robo_jazzy_ws/install/setup.bash
export ROS_DOMAIN_ID=0
rviz2
```

Arquivo: [06-rviz.sh](./06-rviz.sh)

## Diagnóstico (terminal adicional)

```bash
source /opt/ros/jazzy/setup.bash
source ~/robo_jazzy_ws/install/setup.bash
export ROS_DOMAIN_ID=0
ros2 topic hz /scan_front
```

Outros comandos úteis (rode separadamente após preparar o ambiente):

```bash
ros2 topic hz /odom
ros2 topic echo /diagnostics
ros2 topic list
```

## Observações
- Os comandos de SLAM e Nav2 são registrados como os usados no projeto; **não confirmam que executar os dois simultaneamente está correto em qualquer configuração**.
- O `ROS_DOMAIN_ID=0` corresponde ao ambiente usado nas últimas sessões.
- Comandos antigos de ROS 2 Humble e `~/ros2_ws` não devem ser misturados com estes do Jazzy.
- Caso os nomes dos launch files tenham mudado, revisar os arquivos reais no notebook antes de atualizar esta documentação.
