/**
 * {{PACK_TITLE}}（{{PACK_NAME}}）—— 浏览器半（Client）
 *
 * 加载契约：`window.__ModuleLoader__.load({ id, factory(require) { ... } })`
 *   ⚠ `id` 必须是 **manifest 包名**（`{{PACK_NAME}}`），不是能力清单 id（`{{PACK_ID}}`）。
 *   写成短 id 的话：工作台能看到入口，但点「打开」没反应（工厂挂不到模块上）。
 * 主面板：`ctx.slots.inject('main', () => ctx.slots.register({ name:'main', key: ENTRY_KEY }, Comp))`。
 * 只用 `React.createElement`，无 JSX；不引三方库。
 * 前端半改动只需刷新页面；宿主半（index.js）改动必须重启 DSH。
 */

window.__ModuleLoader__.load({
  id: '{{PACK_NAME}}',
  factory(require) {
    const React = require('react');
    const h = React.createElement;
    const { useState, useEffect } = React;

    const API = '/api/{{PACK_ID}}';
    const ENTRY_KEY = '{{PACK_ENTRY_KEY}}';
    const OPEN_EVENT = '{{PACK_OPEN_EVENT}}';
    const STYLE_ID = '{{PACK_ID}}-styles';

    async function requestJson(path, options) {
      const res = await fetch(API + path, {
        headers: { 'content-type': 'application/json' },
        ...options,
      });
      const text = await res.text();
      let data = null;
      try {
        data = text ? JSON.parse(text) : null;
      } catch {
        data = { raw: text };
      }
      if (!res.ok) {
        const hint = data && (data.hint || data.error) ? data.hint || data.error : '';
        throw new Error(`HTTP ${res.status} ${path}${hint ? `（${hint}）` : ''}`);
      }
      return data;
    }

    function App() {
      const [health, setHealth] = useState(null);
      const [error, setError] = useState('');
      const [pingResult, setPingResult] = useState('');

      useEffect(() => {
        requestJson('/health')
          .then((data) => setHealth(data))
          .catch((err) => setError(err.message));
      }, []);

      async function onPing() {
        setPingResult('请求中…');
        try {
          const data = await requestJson('/ping', {
            method: 'POST',
            body: JSON.stringify({ text: 'hello from ' + ENTRY_KEY }),
          });
          setPingResult(JSON.stringify(data));
        } catch (err) {
          setPingResult(`失败：${err.message}`);
        }
      }

      return h(
        'div',
        { className: 'cpk-root' },
        h('h2', { className: 'cpk-title' }, '{{PACK_ICON}} {{PACK_TITLE}}'),
        h(
          'p',
          { className: 'cpk-desc' },
          '能力包骨架已就位：改 index.js / client.js 实现业务，保持 health 与 404 契约不变。',
        ),
        error ? h('p', { className: 'cpk-error' }, `健康检查失败：${error}`) : null,
        h(
          'p',
          { className: 'cpk-meta' },
          health
            ? `host v${String(health.version || '?').replace(/^v/, '')} ｜ entryKey ${health.entryKey || ENTRY_KEY}`
            : '正在检查宿主半…',
        ),
        h(
          'button',
          { type: 'button', className: 'cpk-btn', onClick: onPing },
          '测试 /ping',
        ),
        pingResult ? h('pre', { className: 'cpk-out' }, pingResult) : null,
      );
    }

    function EntryIcon() {
      return h('span', { className: 'cpk-side-icon', title: '{{PACK_TITLE}}' }, '{{PACK_ICON}}');
    }

    const CSS = [
      '.cpk-root{padding:18px;font:14px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif;color:#1f2328}',
      '.cpk-title{margin:0 0 8px;font-size:18px}',
      '.cpk-desc{margin:0 0 10px;color:#57606a}',
      '.cpk-meta{margin:0 0 12px;color:#1a7f37}',
      '.cpk-error{margin:0 0 12px;color:#cf222e}',
      '.cpk-btn{padding:6px 14px;border:1px solid #d0d7de;border-radius:6px;background:#f6f8fa;cursor:pointer}',
      '.cpk-btn:hover{background:#eef1f4}',
      '.cpk-out{margin:12px 0 0;padding:10px;background:#f6f8fa;border-radius:6px;overflow:auto;max-height:180px}',
      '.cpk-side-icon{font-size:16px}',
    ].join('\n');

    function ensureStyle(doc) {
      if (!doc || !doc.head || doc.getElementById(STYLE_ID)) return;
      const style = doc.createElement('style');
      style.id = STYLE_ID;
      style.textContent = CSS;
      doc.head.appendChild(style);
    }

    return {
      inject: ['slots', 'layout'],
      apply(ctx) {
        const cleanups = [];
        try {
          ensureStyle(typeof document !== 'undefined' ? document : null);
        } catch {
          /* 无 DOM 环境 */
        }
        const slots = ctx && (ctx.slots || (typeof ctx.get === 'function' ? ctx.get('slots') : null));
        if (slots && typeof slots.inject === 'function' && typeof slots.register === 'function') {
          cleanups.push(slots.inject('main', () => slots.register({ name: 'main', key: ENTRY_KEY }, () => h(App))));
          try {
            cleanups.push(
              slots.inject('sidebar.panellist', () =>
                slots.register(
                  { name: 'sidebar.panellist', id: ENTRY_KEY, order: {{PACK_ORDER}}, label: '{{PACK_TITLE}}' },
                  EntryIcon,
                ),
              ),
            );
          } catch {
            /* 侧栏入口注册失败不影响主面板 */
          }
        }
        const layout = (ctx && (ctx.layout || (typeof ctx.get === 'function' ? ctx.get('layout') : null))) || null;
        function openPanel() {
          try {
            if (layout && typeof layout.selectPanel === 'function') layout.selectPanel(ENTRY_KEY);
          } catch {
            /* 面板不可用时忽略 */
          }
        }
        try {
          if (typeof window !== 'undefined' && window.addEventListener) {
            window.addEventListener(OPEN_EVENT, openPanel);
            cleanups.push(() => window.removeEventListener(OPEN_EVENT, openPanel));
          }
        } catch {
          /* 事件注册失败忽略 */
        }
        return () => {
          for (const cleanup of cleanups.reverse()) {
            try {
              if (typeof cleanup === 'function') cleanup();
            } catch {
              /* 尽力卸载 */
            }
          }
          cleanups.length = 0;
        };
      },
      __test: { entryKey: ENTRY_KEY, api: API, openEvent: OPEN_EVENT },
    };
  },
});
