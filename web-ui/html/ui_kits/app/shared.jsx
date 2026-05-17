// MeliSim Design System — Shared Components
// All real API calls go through window.MeliSim (see api.js).

const C = {
  yellow: '#FFE600', yellowDk: '#F0D900',
  blue: '#2D3277', blueDk: '#1E2255', blueLt: '#3D4591',
  action: '#3483FA', actionDk: '#2968C8', actionLt: '#EBF4FF',
  success: '#00A650', successBg: '#E8F7EF',
  danger: '#F23D4F', dangerBg: '#FEE8EA',
  warning: '#F2A900', warningBg: '#FFF3E0',
  gray900: '#1A1A1A', gray800: '#333', gray700: '#4D4D4D',
  gray600: '#666', gray500: '#808080', gray400: '#999',
  gray300: '#CCC', gray200: '#E0E0E0', gray100: '#EBEBEB',
  gray50: '#F5F5F5', white: '#fff',
  pageBg: '#EBEBEB',
};

const T = { sans: "'Nunito Sans', system-ui, sans-serif", mono: "'JetBrains Mono', monospace" };

/* ── React data-fetching helpers ─────────────────────────────────────── */

// Subscribe a component to localStorage cart changes so the badge stays in sync.
function useCartCount() {
  const [n, setN] = React.useState(() => MeliSim.cart.count());
  React.useEffect(() => {
    const sync = () => setN(MeliSim.cart.count());
    window.addEventListener('melisim:cart-changed', sync);
    window.addEventListener('storage', sync);
    return () => {
      window.removeEventListener('melisim:cart-changed', sync);
      window.removeEventListener('storage', sync);
    };
  }, []);
  return n;
}

// Fetch a value from the API. Returns { data, loading, error, reload }.
// Pass deps array to refetch when they change.
function useApi(fn, deps = []) {
  const [state, setState] = React.useState({ data: null, loading: true, error: null });
  const reload = React.useCallback(() => {
    let cancelled = false;
    setState(s => ({ ...s, loading: true, error: null }));
    Promise.resolve(fn())
      .then(d => { if (!cancelled) setState({ data: d, loading: false, error: null }); })
      .catch(e => { if (!cancelled) setState({ data: null, loading: false, error: e }); });
    return () => { cancelled = true; };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  React.useEffect(() => reload(), [reload]);
  return { ...state, reload };
}

/* ── Logo + Brand ────────────────────────────────────────────────────── */

function Logo({ size = 22 }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
      <div style={{
        background: C.yellow, borderRadius: 8, width: size * 1.8, height: size * 1.8,
        display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0
      }}>
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
          <path d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4z" stroke={C.blue} strokeWidth="2" fill="none"/>
          <line x1="3" y1="6" x2="21" y2="6" stroke={C.blue} strokeWidth="2"/>
          <path d="M16 10a4 4 0 01-8 0" stroke={C.blue} strokeWidth="2" strokeLinecap="round"/>
        </svg>
      </div>
      <span style={{ fontSize: size, fontWeight: 800, color: C.blue, letterSpacing: '-0.02em' }}>MeliSim</span>
    </div>
  );
}

/* ── Top Header ──────────────────────────────────────────────────────── */

function Header({ onNav, currentPersona, notifCount = 0 }) {
  const [q, setQ] = React.useState('');
  const cartCount = useCartCount();
  const user = MeliSim.getUser();
  const avatarLetter = (user?.name || '?').charAt(0).toUpperCase();

  const submitSearch = (e) => {
    e?.preventDefault?.();
    const url = `11-buyer-search.html?q=${encodeURIComponent(q)}`;
    window.location.href = url;
  };

  const goLogin = () => { window.location.href = '01-login.html'; };

  return (
    <div style={{ position: 'sticky', top: 0, zIndex: 100 }}>
      {/* Top bar */}
      <div style={{ background: C.yellow, padding: '10px 24px', display: 'flex', alignItems: 'center', gap: 16 }}>
        <a href="10-buyer-home.html" style={{ textDecoration: 'none' }}><Logo size={20} /></a>
        <form onSubmit={submitSearch} style={{ flex: 1, display: 'flex', border: '1px solid #E5E5E5', borderRadius: 4, overflow: 'hidden', maxWidth: 600, background: C.white }}>
          <select style={{ padding: '8px 10px', border: 'none', borderRight: '1px solid #E5E5E5', fontSize: 12, fontFamily: T.sans, color: C.gray600, background: C.white, outline: 'none' }}>
            <option>Todas</option><option>electronics</option><option>computers</option><option>home</option><option>fashion</option><option>games</option><option>audio</option>
          </select>
          <input value={q} onChange={e => setQ(e.target.value)} placeholder="Buscar produtos, marcas e mais…"
            style={{ flex: 1, padding: '8px 12px', border: 'none', fontSize: 14, fontFamily: T.sans, outline: 'none' }} />
          <button type="submit" style={{ background: C.blue, color: C.white, border: 'none', padding: '0 16px', cursor: 'pointer', fontSize: 18 }}>⌕</button>
        </form>
        <div style={{ display: 'flex', gap: 20, alignItems: 'center' }}>
          <a href="12-buyer-cart.html" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', cursor: 'pointer', position: 'relative', textDecoration: 'none' }}>
            <span style={{ fontSize: 20 }}>🛒</span>
            {cartCount > 0 && <span style={{ position: 'absolute', top: -4, right: -6, background: C.danger, color: C.white, borderRadius: '50%', minWidth: 16, height: 16, fontSize: 10, display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, padding: '0 4px' }}>{cartCount}</span>}
            <span style={{ fontSize: 10, color: C.blue, fontWeight: 600 }}>Carrinho</span>
          </a>
          <a href="15-buyer-notifications.html" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', cursor: 'pointer', position: 'relative', textDecoration: 'none' }}>
            <span style={{ fontSize: 20 }}>🔔</span>
            {notifCount > 0 && <span style={{ position: 'absolute', top: -4, right: -6, background: C.danger, color: C.white, borderRadius: '50%', minWidth: 16, height: 16, fontSize: 10, display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, padding: '0 4px' }}>{notifCount}</span>}
            <span style={{ fontSize: 10, color: C.blue, fontWeight: 600 }}>Avisos</span>
          </a>
          {user ? (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
              <a href="16-buyer-profile.html" style={{ width: 32, height: 32, borderRadius: '50%', background: C.blue, color: C.yellow, display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: 13, cursor: 'pointer', textDecoration: 'none' }}>{avatarLetter}</a>
              <span style={{ fontSize: 10, color: C.blue, fontWeight: 600 }}>{user.name?.split(' ')[0] || 'Você'}</span>
            </div>
          ) : (
            <button onClick={goLogin} style={{ background: C.blue, color: C.white, border: 'none', padding: '8px 16px', borderRadius: 4, fontSize: 13, fontWeight: 700, cursor: 'pointer', fontFamily: T.sans }}>Entrar</button>
          )}
        </div>
      </div>
      {/* Category bar */}
      <div style={{ background: C.blue, padding: '0 24px', display: 'flex', gap: 2, overflowX: 'auto' }}>
        {[['Eletrônicos','electronics'],['Computadores','computers'],['Casa','home'],['Moda','fashion'],['Esportes','sports'],['Games','games'],['Áudio','audio'],['Livros','books'],['Escritório','office']].map(([label, cat]) => (
          <a key={cat} href={`11-buyer-search.html?category=${cat}`}
            style={{ color: C.white, fontSize: 12, padding: '8px 12px', cursor: 'pointer', whiteSpace: 'nowrap', opacity: 0.85, borderRadius: 2, textDecoration: 'none' }}
            onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,230,0,0.15)'; e.currentTarget.style.opacity = 1; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.opacity = 0.85; }}>
            {label}
          </a>
        ))}
      </div>
    </div>
  );
}

/* ── Sidebar (authenticated views) ───────────────────────────────────── */

function Sidebar({ persona, active, onNav, variant }) {
  const isSre = variant === 'sre';
  const menus = {
    buyer: [
      { icon: '🏠', label: 'Início', screen: 'home', href: '10-buyer-home.html' },
      { icon: '🛍', label: 'Meus Pedidos', screen: 'orders', href: '14-buyer-orders.html' },
      { icon: '🔔', label: 'Notificações', screen: 'notifications', href: '15-buyer-notifications.html' },
      { icon: '👤', label: 'Perfil', screen: 'profile', href: '16-buyer-profile.html' },
    ],
    seller: [
      { icon: '⊞', label: 'Dashboard', screen: 'seller-dashboard', href: '20-seller-dashboard.html' },
      { icon: '📦', label: 'Produtos', screen: 'seller-products' },
      { icon: '🛍', label: 'Vendas', screen: 'seller-sales' },
      { icon: '📊', label: 'Estoque', screen: 'seller-inventory' },
    ],
    admin: [
      { icon: '⊞', label: 'Overview', screen: 'admin-overview' },
      { icon: '🔧', label: 'Services', screen: 'admin-services' },
      { icon: '📤', label: 'Outbox', screen: 'admin-outbox' },
      { icon: '💀', label: 'DLQ', screen: 'admin-dlq' },
      { icon: '⚡', label: 'Kafka', screen: 'admin-kafka' },
    ],
  };

  const user = MeliSim.getUser();
  const av = {
    letter: (user?.name || persona[0]).charAt(0).toUpperCase(),
    name: user?.name || persona,
    role: user?.userType === 'ADMIN' ? 'Administrador' : user?.userType === 'SELLER' ? 'Vendedor ⭐' : user?.userType === 'BUYER' ? 'Comprador' : '—',
  };

  const sbBg = isSre ? '#1a2340' : C.white;
  const sbShadow = isSre ? 'none' : '0 1px 4px rgba(0,0,0,0.10)';
  const sbBorder = isSre ? 'rgba(255,255,255,0.08)' : C.gray100;
  const txtMuted = isSre ? 'rgba(232,234,239,0.65)' : C.gray500;
  const txtMain = isSre ? '#e8eaef' : C.gray800;
  const navInactive = isSre ? 'rgba(232,234,239,0.82)' : C.gray700;
  const navActiveBg = isSre ? 'rgba(255,255,255,0.08)' : C.gray50;
  const navHoverBg = isSre ? 'rgba(255,255,255,0.06)' : C.gray50;
  const accentActive = isSre ? '#5c9cff' : C.blue;

  return (
    <div style={{
      width: isSre ? 248 : 220,
      flexShrink: 0,
      background: sbBg,
      boxShadow: sbShadow,
      display: 'flex',
      flexDirection: 'column',
      minHeight: isSre ? '100vh' : 'calc(100vh - 96px)',
    }}>
      <div style={{ padding: '20px 16px', borderBottom: `1px solid ${sbBorder}` }}>
        <div style={{
          width: 44,
          height: 44,
          borderRadius: '50%',
          background: isSre ? '#2D3277' : C.blue,
          color: isSre ? C.white : C.yellow,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontWeight: 800,
          fontSize: 18,
          marginBottom: 8,
          border: isSre ? '2px solid rgba(255,255,255,0.15)' : 'none',
        }}>{av.letter}</div>
        <div style={{ fontWeight: 700, fontSize: 14, color: txtMain }}>{av.name}</div>
        <div style={{ fontSize: 11, color: txtMuted, marginTop: 2 }}>{isSre && user?.userType === 'ADMIN' ? 'Admin · SRE' : av.role}</div>
      </div>
      <nav style={{ padding: '8px 0', flex: 1 }}>
        {menus[persona].map(({ icon, label, screen, href }) => {
          const activeRow = active === screen;
          const itemEl = (
            <div onClick={() => !href && onNav && onNav(screen)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                padding: '10px 16px',
                fontSize: 14,
                color: activeRow ? accentActive : navInactive,
                fontWeight: activeRow ? 700 : 400,
                background: activeRow ? navActiveBg : 'transparent',
                cursor: 'pointer',
                position: 'relative',
                transition: 'background 150ms',
                textDecoration: 'none',
              }}
              onMouseEnter={e => { if (!activeRow) e.currentTarget.style.background = navHoverBg; }}
              onMouseLeave={e => { if (!activeRow) e.currentTarget.style.background = 'transparent'; }}>
              {activeRow && <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: 3, background: C.yellow, borderRadius: '0 2px 2px 0' }} />}
              <span style={{ fontSize: 16, width: 20, textAlign: 'center' }}>{icon}</span>
              {label}
            </div>
          );
          return href
            ? <a key={screen} href={href} style={{ textDecoration: 'none', color: 'inherit' }}>{itemEl}</a>
            : <React.Fragment key={screen}>{itemEl}</React.Fragment>;
        })}
        <div onClick={() => MeliSim.logout()}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            padding: '10px 16px',
            fontSize: 14,
            color: txtMuted,
            cursor: 'pointer',
            borderTop: `1px solid ${sbBorder}`,
            marginTop: 12,
          }}
          onMouseEnter={e => { e.currentTarget.style.background = navHoverBg; }}
          onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}>
          <span style={{ fontSize: 16, width: 20, textAlign: 'center' }}>↪</span>
          Sair
        </div>
      </nav>
    </div>
  );
}

/* ── Buttons / Cards / Badges ────────────────────────────────────────── */

function Btn({ children, variant = 'primary', size = 'md', disabled, loading, onClick, type = 'button', style: sx }) {
  const sizes = { sm: { padding: '6px 12px', fontSize: 12 }, md: { padding: '10px 20px', fontSize: 14 }, lg: { padding: '13px 28px', fontSize: 16 } };
  const variants = {
    primary: { background: C.yellow, color: C.blue, border: 'none' },
    secondary: { background: 'transparent', color: C.blue, border: `2px solid ${C.blue}` },
    ghost: { background: 'transparent', color: C.action, border: 'none' },
    danger: { background: C.danger, color: C.white, border: 'none' },
  };
  const s = sizes[size]; const v = variants[variant];
  return (
    <button type={type} onClick={!disabled && !loading ? onClick : undefined}
      style={{ fontFamily: T.sans, fontWeight: 700, borderRadius: 6, cursor: disabled || loading ? 'not-allowed' : 'pointer', transition: 'all 150ms', opacity: disabled ? 0.4 : 1, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 6, ...s, ...v, ...sx }}
      onMouseEnter={e => { if (!disabled && !loading && variant === 'primary') e.currentTarget.style.background = C.yellowDk; }}
      onMouseLeave={e => { if (variant === 'primary') e.currentTarget.style.background = C.yellow; }}>
      {loading ? <span style={{ display: 'inline-block', width: 14, height: 14, border: `2px solid ${v.color}`, borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 0.7s linear infinite' }} /> : children}
    </button>
  );
}

function Badge({ children, color = C.action, bg = C.actionLt, pill = false }) {
  return <span style={{ display: 'inline-flex', alignItems: 'center', padding: '3px 10px', borderRadius: pill ? 999 : 4, fontSize: 11, fontWeight: 700, color, background: bg, whiteSpace: 'nowrap' }}>{children}</span>;
}

function OrderBadge({ status }) {
  const map = {
    CREATED: { label: 'Criado', color: C.action, bg: C.actionLt },
    PAYMENT_PENDING: { label: 'Aguard. Pagto', color: '#b37800', bg: C.warningBg },
    PAID: { label: 'Pago', color: C.success, bg: C.successBg },
    SHIPPED: { label: 'Enviado', color: C.actionDk, bg: '#D6E8FF' },
    DELIVERED: { label: 'Entregue', color: C.yellow, bg: C.blue },
    CANCELLED: { label: 'Cancelado', color: C.danger, bg: C.dangerBg },
  };
  const m = map[status] || map.CREATED;
  return <Badge color={m.color} bg={m.bg}>{m.label}</Badge>;
}

function Card({ children, style: sx, hover = true }) {
  const [hov, setHov] = React.useState(false);
  return (
    <div onMouseEnter={() => hover && setHov(true)} onMouseLeave={() => setHov(false)}
      style={{ background: C.white, borderRadius: 4, boxShadow: hov ? '0 4px 12px rgba(0,0,0,0.14)' : '0 1px 4px rgba(0,0,0,0.10)', transition: 'box-shadow 150ms, transform 150ms', transform: hov ? 'translateY(-2px)' : 'none', ...sx }}>
      {children}
    </div>
  );
}

function MetricCard({ label, value, sub, trend, color = C.blue }) {
  const up = trend >= 0;
  return (
    <Card style={{ padding: 20, flex: 1 }}>
      <div style={{ fontSize: 12, color: C.gray500, marginBottom: 6, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</div>
      <div style={{ fontSize: 28, fontWeight: 800, color, lineHeight: 1.1, marginBottom: 4 }}>{value}</div>
      {sub && <div style={{ fontSize: 12, color: C.gray500 }}>{sub}</div>}
      {trend !== undefined && (
        <div style={{ fontSize: 11, color: up ? C.success : C.danger, fontWeight: 700, marginTop: 6, display: 'flex', alignItems: 'center', gap: 3 }}>
          {up ? '↑' : '↓'} {Math.abs(trend)}% vs ontem
        </div>
      )}
    </Card>
  );
}

function Sparkline({ data, color = C.action, width = 80, height = 30 }) {
  if (!data || data.length < 2) return <svg width={width} height={height} />;
  const max = Math.max(...data); const min = Math.min(...data);
  const range = max - min || 1;
  const pts = data.map((v, i) => `${(i / (data.length - 1)) * width},${height - ((v - min) / range) * (height - 4) - 2}`).join(' ');
  return (
    <svg width={width} height={height} style={{ display: 'block' }}>
      <polyline fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" points={pts} />
    </svg>
  );
}

function Toast({ message, type = 'success', onClose }) {
  const colors = { success: C.success, error: C.danger, warning: C.warning, info: C.action };
  React.useEffect(() => { const t = setTimeout(onClose, 4000); return () => clearTimeout(t); }, []);
  return (
    <div style={{ position: 'fixed', top: 20, right: 20, background: C.white, borderRadius: 6, boxShadow: '0 4px 16px rgba(0,0,0,0.18)', padding: '14px 20px', display: 'flex', alignItems: 'center', gap: 12, zIndex: 9999, maxWidth: 320, borderLeft: `4px solid ${colors[type]}`, animation: 'slideIn 0.2s ease' }}>
      <span style={{ fontSize: 18 }}>{type === 'success' ? '✓' : type === 'error' ? '✕' : type === 'warning' ? '⚠' : 'ℹ'}</span>
      <span style={{ fontSize: 14, color: C.gray800, flex: 1 }}>{message}</span>
      <span onClick={onClose} style={{ cursor: 'pointer', color: C.gray400, fontSize: 16 }}>✕</span>
    </div>
  );
}

/* ── Async-state helpers ─────────────────────────────────────────────── */

function Loading({ label = 'Carregando…', height = 200 }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: height, gap: 12, color: C.gray500 }}>
      <div style={{ width: 36, height: 36, border: `3px solid ${C.gray200}`, borderTopColor: C.action, borderRadius: '50%', animation: 'spin 0.7s linear infinite' }} />
      <div style={{ fontSize: 13 }}>{label}</div>
    </div>
  );
}

function ErrorState({ error, onRetry, height = 200 }) {
  const msg = error?.message || String(error || 'Erro desconhecido');
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: height, gap: 12, color: C.gray700, textAlign: 'center', padding: 24 }}>
      <div style={{ fontSize: 40, opacity: 0.5 }}>⚠</div>
      <div style={{ fontSize: 16, fontWeight: 700 }}>Não foi possível carregar</div>
      <div style={{ fontSize: 13, color: C.gray500, maxWidth: 380 }}>{msg}</div>
      {onRetry && <Btn variant="secondary" size="sm" onClick={onRetry}>Tentar novamente</Btn>}
    </div>
  );
}

function EmptyState({ icon = '🗒', title, description, cta }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: 240, gap: 10, color: C.gray700, textAlign: 'center', padding: 32 }}>
      <div style={{ fontSize: 56, opacity: 0.4 }}>{icon}</div>
      <div style={{ fontSize: 18, fontWeight: 700 }}>{title}</div>
      {description && <div style={{ fontSize: 13, color: C.gray500, maxWidth: 380 }}>{description}</div>}
      {cta}
    </div>
  );
}

/* Generic product icon based on category — replaces the hardcoded emojis. */
function productIcon(p) {
  const c = (p?.category || '').toLowerCase();
  const t = (p?.title || '').toLowerCase();
  if (/iphone|galaxy|smartphone|celular/.test(t)) return '📱';
  if (/macbook|notebook|laptop/.test(t)) return '💻';
  if (/headphone|headset|fone/.test(t)) return '🎧';
  if (/playstation|ps5|xbox|game/.test(t)) return '🎮';
  if (/tv\b|smart tv|televis/.test(t)) return '📺';
  if (/watch/.test(t)) return '⌚';
  if (/kindle|livro/.test(t)) return '📚';
  if (/cadeira|chair/.test(t)) return '🪑';
  if (/teclado|keyboard/.test(t)) return '⌨️';
  if (/mouse/.test(t)) return '🖱️';
  if (/monitor/.test(t)) return '🖥️';
  if (/aspirador|roomba/.test(t)) return '🤖';
  if (/fryer|cafeteira|micro/.test(t)) return '🍳';
  if (/tênis|tenis|sapato|nike/.test(t)) return '👟';
  if (c === 'electronics') return '📦';
  if (c === 'computers') return '💻';
  if (c === 'audio') return '🎧';
  if (c === 'games') return '🎮';
  if (c === 'home') return '🏠';
  if (c === 'fashion') return '👕';
  return '🛍';
}

Object.assign(window, {
  C, T, Logo, Header, Sidebar, Btn, Badge, OrderBadge, Card, MetricCard,
  Sparkline, Toast, Loading, ErrorState, EmptyState, useApi, useCartCount, productIcon,
});
