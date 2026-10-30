-- Cartographer 2D SLAM configuration — Caddy AI2 (Ackermann robot)
-- LiDAR: SICK LMS291 → /caddy_ai2/sick_lms_291/scan
-- Odometry: bicycle_steering_controller → /caddy_ai2/bicycle_steering_controller/odometry

include "map_builder.lua"
include "trajectory_builder.lua"

options = {
  map_builder            = MAP_BUILDER,
  trajectory_builder     = TRAJECTORY_BUILDER,

  -- Frames
  map_frame              = "map",
  tracking_frame         = "base_footprint",
  -- published_frame = "odom" → Cartographer publishes map→odom
  -- The controller already handles odom→base_footprint
  published_frame        = "odom",
  odom_frame             = "odom",
  provide_odom_frame     = false,
  publish_frame_projected_to_2d = true,

  use_pose_extrapolator  = true,
  use_odometry           = true,   -- wheel odometry from controller
  use_nav_sat            = false,
  use_landmarks          = false,

  -- One standard 2D laser scan (SICK LMS291)
  num_laser_scans               = 1,
  num_multi_echo_laser_scans    = 0,
  num_subdivisions_per_laser_scan = 1,
  num_point_clouds              = 0,

  -- Timing
  lookup_transform_timeout_sec   = 0.2,
  submap_publish_period_sec      = 0.3,
  pose_publish_period_sec        = 5e-3,
  trajectory_publish_period_sec  = 30e-3,

  -- Sampling ratios (1 = use every message)
  rangefinder_sampling_ratio         = 1.,
  odometry_sampling_ratio            = 1.,
  fixed_frame_pose_sampling_ratio    = 1.,
  imu_sampling_ratio                 = 1.,
  landmarks_sampling_ratio           = 1.,
}

-- 2D mode
MAP_BUILDER.use_trajectory_builder_2d = true

-- Local SLAM (trajectory builder)
TRAJECTORY_BUILDER_2D.submaps.num_range_data      = 35
TRAJECTORY_BUILDER_2D.min_range                   = 0.3
TRAJECTORY_BUILDER_2D.max_range                   = 20.0   -- SICK LMS291 max range
TRAJECTORY_BUILDER_2D.missing_data_ray_length      = 1.0
TRAJECTORY_BUILDER_2D.use_imu_data                = false  -- IMU not needed for 2D

-- Real-time scan matching (improves accuracy at the cost of CPU)
TRAJECTORY_BUILDER_2D.use_online_correlative_scan_matching               = true
TRAJECTORY_BUILDER_2D.real_time_correlative_scan_matcher.linear_search_window   = 0.1
TRAJECTORY_BUILDER_2D.real_time_correlative_scan_matcher.translation_delta_cost_weight = 10.
TRAJECTORY_BUILDER_2D.real_time_correlative_scan_matcher.rotation_delta_cost_weight    = 1e-1

-- Global SLAM (loop closure / pose graph)
POSE_GRAPH.optimize_every_n_nodes           = 35
POSE_GRAPH.constraint_builder.min_score     = 0.65
POSE_GRAPH.optimization_problem.huber_scale = 1e2

return options
