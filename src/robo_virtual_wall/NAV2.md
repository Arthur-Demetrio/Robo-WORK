# Parede de fita no Nav2 Jazzy

O detector publica segmentos métricos atuais em `base_link` somente com
`homography_file` validado. A prévia não alimenta a navegação. `tape_keepout`
transforma cada observação para o frame de `/map` pelo TF no timestamp da imagem.
Três observações consecutivas compatíveis (extremos até 8 cm, ordem reversível)
confirmam um trecho. Quadros repetidos não contam; perda de observação, TF ausente
ou intervalo maior que 0,5 s reiniciam a confirmação pendente. Observações antigas,
futuras ou não métricas são rejeitadas.

Trechos confirmados permanecem na memória até limpar ou reiniciar o nó, mesmo
quando a fita sai da câmera. Não são apagados pelos raios do LiDAR. São publicados
como OccupancyGrid 0/100 em `/virtual_wall/keepout_mask`, com metadados de tipo 0 em
`/virtual_wall/filter_info`, ambos reliable/transient-local. A máscara acompanha a
origem, resolução e expansão do mapa, inclusive origem girada. Não modifica `/map`
nem a localização. Limite de 2000 segmentos e 4 milhões de células, configuráveis.

`navigation.launch.py virtual_walls:=true` inicia esse nó e carrega
`virtual_wall_filters.yaml`, com KeepoutFilter no global e no local e uma inflação
adicional após o filtro (raio 55 cm, fator 5). Os plugins normais de LiDAR e mapa
permanecem. Filtros rodam depois das camadas normais: a inflação normal não basta
para a máscara. Fonte: documentação oficial Jazzy:
https://docs.nav2.org/jazzy/configuration_and_development/configuration_guide/core_servers/costmap_2d/costmap_filters/keepout_filter/

## Calibração que falta no robô

1. Confirmar a origem `base_link` física. Medir x/y da origem frontal branca nesse
   frame. O footprint tem frente x=0,365 m, mas isso não comprova a posição da
   borda usada na trena. Os eixos da referência frontal devem estar alinhados aos
   do robô: x frente, y esquerda. A ferramenta abaixo só muda a origem.
2. Conferir pelo menos três pontos independentes dentro da área calibrada,
   distribuídos também lateralmente, com câmera fixa. Usar centros de marcas
   pontuais, não cruzamentos instáveis de fita longitudinal. Registrar pixels da
   imagem original 640x480 e medidas em metros da referência frontal. Não reutilizar
   as quatro cruzes de ajuste. O arquivo de verificações tem listas `pixels` e
   `metres` correspondentes, cada uma com pares `[x,y]`.
3. Converter com as medidas reais. Exemplo de estrutura do comando (os valores
   em maiúsculas são substituídos pelas medidas, não copiar literalmente):

```bash
ros2 run robo_virtual_wall validate_tape_calibration \
  --preview src/robo_virtual_wall/calibration/front_preview_20261106_repositioned.json \
  --checks verificacoes_medidas.json \
  --front-x X_MEDIDO_EM_METROS --front-y Y_MEDIDO_EM_METROS \
  --output src/robo_virtual_wall/calibration/front_base_link_validated.json
```

A ferramenta exige pelo menos 10 cm de distribuição longitudinal, 15 cm lateral,
pontos não colineares, dentro do domínio e erro máximo de 2 cm. Cria outro arquivo,
sem sobrescrever a prévia. Não corrige distorção nem certifica toda a região;
conferir mais pontos/ângulos e iluminação. Nunca editar apenas `validated=true`.

## Iniciar após validar

Compilar no workspace efetivamente usado no robô; os scripts operacionais antigos
podem apontar para `~/robo_jazzy_ws` em vez de `~/Robo-WORK`.

```bash
cd ~/Robo-WORK
source /opt/ros/jazzy/setup.bash
colcon build --packages-up-to robo_navigation
source install/setup.bash
```

Encerrar a prévia e o Nav2 anterior para evitar disputa da câmera/nós duplicados.
Com mapa/localização/TF já disponíveis, iniciar:

```bash
ros2 launch robo_navigation tape_navigation.launch.py \
  homography_file:="$HOME/Robo-WORK/src/robo_virtual_wall/calibration/front_base_link_validated.json"
```

O launch recusa calibração preliminar antes de iniciar os componentes. Se o
detector métrico já estiver iniciado separadamente, usar apenas:

```bash
ros2 launch robo_navigation navigation.launch.py virtual_walls:=true
```

No RViz, adicionar Map `/virtual_wall/keepout_mask` (durabilidade Transient Local),
os costmaps global/local e o footprint. Primeiro conferir parado a posição da
barreira e a inflação. Depois testar planejamento para um objetivo além da fita:
a rota deve contornar o trecho confirmado ou falhar se ele bloquear a passagem.
Isso ainda precisa de teste real no robô; os testes automatizados não certificam
frenagem, percepção ou toda a cadeia Nav2.

Limpar os trechos confirmados e pendentes:

```bash
ros2 service call /tape_keepout/clear std_srvs/srv/Empty '{}'
```

Se a fita continuar visível, será confirmada novamente. Limpar sem a câmera vendo
a fita quando o propósito for removê-la do mapa de teste.

## Limites operacionais

- A região atual só cobre 20–45 cm à frente da referência branca e ±15 cm de lado.
  Fita fora dela continua sendo detectada em pixels, mas não vira obstáculo métrico.
  Para maior antecedência/largura, medir e validar uma região maior, sem extrapolar H.
- Meia largura de parede padrão 5 cm: contempla metade da fita e incerteza; não é
  o raio do robô. Inflação/footprint continuam necessários. Ajustar pela fita real.
- Trechos alinhados com lacunas até 40 pixels podem ser unidos; testar falsos
  positivos com outros objetos vermelhos/brancos do cenário da competição.
- Memória é da sessão. Falsos positivos confirmados exigem limpeza. Não há remoção
  seletiva, associação semântica global ou correção de paredes após loop closure.
  Após relocalização/reset do mapa no mesmo frame, limpar e observar novamente.
- Uma falha de câmera não é convertida em comando de parada. Não há intertravamento
  de velocidade por saúde da visão; o Collision Monitor de LiDAR não vê fita plana.
- Alinhador, travessias e recoveries que publicam velocidade diretamente podem não
  consultar esses costmaps. Esta integração restringe o planejamento/controle Nav2;
  não garante que todo movimento externo ao Nav2 respeite a fita.
- Não foram assumidas regras específicas da competição; confirmar a identificação
  vermelho/branco e os limites proibidos com a organização da modalidade.

## Ativação com as conferências desta sessão (06/11/2026)

`calibration/front_base_link_validated.json` foi gerado por translação de +0,365 m
em X da homografia frontal 640x480. O usuário confirmou que a borda branca é a
frente do footprint. `field_checks_20261106.json` registra os testes independentes
relatados: 25/35/40 cm com leituras 24,5/34,9/40,0 cm e ponto (35 cm, −10 cm)
com leitura (35,4 cm, −10,0 cm). Não foram fabricados pixels para essas medidas.
A validação usa leituras de tela conferidas pelo usuário, não resíduos de
reprojeção recalculados nem teste de estabilidade temporal. O erro longitudinal
máximo relatado é 5 mm e o erro do ponto lateral é 4 mm. A verificação lateral
independente cobre apenas o lado direito; o esquerdo permanece sem teste novo.
Isso habilita o comissionamento estático no domínio original, não certifica
comportamento em movimento nem distâncias fora do domínio.

A função `base_calibration_from_field_checks` registra explicitamente esse método
e escopo. A ferramenta de calibração por pixels continua exigindo seus próprios
pontos distribuídos; nenhum requisito dela foi reduzido para aceitar dados falsos.

Para usar o launch/parâmetros/BT operacionais de `~/robo_jazzy_ws`, com apenas o
pacote novo de visão sobreposto:

```bash
cd ~/Robo-WORK
./terminais/11-ativar-fita-nav2.sh
```

Esse comando abre navegação/visão e um RViz dedicado aos costmaps. Encerra por
SIGINT a instância anterior de `virtual_wall` para liberar a câmera, sem parar a
base ROS. Recusa iniciar outra instância se controller_server/planner_server ou
tape_keepout já estiverem ativos. O script não envia objetivos nem velocidades.
O launch operacional existente inclui suas rotinas de alinhamento/recovery, cujas
limitações quanto a movimentos fora do Nav2 continuam descritas acima.

O launch `robo_virtual_wall operational_tape.launch.py` mescla somente os filtros
em uma cópia temporária do YAML operacional e inclui o launch operacional com essa
cópia. Não regrava os parâmetros originais, nem muda BT ou remapeamentos de
velocidade. A cópia temporária é removida ao encerrar o launch. O RViz fornecido
não inclui ferramenta de envio de objetivo; inspecionar a parede primeiro.

Manter hardware, LiDAR, localização e SLAM em execução. A fita precisa cruzar o
quadrilátero calibrado para gerar máscara. No RViz, verificar `Parede de fita -
mascara` e os dois costmaps; desligar alternadamente os displays para distinguir
as camadas sobrepostas. A parede deve permanecer quando sai da imagem. O teste
em movimento/planejamento real ainda precisa ser executado no robô. Testes locais
usam quadros sintéticos, calibração real e TF simulado: não comprovam transporte
DDS, TF real ou carregamento dos plugins em execução na sessão gráfica.

## Estabilidade de confirmação

A máscara confirma a mediana de três observações, comparadas à primeira amostra e
à mediana corrente, com tolerância de 2,5 cm e variação de orientação até 10 graus.
Isso evita que uma sequência de pequenas mudanças confirme uma posição que deriva
entre quadros. Trechos menores que 8 cm, frequentes na borda do domínio calibrado,
são descartados na máscara. Esses valores são parâmetros de tape_keepout:
`confirmation_tolerance_m` e `min_segment_length_m`.

Uma observação menor contida numa parede já confirmada não cria outra parede.
Paredes confirmadas continuam fixas no frame map; mudanças de posição reais ou
saltos da localização não são corrigidos por essa filtragem. A associação usa
2,5 cm transversalmente e o limite de orientação; a tolerância de extremos para
paredes já confirmadas permanece 8 cm. Movimento do robô é compensado pelo TF antes
dessa associação. Não altera os dados atuais publicados pelo detector.

O RViz de teste inicia com `Segmentos metricos da fita` desmarcado: esse display
mostra observações instantâneas, que podem oscilar mesmo com máscara confirmada
estável. Ativá-lo quando for útil diagnosticar a visão. Não confundir os segmentos
atuais com a máscara persistente. Após substituir o código, reiniciar apenas a
integração e RViz; não é necessário reiniciar hardware ou SLAM.

### TF ligeiramente posterior à imagem

`tape_keepout` mantém uma fila limitada a 16 imagens pendentes quando o TF no
instante da captura ainda não está disponível. Um timer de 20 ms tenta novamente,
sem bloquear o executor e sem substituir pelo TF mais recente. As imagens continuam
sujeitas ao limite de idade de 0,5 s. A confirmação pendente é descartada quando a
imagem expira; o timestamp só é consumido depois da transformação bem-sucedida.
Isso trata atrasos curtos do TF, não corrige deriva ou erro de localização.
