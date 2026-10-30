# caddy_ai2_ros2_navigation

Paquete de navegación autónoma para el robot agrícola **Caddy AI2** (cinemática Ackermann).

**Stack:** ROS 2 Jazzy · Gazebo Harmonic · EasyNav 0.5.0 · slam_toolbox

---

## ¿Qué hace este paquete?

Permite que el robot navegue de forma autónoma dándole un destino en el mapa.
Para ello necesita tres cosas:

1. **Un mapa del entorno** — construido con SLAM (una sola vez).
2. **Saber dónde está** — localización AMCL de EasyNav (cada vez que arranca).
3. **Planificar y ejecutar la ruta** — EasyNav (siempre que navega).

---

## Conceptos básicos (para novatos)

### ¿Qué es SLAM?

SLAM significa *Simultaneous Localization And Mapping* — el robot construye
un mapa mientras se mueve, usando el LiDAR para detectar paredes y obstáculos.

> **Analogía:** es como dibujar un plano de tu casa mientras la recorres por
> primera vez con los ojos vendados, guiándote solo por el sonido del eco.

**Solo necesitas hacer SLAM una vez** (o cuando el entorno cambia).
El mapa se guarda en disco y se reutiliza siempre.

### ¿Qué es AMCL?

AMCL (*Adaptive Monte Carlo Localization*) usa el mapa guardado + el LiDAR
para estimar dónde está el robot dentro del mapa.

> **Analogía:** es como abrir los ojos en tu casa ya conocida y orientarte
> mirando los muebles para saber en qué habitación estás.

### ¿Qué es EasyNav?

EasyNav es el stack de navegación que sustituye a Nav2. Con el mapa y la posición
del robot calcula la ruta (A*) y envía comandos de velocidad (Regulated Pure Pursuit).
**No hace SLAM**: para construir el mapa se sigue usando `slam_toolbox`.

### El árbol de transformadas (TF)

Para navegar, el robot necesita saber la relación entre estos sistemas de referencia:

```
map → odom → base_footprint → base_link → sensores/ruedas
 ↑      ↑
AMCL  Odometría (controlador o EKF)
```

- `map → odom`: AMCL lo publica (corrección de deriva acumulada)
- `odom → base_footprint`: odometría de ruedas (controlador) o EKF
- El resto: robot_state_publisher (geometría fija del robot)

---

## Instalación de dependencias

EasyNav 0.5.0 se compila desde fuente dentro de este workspace (el APT de Jazzy
todavía instala la 0.4.0). Los repos viven en `src/easynav/`:

| Repo | Tag |
|---|---|
| EasyNavigation/EasyNavigation | 0.5.0 |
| EasyNavigation/easynav_plugins | 0.5.0 |
| EasyNavigation/NavMap | 0.6.0 |
| fmrico/yaets | 1.2.0 |

```bash
cd ~/ws_ros2_simulation
# Si tienes un virtualenv activo (p. ej. opencv), desactívalo: su `empy` rompe la
# generación de interfaces de ROS.
deactivate 2>/dev/null
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install \
  --cmake-args -DCMAKE_BUILD_TYPE=Release \
               -DOpenCV_DIR=/usr/lib/x86_64-linux-gnu/cmake/opencv4 \
  --packages-up-to easynav_system easynav_costmap_maps_manager \
    easynav_costmap_localizer easynav_costmap_planner \
    easynav_regulated_pp_controller easynav_diagnostic_recovery
colcon build --symlink-install --packages-select caddy_ai2_ros2_navigation
source install/setup.bash
```

> `-DOpenCV_DIR=...` evita el OpenCV con CUDA de `/usr/local`, que rompe `find_package(OpenCV)`
> en `easynav_sensors`. `navmap_tools` (necesita `python3-pyproj`) no se compila porque no se usa.

## Flujo completo paso a paso

```
PASO 1 (una sola vez)          PASO 2 (cada sesión)
─────────────────────          ──────────────────────────
slam.launch.py                 navigation.launch.py
  │                              │
  ├─ Arranca simulación          ├─ Arranca simulación
  ├─ Arranca slam_toolbox        ├─ Carga el mapa guardado
  │                              ├─ Arranca AMCL
  ├─ Teleoperás el robot         ├─ Arranca EasyNav completo
  │   (construye el mapa)        └─ Mandas goals desde RViz
  │
  └─ Guardas el mapa
      (map_saver_cli)
```

---

## PASO 1 — Construir el mapa (SLAM)

### 1.1 Lanzar la simulación con SLAM

```bash
source ~/ws_ros2_simulation/install/setup.bash
ros2 launch caddy_ai2_ros2_navigation slam.launch.py
```

Esto arranca:
- Gazebo con el mundo `navigation_test.sdf` (recinto rectangular con obstáculos)
- slam_toolbox en modo *online async* (construye el mapa en tiempo real)
- RViz para visualizar

### 1.2 Ver el mapa en RViz

En RViz, añade el topic `/map` (tipo `Map`) para ver cómo se va construyendo
el mapa mientras el robot se mueve.

### 1.3 Teleoperár el robot

En una **nueva terminal**, lanza el teleop:

```bash
source ~/ws_ros2_simulation/install/setup.bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard \
  --ros-args \
  -r /cmd_vel:=/caddy_ai2/bicycle_steering_controller/reference \
  -p stamped:=true \
  -p frame_id:=base_link
```

Controles del teclado:
- `i` — avanzar
- `,` — retroceder
- `j` / `l` — girar izquierda / derecha
- `k` — parar
- `u` / `o` — curva adelante izquierda / derecha

> **Consejo:** recorre todo el perímetro interior del mundo y pasa cerca de
> todos los obstáculos para que el LiDAR los registre bien en el mapa.

### 1.4 Guardar el mapa

Cuando el mapa en RViz se vea completo y sin huecos, guárdalo.

**Terminal nueva — guardar el mapa en formato imagen (.pgm + .yaml):**

```bash
ros2 run nav2_map_server map_saver_cli \
  -f ~/ws_ros2_simulation/src/caddy_ai2_ros2_sim/src/caddy_ai2_ros2_navigation/maps/navigation_test \
  --ros-args -r map:=/map -p map_subscribe_transient_local:=true
```

Verás el mensaje: `[map_saver]: Map saved successfully`

Se crean dos ficheros:
- `maps/navigation_test.pgm` — imagen del mapa (negro=pared, blanco=libre, gris=desconocido)
- `maps/navigation_test.yaml` — metadatos (resolución, origen del mapa)

**Guardar también el pose graph** (permite continuar el SLAM más adelante):

```bash
ros2 service call /slam_toolbox/serialize_map \
  slam_toolbox/srv/SerializePoseGraph \
  "{filename: '$(ros2 pkg prefix caddy_ai2_ros2_navigation)/share/caddy_ai2_ros2_navigation/maps/navigation_test'}"
```

### 1.5 Verificar el mapa guardado

```bash
ls -lh ~/ws_ros2_simulation/src/caddy_ai2_ros2_sim/src/caddy_ai2_ros2_navigation/maps/
```

Deberías ver:
```
navigation_test.pgm        ← imagen del mapa
navigation_test.yaml       ← metadatos
navigation_test.data       ← pose graph (binario)
navigation_test.posegraph  ← grafo de poses slam_toolbox
```

Una vez guardados, **cierra la simulación** (Ctrl+C en la terminal del launch).

---

## PASO 2 — Navegar con el mapa guardado

### 2.1 Lanzar navegación completa

```bash
source ~/ws_ros2_simulation/install/setup.bash
ros2 launch caddy_ai2_ros2_sim sim.launch.py world:=navigation_test.sdf nav:=2d
```

Por defecto carga `maps/navigation_test.yaml` del propio paquete. Esto arranca:
- Gazebo con la simulación y el EKF
- EasyNav (`system_main`): mapa de costes, AMCL, planificador A*, Regulated Pure Pursuit y recovery

Si la simulación ya está en marcha, solo EasyNav: `ros2 launch caddy_ai2_ros2_navigation navigation.launch.py`.

EasyNav publica `TwistStamped` directamente sobre
`/caddy_ai2/bicycle_steering_controller/reference`, así que ya no hace falta `twist_stamper`.

> RViz no se lanza desde este launch. Ábrelo aparte y usa `map`/`odom` como frame fijo.

### 2.2 Pose inicial

La pose inicial por defecto es `(0, 0, 0)` con desviación 0.3 m
(`localizer_node.costmap.initial_pose` en `config/easynav_params.yaml`).
Si el robot arranca en otro sitio, usa **2D Pose Estimate** en RViz (topic `/initialpose`).

### 2.3 Mandar un goal

En RViz, **2D Goal Pose** (topic `/goal_pose`):

```bash
ros2 topic pub --once /goal_pose geometry_msgs/msg/PoseStamped \
  "{header: {frame_id: map}, pose: {position: {x: 3.0, y: 2.0}, orientation: {w: 1.0}}}"
```

---

## Argumentos de los launch

### `slam.launch.py`

| Argumento | Default | Descripción |
|---|---|---|
| `namespace` | `caddy_ai2` | Namespace del robot |
| `use_sim_time` | `true` | Reloj de Gazebo |
| `world` | `navigation_test.sdf` | Mundo de Gazebo |
| `slam_params_file` | `config/slam_toolbox_params.yaml` | Configuración de SLAM |
| `include_sim` | `true` | `false` si la sim ya está corriendo |
| `autostart` | `true` | Autoactivar los nodos lifecycle |

### `navigation.launch.py`

| Argumento | Default | Descripción |
|---|---|---|
| `params_file` | `config/easynav_params.yaml` | Parámetros de EasyNav |
| `map_package` | `caddy_ai2_ros2_navigation` | Paquete cuyo `share/` contiene el mapa |
| `map_file` | `maps/navigation_test.yaml` | YAML del mapa, relativo a `map_package` |

Solo arranca EasyNav. La simulación y el EKF los lanza `caddy_ai2_ros2_sim sim.launch.py`.

---

## Verificación rápida

```bash
ros2 topic hz /map                                  # durante el SLAM
ros2 run tf2_tools view_frames                      # map → odom → base_footprint → ...
ros2 topic echo /caddy_ai2/bicycle_steering_controller/reference   # salida de EasyNav
ros2 topic echo /diagnostics                        # estado del recovery
```

---

## Limitaciones conocidas respecto a Nav2

- **El planificador no es cinemático.** `easynav_costmap_planner` es un A* sobre rejilla;
  no respeta el radio de giro mínimo (~2 m) como hacía `SmacPlannerHybrid`. Pure Pursuit suaviza
  el seguimiento (`regulated_linear_scaling_min_radius: 2.0`), pero puede haber giros cerrados.
- **Sin giro en el sitio:** `use_rotate_to_heading: false`, sin marcha atrás, y se ignora el
  yaw del goal (`yaw_goal_tolerance: 3.14`).
- **El robot es un círculo** (`robot_geometry.radius: 1.47`), no el rectángulo 2.66 × 1.23 m.
  Es conservador en pasillos estrechos.

---

## Árbol de nodos durante la navegación

```
Gazebo Harmonic
  │  SICK LMS291 scan + odometría de ruedas
  ▼
[bicycle_steering_controller] ── odom → base_footprint (TF)
  ▼
[EasyNav system_main]
  ├─ sensors_node      ← /caddy_ai2/sick_lms_291/scan
  ├─ maps_manager_node ← maps/navigation_test.yaml
  ├─ localizer_node    (AMCL, publica map → odom)
  ├─ planner_node      (A*)
  ├─ controller_node   (Regulated Pure Pursuit)
  └─ recovery_node
  │  /caddy_ai2/bicycle_steering_controller/reference (TwistStamped)
  ▼
[bicycle_steering_controller] → Gazebo
```

---

## Navegación 3D en el parking (EasyNav + Helios)

Mapas 3D de `easynav_playgrounds` (Bonxai + NavMap, multi-planta), localización NavMap AMCL,
A* sobre el NavMap y Regulated Pure Pursuit, alimentado por el Helios RS-5515.

```bash
# Todo en un launch (simulación + EKF + EasyNav 3D), sin pantalla, p. ej. en un servidor:
ros2 launch caddy_ai2_ros2_sim sim.launch.py \
  world:=parking_garage.sdf headless:=true nav:=3d

# Si prefieres separarlo: simulación primero y EasyNav 3D después
ros2 launch caddy_ai2_ros2_sim sim.launch.py world:=parking_garage.sdf headless:=true
ros2 launch caddy_ai2_ros2_navigation navigation_3d.launch.py
```

EasyNav tarda ~2 min en publicar `map -> odom` (infla el mapa Bonxai).

- **Pose inicial:** si el robot no arranca en (0, 0) o la odometría ya ha acumulado distancia
  (reinicios, teletransportes), publica `/initialpose` en `map`. Con `compute_odom_from_tf` el
  localizador supone que la odometría empieza en el origen del mapa.
- **Autoimpacto del Helios:** un `pcl_ros::CropBox` quita el cuerpo del Caddy
  (`points` → `points_filtered`); EasyNav solo consume la nube filtrada.
- **Altura libre del chasis:** `vehicle_collision_ground_clearance` en `robot_params.yaml`
  (0,20 m). Con 0 el chasis rozaba la malla del suelo y el robot se quedaba clavado.
- **RViz remoto en tu PC:** `config/zenoh/` (puente `zenoh-bridge-ros2dds` por `ssh -L 7447`) y
  `launch/remote_viz.launch.py` (nube submuestreada). Config de RViz: `rviz/navigation_3d_remote.rviz`.
- **Modelo del parking:** viene de `parking-garage-world` (GPL-3.0). Se cambió su fricción a
  isótropa (`mu = mu2 = 1.0`); el original tenía `mu2 = 0.1` con `fdir1` vertical.
