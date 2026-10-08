# Frontend de Hormiguero Vivo

Interfaz en React que muestra la simulación en vivo. El mundo ocupa el centro de la pantalla y los controles quedan a un clic: barra superior, paleta de herramientas, cajón lateral con Nido, Gráficas y Parámetros, y línea de eventos inferior.

## Ejecución

Desde `frontend/`, con el backend corriendo en `http://localhost:8000`:

```powershell
npm install
npm run dev
```

El servidor de Vite redirige `/api` y el WebSocket al backend, así que no hace falta configurar CORS. Para otro destino se define `HORMIGUERO_API_URL`.

| Comando | Uso |
|---|---|
| `npm run gen:api` | Regenera `src/api/schema.d.ts` desde `contract/openapi.json` |
| `npm run build` | Compila con TypeScript y Vite |
| `npm run lint` | Revisa el código con oxlint |
| `npm test` | Ejecuta las pruebas con Vitest |

## Estructura

- `src/api`: tipos generados, cliente REST, consultas de TanStack Query y cliente WebSocket con reconexión.
- `src/sim`: store de Zustand, decodificador de capas e historial en vivo.
- `src/world`: escena de PixiJS que dibuja el mundo.
- `src/components`: paneles y controles de la interfaz.
