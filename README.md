# caddy_ai2_ros2_navigation

Paquete de navegación autónoma para el robot agrícola **Caddy AI2** (cinemática Ackermann).

**Stack:** ROS 2 Jazzy · Gazebo Harmonic · Nav2 · slam_toolbox

---

## ¿Qué hace este paquete?

Permite que el robot navegue de forma autónoma dándole un destino en el mapa.
Para ello necesita tres cosas:

1. **Un mapa del entorno** — construido con SLAM (una sola vez).
2. **Saber dónde está** — localización con AMCL (cada vez que arranca).
3. **Planificar y ejecutar la ruta** — Nav2 (siempre que navega).

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

### ¿Qué es Nav2?

Nav2 es el stack de navegación de ROS 2. Con el mapa y la posición del robot,
calcula la ruta óptima hasta el destino y envía comandos de velocidad al robot.

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

```bash
sudo apt install ros-jazzy-twist-stamper
```

Compilar el paquete:

```bash
cd ~/ws_ros2_simulation
colcon build --packages-select caddy_ai2_ros2_navigation
source install/setup.bash
```

---

## Flujo completo paso a paso

```
PASO 1 (una sola vez)          PASO 2 (cada sesión)
─────────────────────          ──────────────────────────
slam.launch.py                 navigation.launch.py
  │                              │
  ├─ Arranca simulación          ├─ Arranca simulación
  ├─ Arranca slam_toolbox        ├─ Carga el mapa guardado
  │                              ├─ Arranca AMCL
  ├─ Teleoperás el robot         ├─ Arranca Nav2 completo
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
ros2 launch caddy_ai2_ros2_navigation navigation.launch.py \
  map:=$(ros2 pkg prefix caddy_ai2_ros2_navigation)/share/caddy_ai2_ros2_navigation/maps/navigation_test.yaml
```

Esto arranca:
- Gazebo con la simulación
- AMCL (localización con el mapa cargado)
- Nav2 completo (planificador + controlador)
- twist_stamper (adapta los comandos de Nav2 al controlador del robot)
- RViz con el panel de navegación

### 2.2 Dar la pose inicial al robot en RViz

AMCL necesita una estimación inicial de dónde está el robot en el mapa.

1. En RViz, haz clic en **"2D Pose Estimate"** (barra superior)
2. Haz clic en el mapa donde está el robot y arrastra en la dirección a la que mira
3. Verás las partículas de AMCL (flechas) converger alrededor del robot

> Si el robot arranca siempre en la misma posición (origen del mapa), puedes
> saltarte este paso — AMCL convergerá solo en unos segundos.

### 2.3 Mandar un goal de navegación

1. En RViz, haz clic en **"Nav2 Goal"** (o **"2D Nav Goal"**)
2. Haz clic en el mapa donde quieres que vaya el robot y arrastra para indicar la orientación final
3. Nav2 calculará la ruta y el robot empezará a moverse

Puedes ver la ruta planificada en RViz como una línea verde.

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
| `namespace` | `caddy_ai2` | Namespace del robot |
| `use_sim_time` | `true` | Reloj de Gazebo |
| `map` | *(vacío)* | **Ruta completa al .yaml del mapa** |
| `use_slam` | `false` | `true` = SLAM simultáneo en lugar de AMCL |
| `params_file` | `config/nav2_params.yaml` | Parámetros de Nav2 |
| `include_sim` | `true` | `false` si la sim ya está corriendo |
| `use_localization` | `true` | `false` = sin EKF (odometría directa) |

---

## Verificación rápida

```bash
# ¿Se está publicando el mapa?
ros2 topic hz /map

# ¿AMCL está publicando la TF map→odom?
ros2 run tf2_tools view_frames
# Debe aparecer: map → odom → base_footprint → ...

# ¿Nav2 está activo?
ros2 topic echo /caddy_ai2/plan --once
```

---

## Árbol de nodos durante la navegación

```
Gazebo Harmonic
  │  SICK LMS291 scan + odometría de ruedas
  ▼
[bicycle_steering_controller] ── odom → base_footprint (TF)
  │  /caddy_ai2/bicycle_steering_controller/odometry
  ▼
[AMCL] ← mapa cargado + /caddy_ai2/sick_lms_291/scan
  │  map → odom (TF)
  ▼
[Nav2: SmacPlannerHybrid + MPPI Controller]
  │  /caddy_ai2/cmd_vel (Twist)
  ▼
[twist_stamper]
  │  /caddy_ai2/bicycle_steering_controller/reference (TwistStamped)
  ▼
[bicycle_steering_controller] → Gazebo
```
