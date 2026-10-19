#!/usr/bin/env python3
"""Planejamento de ponto de alinhamento para corredor observado no mapa SLAM.

Padrao: SOMENTE PREVIA. --execute-stage envia apenas uma meta intermediaria
ao Nav2, com confirmacao humana, sem entrar no corredor nem comandar motores
diretamente. Nao executa re, giro manual ou escape lateral.
"""
import argparse
import json
import math
import time
from datetime import datetime
from pathlib import Path

import rclpy
from rclpy.duration import Duration
from rclpy.time import Time
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import OccupancyGrid
from tf2_ros import Buffer, TransformListener
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult

from geometry_corridor_geometry import Grid, stage_for_path


def yaw(q):
    return math.atan2(2 * (q.w * q.z + q.x * q.y),
                      1 - 2 * (q.y * q.y + q.z * q.z))


def diff_angle(a, b):
    return math.atan2(math.sin(a - b), math.cos(a - b))


def stamped_pose(nav, x, y, a):
    p = PoseStamped()
    p.header.frame_id = "map"
    p.header.stamp = nav.get_clock().now().to_msg()
    p.pose.position.x = float(x)
    p.pose.position.y = float(y)
    p.pose.orientation.z = math.sin(a / 2)
    p.pose.orientation.w = math.cos(a / 2)
    return p


def get_tf_pose(buffer):
    t = buffer.lookup_transform("map", "base_link", Time())
    return (t.transform.translation.x,
            t.transform.translation.y,
            yaw(t.transform.rotation))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--goal-x", type=float, required=True)
    parser.add_argument("--goal-y", type=float, required=True)
    parser.add_argument("--goal-yaw-deg", type=float, default=0.0)
    parser.add_argument("--execute-stage", action="store_true")
    parser.add_argument("--timeout", type=float, default=120.0)
    args = parser.parse_args()

    rclpy.init()
    navigator = BasicNavigator()
    buffer = Buffer()
    listener = TransformListener(buffer, navigator)
    latest_map = [None]

    qos = QoSProfile(
        depth=1,
        reliability=ReliabilityPolicy.RELIABLE,
        durability=DurabilityPolicy.TRANSIENT_LOCAL,
    )
    sub = navigator.create_subscription(
        OccupancyGrid, "/map",
        lambda msg: latest_map.__setitem__(0, msg), qos
    )

    try:
        print("Aguardando /map e TF map->base_link...", flush=True)
        deadline = time.monotonic() + 18
        start = None
        while time.monotonic() < deadline:
            rclpy.spin_once(navigator, timeout_sec=0.2)
            try:
                start = get_tf_pose(buffer)
            except Exception:
                pass
            if latest_map[0] is not None and start is not None:
                break
        if latest_map[0] is None or start is None:
            raise RuntimeError("Sem mapa SLAM atual ou TF map->base_link; nao mover")

        m = latest_map[0]
        map_age = (navigator.get_clock().now() -
                   Time.from_msg(m.header.stamp)).nanoseconds / 1e9
        if map_age < -0.5 or map_age > 12.0:
            raise RuntimeError("Mapa muito antigo ou relogio incorreto: %.2fs" % map_age)
        if m.header.frame_id != "map":
            raise RuntimeError("Frame de mapa inesperado: " + m.header.frame_id)

        print("Pedindo caminho global para (%.2f, %.2f)..."
              % (args.goal_x, args.goal_y), flush=True)
        origin = stamped_pose(navigator, *start)
        final = stamped_pose(navigator, args.goal_x, args.goal_y,
                             math.radians(args.goal_yaw_deg))
        path = navigator.getPath(origin, final, use_start=True)
        if path is None or len(path.poses) < 2:
            raise RuntimeError("Planner nao devolveu caminho valido")

        g = Grid(
            m.info.width, m.info.height, m.info.resolution,
            m.info.origin.position.x, m.info.origin.position.y,
            yaw(m.info.origin.orientation), m.data
        )
        pts = [(p.pose.position.x, p.pose.position.y) for p in path.poses]
        plan = stage_for_path(pts, g)
        sx, sy, sa = plan["stage"]
        width = plan["estimated_width"]
        print("\n===== ALINHAMENTO ANTES DO CORREDOR =====")
        print("Entrada estimada: (%.3f, %.3f)" % plan["entrance"])
        print("Largura entre paredes: %.2f m" % width)
        print("Eixo estimado: %.2f graus" % math.degrees(sa))
        print("Ponto de alinhamento: x=%.3f y=%.3f yaw=%.2f graus" %
              (sx, sy, math.degrees(sa)))
        print("Distancia ate a entrada: %.2f m" %
              plan["distance_stage_to_entrance"])

        logdir = Path.home() / "robo_jazzy_ws/logs"
        logdir.mkdir(parents=True, exist_ok=True)
        filename = logdir / ("corridor_staging_" +
                             datetime.now().strftime("%Y%m%d_%H%M%S") +
                             ".json")
        filename.write_text(json.dumps({
            "goal": [args.goal_x, args.goal_y, args.goal_yaw_deg],
            "map_stamp": [m.header.stamp.sec, m.header.stamp.nanosec],
            "plan": plan, "executed": False
        }, indent=2))
        print("Plano salvo:", filename)

        if not args.execute_stage:
            print("MODO PREVIA: nao foi enviado nenhum comando de navegacao.")
            return

        print("\nATENCAO: esta opcao manda APENAS o Nav2 chegar ao ponto")
        print("de alinhamento, em area aberta. Nao atravessa o corredor.")
        print("Confirme no RViz que nao ha objetivo ativo, pessoas ou obstaculos.")
        if input("Digite ALINHAR para permitir a meta intermediaria: ").strip() != "ALINHAR":
            print("Cancelado pelo operador.")
            return

        navigator.goToPose(stamped_pose(navigator, sx, sy, sa))
        deadline = time.monotonic() + args.timeout
        while not navigator.isTaskComplete():
            if time.monotonic() > deadline:
                navigator.cancelTask()
                raise RuntimeError("Timeout da navegacao intermediaria: cancelada")
            time.sleep(0.1)

        if navigator.getResult() != TaskResult.SUCCEEDED:
            raise RuntimeError("Nao chegou ao ponto de alinhamento: Nav2 falhou")

        rclpy.spin_once(navigator, timeout_sec=0.2)
        actual = get_tf_pose(buffer)
        heading_error = abs(math.degrees(diff_angle(actual[2], sa)))
        distance_error = math.hypot(actual[0] - sx, actual[1] - sy)
        print("Alinhamento: erro angular %.2f graus; posicao %.2f m" %
              (heading_error, distance_error))
        if heading_error > 5.0 or distance_error > 0.08:
            raise RuntimeError("Alinhamento ainda insuficiente; nao entrar no corredor")
        print("Alinhamento intermediario concluido.")
        print("A travessia fica para uma meta supervisionada pelo RViz.")

    except Exception as ex:
        print("SEM PROGRESSAO AUTOMATICA:", ex)
        raise SystemExit(2)
    finally:
        navigator.destroy_subscription(sub)
        navigator.destroyNode()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
