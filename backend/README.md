# Backend de Hormiguero Vivo

API en FastAPI que expone la simulación híbrida ABM + SD. En la fase 1 el motor es un modelo simulado que respeta el contrato completo, de modo que el frontend puede trabajar contra datos plausibles mientras se implementa el modelo real.

## Ejecución

Desde `backend/`, usando el entorno del directorio superior:

```powershell
..\..\.venv\Scripts\python.exe -m uvicorn hormiguero.main:app --app-dir src --reload
..\..\.venv\Scripts\python.exe -m pytest
cd src; ..\..\..\.venv\Scripts\python.exe -m hormiguero.export_openapi
```

La documentación interactiva queda en `http://localhost:8000/docs`. El último comando regenera `contract/openapi.json`, que el frontend usa para generar sus tipos con `openapi-typescript`. Los orígenes permitidos por CORS se configuran con la variable `HORMIGUERO_CORS_ORIGINS`, separados por comas; por defecto se permite `http://localhost:5173`.

## Contrato

Todas las rutas viven bajo `/api/v1`. Los errores siempre tienen la forma `{"error": {"code", "message", "details"}}`: 404 para recursos inexistentes, 409 para conflictos de estado y 422 para validaciones.

| Grupo | Rutas |
|---|---|
| Meta | `GET /health`, `GET /parameters/schema`, `GET /catalog`, `GET /scenarios`, `GET /ws/schema` |
| Simulaciones | `POST/GET /simulations`, `GET/DELETE /simulations/{id}`, `POST /control`, `GET/PATCH /parameters`, `GET /state` |
| Datos | `GET /fields/{layer}`, `GET /history`, `GET /metrics/summary`, `GET /export` |
| Mundo | `POST /world/obstacles`, `POST /world/food`, `POST /predators`, `DELETE /predators/{pid}` |
| Perturbaciones | `POST/GET /events`, `GET/PATCH/DELETE /events/{eid}` |

`GET /catalog` entrega etiquetas y unidades para cada serie del historial, cada capa, cada perturbación y cada estado de los agentes. `GET /parameters/schema` incluye límites, paso sugerido y restricciones entre parámetros para construir los controles.

### Ciclo de vida

`created → running ⇄ paused → finished`.

- `start` y `step` se permiten en `created` y `paused`. También en `finished` si terminó por `max_ticks` y luego se aumentó `run.max_ticks`.
- `set_speed` cambia la velocidad en cualquier estado.
- `reset` vuelve a `created`; acepta una nueva `seed` y `keep_obstacles` para conservar el mapa dibujado.
- Los parámetros con `live_editable = false` solo se cambian en `created`.
- Las perturbaciones solo se editan con `PATCH` mientras están en `scheduled`.

### Historial

El historial guarda hasta 20 000 muestras. Cuando se llena, conserva una de cada dos y duplica `resolution`, de modo que siempre cubre la corrida completa desde el tick 0.

### WebSocket `/api/v1/ws/simulations/{id}`

Cada mensaje del servidor tiene la forma `{seq, tick, sim_time, type, payload}`:

- `init`: información, configuración, mundo estático, suscripción y perturbaciones. Se envía al conectar y tras un reset.
- `status`: estado y velocidad.
- `config`: configuración completa tras cada cambio de parámetros.
- `frame`: hormigas y depredadores en arreglos paralelos, stocks y flujos del nido y métricas. `role` y `state` de las hormigas son índices en `ant_roles` y `ant_states` del catálogo. También se envía tras cada edición del mundo, aunque la simulación esté en pausa.
- `field`: una capa de la cuadrícula codificada en `uint8` base64. El valor real es `byte / 255 * scale`, y `scale` es el máximo histórico de la capa, estable entre envíos.
- `event`: avisos de perturbaciones con la perturbación completa, comandos aplicados y fin de la simulación.
- `error` y `pong`.

`seq` es consecutivo por conexión. Si un cliente lento llena su cola, el servidor descarta primero `frame` y `field`; un salto en `seq` indica que se perdieron mensajes y el cliente debe pedir `GET /state`.

El cliente envía `{"type": "subscribe", "payload": {layers, frame_every, field_every, field_downsample}}` para elegir capas y frecuencia, y `{"type": "ping"}` para mantener viva la conexión. Si la conexión se pierde, el cliente pide `GET /state` y vuelve a conectarse.

Las rutas y el WebSocket se definen como `async` porque la simulación avanza en el mismo ciclo de eventos. Así un comando nunca se aplica a mitad de un tick.
