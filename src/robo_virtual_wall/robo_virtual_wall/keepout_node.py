"""Accumulate confirmed, calibrated tape observations as a Nav2 keepout mask."""
from collections import deque
import copy
import json
import math
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.time import Time
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy
from nav_msgs.msg import OccupancyGrid
from nav2_msgs.msg import CostmapFilterInfo
from std_msgs.msg import String
from std_srvs.srv import Empty
from tf2_ros import Buffer, TransformListener, TransformException
from .wall_map import WallTracker, rasterize


def rotation_matrix(q):
    values = np.array([q.x,q.y,q.z,q.w],dtype=float)
    norm = np.linalg.norm(values)
    if not np.isfinite(norm) or norm < 1e-9:
        raise ValueError('Invalid TF quaternion')
    x,y,z,w = values/norm
    return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
                     [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
                     [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])


class TapeKeepout(Node):
    def __init__(self):
        super().__init__('tape_keepout')
        defaults = dict(map_topic='/map', detections_topic='/virtual_wall/detections',
                        mask_topic='/virtual_wall/keepout_mask',
                        filter_info_topic='/virtual_wall/filter_info',
                        confirmations=3, match_tolerance_m=.08,
                        wall_half_width_m=.05, confirmation_tolerance_m=.025, min_segment_length_m=.08,
                        max_observation_age_s=.5,
                        max_walls=2000, max_map_cells=4000000)
        for key,value in defaults.items():
            self.declare_parameter(key,value)
        self.p = lambda key: self.get_parameter(key).value
        if (self.p('confirmations') < 2 or self.p('match_tolerance_m') <= 0 or
                self.p('wall_half_width_m') <= 0 or self.p('max_observation_age_s') <= 0 or
                self.p('max_walls') < 1 or self.p('max_map_cells') < 1 or
                self.p('confirmation_tolerance_m') <= 0 or self.p('min_segment_length_m') <= 0):
            raise ValueError('Invalid keepout parameters')
        self.tracker = WallTracker(self.p('confirmations'),self.p('match_tolerance_m'),
                                   self.p('max_walls'),self.p('confirmation_tolerance_m'),
                                   self.p('min_segment_length_m'))
        self.map = None
        self.last_stamp = None
        self.waiting_tf = deque()
        self.last_clock = None
        self.dirty = True
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer,self)
        qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL,
                         reliability=ReliabilityPolicy.RELIABLE)
        self.mask_pub = self.create_publisher(OccupancyGrid,self.p('mask_topic'),qos)
        self.info_pub = self.create_publisher(CostmapFilterInfo,self.p('filter_info_topic'),qos)
        self.create_subscription(OccupancyGrid,self.p('map_topic'),self.on_map,qos)
        self.create_subscription(String,self.p('detections_topic'),self.on_detections,10)
        self.create_service(Empty,'~/clear',self.clear)
        self.create_timer(.2,self.publish)
        self.create_timer(.02,self.retry_waiting_tf)
        self.get_logger().info('Keepout waiting for /map and validated base_link observations. '
                               'Confirmed walls persist until ~/clear or node restart.')

    def clear(self, request, response):
        self.tracker.walls.clear()
        self.tracker.pending.clear()
        self.waiting_tf.clear()
        self.dirty = True
        self.get_logger().info('Tape walls cleared')
        self.publish()
        return response

    def on_map(self, message):
        info = message.info
        if (not message.header.frame_id or info.width*info.height > self.p('max_map_cells') or
                min(info.width,info.height,info.resolution) <= 0 or
                not math.isfinite(info.resolution)):
            self.get_logger().warning('Invalid or oversized map ignored',throttle_duration_sec=5.)
            return
        try:
            rotation_matrix(info.origin.orientation)
        except ValueError:
            return
        if not all(math.isfinite(v) for v in [info.origin.position.x,info.origin.position.y]):
            return
        if self.map and self.map.header.frame_id != message.header.frame_id:
            self.tracker.walls.clear()
            self.tracker.pending.clear()
        changed = (self.map is None or self.map.info != info or
                   self.map.header.frame_id != message.header.frame_id)
        self.map = message
        self.dirty |= changed

    def on_detections(self, message):
        # Retry at the exact image timestamp after TF callbacks have run.
        # Never substitute latest TF or block the single-thread executor.
        if self.waiting_tf:
            if len(self.waiting_tf) >= 16:
                self.waiting_tf.popleft()
                self.tracker.pending.clear()
            self.waiting_tf.append(message)
        elif not self.process_detection(message):
            self.waiting_tf.append(message)

    def retry_waiting_tf(self):
        while self.waiting_tf:
            if not self.process_detection(self.waiting_tf[0]):
                break
            self.waiting_tf.popleft()

    def process_detection(self, message):
        if self.map is None:
            return True
        now = self.get_clock().now().nanoseconds*1e-9
        if self.last_clock is not None and now < self.last_clock:
            self.tracker.pending.clear()
            self.last_stamp = None
        self.last_clock = now
        try:
            data = json.loads(message.data)
            if data.get('metric_frame') != 'base_link':
                self.tracker.pending.clear()
                self.get_logger().warning('No validated base_link calibration; tape mask remains '
                                           'unchanged', throttle_duration_sec=10.)
                return True
            sec,nanosec = data['stamp']['sec'],data['stamp']['nanosec']
            if type(sec) is not int or type(nanosec) is not int or not 0 <= nanosec < 1000000000:
                raise ValueError('Invalid image timestamp')
            stamp = sec+nanosec*1e-9
            if not 0 <= now-stamp <= self.p('max_observation_age_s'):
                self.tracker.pending.clear()
                return True
            if self.last_stamp is not None:
                if stamp <= self.last_stamp:
                    return True
                if stamp-self.last_stamp > self.p('max_observation_age_s'):
                    self.tracker.pending.clear()
            segments = []
            for entry in data['detections']:
                if 'base_link_m' not in entry:
                    continue
                points = np.asarray(entry['base_link_m'],dtype=float)
                if points.shape != (2,2) or not np.isfinite(points).all():
                    raise ValueError('Invalid metric tape segment')
                segments.append(points)
            if segments:
                transform = self.tf_buffer.lookup_transform(self.map.header.frame_id,'base_link',
                                    Time(seconds=sec,nanoseconds=nanosec))
                rotation = rotation_matrix(transform.transform.rotation)
                t = transform.transform.translation
                translation = np.array([t.x,t.y,t.z])
                segments = [(np.column_stack((points,np.zeros(2))) @ rotation.T +
                             translation)[:,:2] for points in segments]
            self.last_stamp = stamp
            added = self.tracker.update(segments)
            self.dirty |= added
            if added:
                self.get_logger().info('Tape walls confirmed in map: %d' % len(self.tracker.walls),
                                       throttle_duration_sec=1.)
            if len(self.tracker.walls) >= self.p('max_walls'):
                self.get_logger().warning('Tape wall capacity reached; clear/review mask',
                                           throttle_duration_sec=10.)
        except TransformException as error:
            self.get_logger().warning('Waiting for image-time TF: '+str(error),
                                       throttle_duration_sec=5.)
            return False
        except (ValueError,TypeError,KeyError) as error:
            self.tracker.pending.clear()
            self.get_logger().warning('Tape observation rejected: '+str(error),
                                       throttle_duration_sec=5.)

        return True

    def publish(self):
        if self.map is None or not self.dirty:
            return
        mask = OccupancyGrid()
        mask.header.frame_id = self.map.header.frame_id
        mask.header.stamp = self.get_clock().now().to_msg()
        mask.info = copy.deepcopy(self.map.info)
        o = mask.info.origin
        q = o.orientation
        yaw = math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z))
        grid = rasterize(self.tracker.walls,mask.info.width,mask.info.height,
                         mask.info.resolution,(o.position.x,o.position.y,yaw),
                         self.p('wall_half_width_m'))
        mask.data = grid.ravel().tolist()
        info = CostmapFilterInfo()
        info.header = mask.header
        info.type,info.base,info.multiplier = 0,0.,1.
        info.filter_mask_topic = self.p('mask_topic')
        self.info_pub.publish(info)
        self.mask_pub.publish(mask)
        self.dirty = False


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = TapeKeepout()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.try_shutdown()
