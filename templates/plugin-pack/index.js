/**
 * {{PACK_TITLE}}（{{PACK_NAME}}）—— 宿主半（Host）
 *
 * 这是能力包骨架，`init --kind plugin` 已把占位符替换成你的项目值。
 * 契约要点（改之前先读 `ops/dsh-plugin-dev.md`）：
 *   - 路由只占 `/api/<短id>` 子前缀，**不要**占用 `/api/workbench`；
 *   - `GET /api/<短id>/health` 必须返回 `{ ok, id, version, entryKey, routes }`，
 *     `version` 与 `package.json` 的 version 一致（版本握手靠它）；
 *   - 未知路由返回结构化 404（含 method / path / hint）；
 *   - 宿主半改动后**必须重启 DSH** 才生效（ESM 不热替换），前端半刷新即可。
 */

export const VERSION = '{{PACK_VERSION}}';
export const API_PREFIX = '/api/{{PACK_ID}}';

/** 能力包清单（CAPABILITY-PACK-API v1.0）。 */
export const MANIFEST = {
  id: '{{PACK_ID}}',
  title: '{{PACK_TITLE}}',
  description: '{{PACK_DESC}}',
  entryKey: '{{PACK_ENTRY_KEY}}',
  order: {{PACK_ORDER}},
  icon: '{{PACK_ICON}}',
  category: '{{PACK_CATEGORY}}',
  version: `v${VERSION}`,
  tags: ['{{PACK_TITLE}}'],
  subs: [],
  openEvent: '{{PACK_OPEN_EVENT}}',
  openEventAliases: ['{{PACK_OPEN_EVENT}}'],
};

const MAX_BODY_BYTES = 256 * 1024;

/* ------------------------------------------------------------------ */
/* HTTP 工具                                                           */
/* ------------------------------------------------------------------ */

function sendJson(res, status, obj) {
  const body = JSON.stringify(obj);
  if (res && typeof res.setHeader === 'function') {
    res.setHeader('content-type', 'application/json; charset=utf-8');
    res.setHeader('content-length', Buffer.byteLength(body));
    res.setHeader('cache-control', 'no-store');
  }
  if (res && typeof res.writeHead === 'function') res.writeHead(status);
  res.end(body);
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let size = 0;
    req.on('data', (chunk) => {
      size += chunk.length;
      if (size > MAX_BODY_BYTES) {
        reject(new Error('BODY_TOO_LARGE'));
        req.destroy();
        return;
      }
      chunks.push(chunk);
    });
    req.on('end', () => resolve(Buffer.concat(chunks).toString('utf8')));
    req.on('error', reject);
  });
}

/**
 * 处理 `/api/{{PACK_ID}}/*`。
 * @param {object} req
 * @param {object} res
 * @param {object} [ctx] 宿主上下文；需要模型能力时用 `ctx.get('llm')`（每次请求现取，不缓存）
 */
export async function handleRequest(req, res, ctx) {
  let url;
  try {
    url = new URL(req.url || '/', 'http://127.0.0.1');
  } catch {
    sendJson(res, 400, { error: 'BAD_REQUEST', hint: 'url 无法解析' });
    return;
  }
  const pathname = url.pathname;
  const method = String(req.method || 'GET').toUpperCase();
  if (pathname !== API_PREFIX && !pathname.startsWith(`${API_PREFIX}/`)) {
    // 结构化 404：带 method / path / hint，别写裸 NOT FOUND
    sendJson(res, 404, { error: 'NOT_FOUND', method, path: pathname, hint: `本包路由前缀是 ${API_PREFIX}` });
    return;
  }
  const route = pathname.slice(API_PREFIX.length) || '/';

  try {
    if ((route === '/' || route === '/health') && method === 'GET') {
      sendJson(res, 200, {
        ok: true,
        id: MANIFEST.id,
        version: MANIFEST.version,
        entryKey: MANIFEST.entryKey,
        routes: ['GET /health', 'GET /info', 'POST /ping'],
      });
      return;
    }

    if (route === '/info' && method === 'GET') {
      sendJson(res, 200, {
        ok: true,
        manifest: MANIFEST,
        usage: `POST ${API_PREFIX}/ping  body: {"text":"..."} → 原样回显`,
      });
      return;
    }

    if (route === '/ping' && method === 'POST') {
      let payload;
      try {
        payload = JSON.parse(await readBody(req));
      } catch (err) {
        sendJson(res, 400, {
          error: 'BAD_REQUEST',
          method,
          path: pathname,
          hint: `body 必须是 JSON${err && err.message === 'BODY_TOO_LARGE' ? '（且不超过 256KB）' : ''}`,
        });
        return;
      }
      // 模型能力是软依赖：取不到就降级，不要 500
      const llm = ctx && typeof ctx.get === 'function' ? ctx.get('llm') : null;
      sendJson(res, 200, {
        ok: true,
        echo: payload && typeof payload.text === 'string' ? payload.text : null,
        engine: llm ? 'llm' : 'rule-fallback',
      });
      return;
    }

    sendJson(res, 404, {
      error: 'NOT_FOUND',
      method,
      path: pathname,
      hint: `可用路由见 GET ${API_PREFIX}/health 的 routes 字段`,
    });
  } catch (err) {
    sendJson(res, 500, {
      error: 'INTERNAL',
      method,
      path: pathname,
      hint: err && err.message ? String(err.message) : String(err),
    });
  }
}

/* ------------------------------------------------------------------ */
/* 插件入口                                                            */
/* ------------------------------------------------------------------ */

export const inject = ['webServer'];

export function apply(ctx, _config) {
  const disposers = [];

  // 1. HTTP 子前缀路由（不占用 /api/workbench）
  try {
    const ws = (ctx && ctx.webServer) || (ctx && typeof ctx.get === 'function' ? ctx.get('webServer') : null);
    if (ws && typeof ws.register === 'function') {
      disposers.push(
        ws.register({
          kind: 'prefix',
          path: API_PREFIX,
          handler(req, res) {
            return handleRequest(req, res, ctx).catch((err) => {
              try {
                sendJson(res, 500, { error: 'INTERNAL', hint: err && err.message ? String(err.message) : String(err) });
              } catch {
                /* res 已关闭 */
              }
            });
          },
        }),
      );
    }
  } catch {
    /* webServer 不可用时仅保留 UI */
  }

  // 2. 向工作台注册能力清单（冷启动可能稍晚就绪：150ms × 最多 20 次；服务缺失不崩）
  try {
    let capabilities = null;
    let tries = 0;
    const register = () => {
      try {
        capabilities = ctx && typeof ctx.get === 'function' ? ctx.get('workbenchCapabilities') : null;
      } catch {
        capabilities = null;
      }
      if (capabilities && typeof capabilities.register === 'function') {
        try {
          capabilities.register(MANIFEST);
        } catch {
          return false;
        }
        disposers.push(() => {
          try {
            if (typeof capabilities.unregister === 'function') capabilities.unregister(MANIFEST.id);
          } catch {
            /* 注销失败不影响卸载 */
          }
        });
        return true;
      }
      return false;
    };
    if (!register()) {
      const timer = setInterval(() => {
        tries += 1;
        if (register() || tries >= 20) clearInterval(timer);
      }, 150);
      if (timer && typeof timer.unref === 'function') timer.unref();
      disposers.push(() => clearInterval(timer));
    }
  } catch {
    /* workbenchCapabilities 不可用时不影响 HTTP 半 */
  }

  return () => {
    for (const dispose of disposers.reverse()) {
      try {
        if (typeof dispose === 'function') dispose();
      } catch {
        /* 尽力卸载 */
      }
    }
    disposers.length = 0;
  };
}
