# Backend de Hormiguero Vivo

API en FastAPI que expone la simulación híbrida ABM + SD. En la fase 1 el motor es un modelo simulado que respeta el contrato completo, de modo que el frontend puede trabajar contra datos plausibles mientras se implementa el modelo real.

## Ejecución

Desde `backend/`, usando el entorno del directorio superior:

```powershell
..\..\.venv\Scripts\python.exe -m uvicorn hormiguero.main:app --app-dir src --reload
..\..\.venv\Scripts\python.exe -m pytest
cd src; ..\..\..\.venv\Scripts\python.exe -m hormiguero.export_openapi
```

La documentación interactiva queda en `http://localhost:8000/docs`. El último comando regenera `contract/openapi.json`, que el frontend usa para generar sus tipos con `openapi-typescript`.

## Contrato

Todas las rutas viven bajo `/api/v1`. Los errores siempre tienen la forma `{"error": {"code", "message", "details"}}`: 404 para recursos inexistentes, 409 para conflictos de estado y 422 para validaciones.

| Grupo | Rutas |
|---|---|
| Meta | `GET /health`, `GET /parameters/schema`, `GET /scenarios`, `GET /ws/schema` |
| Simulaciones | `POST/GET /simulations`, `GET/DELETE /simulations/{id}`, `POST /control`, `GET/PATCH /parameters`, `GET /state` |
| Datos | `GET /fields/{layer}`, `GET /history`, `GET /metrics/summary`, `GET /export` |
| Mundo | `POST /world/obstacles`, `POST /world/food`, `POST /predators`, `DELETE /predators/{pid}` |
| Perturbaciones | `POST/GET /events`, `GET/DELETE /events/{eid}` |

### Ciclo de vida

`created → running ⇄ paused → finished`. `step` solo se permite en `created` o `paused`. `reset` vuelve a `created` desde cualquier estado. Los parámetros con `live_editable = false` solo se cambian en `created`.

### WebSocket `/api/v1/ws/simulations/{id}`

Cada mensaje del servidor tiene la forma `{type, tick, sim_time, payload}`:

- `init`: información, configuración, mundo estático, suscripción y perturbaciones. Se envía al conectar y tras un reset.
- `status`: estado y velocidad.
- `frame`: hormigas y depredadores en arreglos paralelos, stocks y flujos del nido y métricas.
- `field`: una capa de la cuadrícula codificada en `uint8` base64. El valor real es `byte / 255 * scale`.
- `event`: avisos de perturbaciones, comandos aplicados y fin de la simulación.
- `error` y `pong`.

El cliente envía `{"type": "subscribe", "payload": {layers, frame_every, field_every, field_downsample}}` para elegir capas y frecuencia, y `{"type": "ping"}` para mantener viva la conexión. Si la conexión se pierde, el cliente pide `GET /state` y vuelve a conectarse.

Las rutas y el WebSocket se definen como `async` porque la simulación avanza en el mismo ciclo de eventos. Así un comando nunca se aplica a mitad de un tick.
