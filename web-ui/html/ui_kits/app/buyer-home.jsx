// MeliSim — Buyer Home (real API)

function ProdCard({ p, onAddToCart }) {
  const [h, setH] = React.useState(false);
  const [adding, setAdding] = React.useState(false);
  const free = p.price >= 299;
  const lowStock = p.stock > 0 && p.stock <= 5;
  const installments = p.price > 800 ? 12 : 6;
  const stars = 4 + Math.round(((p.id * 13) % 9) / 10) / 10; // pseudo-rating from id
  const reviews = 50 + ((p.id * 37) % 800);

  const add = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    setAdding(true);
    MeliSim.cart.add(p, 1);
    setTimeout(() => setAdding(false), 350);
  };

  return (
    <a href={`11-buyer-search.html?view=product&id=${p.id}`}
      onMouseEnter={() => setH(true)} onMouseLeave={() => setH(false)}
      style={{ textDecoration: 'none', color: 'inherit', background: C.white, borderRadius: 4, boxShadow: h ? '0 4px 12px rgba(0,0,0,0.16)' : '0 1px 4px rgba(0,0,0,0.10)', cursor: 'pointer', overflow: 'hidden', transition: 'all 150ms', transform: h ? 'translateY(-2px)' : 'none', position: 'relative', display: 'block' }}>
      <div style={{ position: 'relative', background: C.gray50, height: 160, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 56 }}>
        {productIcon(p)}
        {free && <span style={{ position: 'absolute', top: 8, left: 8, background: C.success, color: C.white, fontSize: 10, fontWeight: 700, padding: '2px 6px', borderRadius: 3 }}>FRETE GRÁTIS</span>}
        {lowStock && <span style={{ position: 'absolute', top: 8, right: 8, background: C.warning, color: C.white, fontSize: 10, fontWeight: 700, padding: '2px 6px', borderRadius: 3 }}>Últimas {p.stock}!</span>}
        {p.stock === 0 && <span style={{ position: 'absolute', top: 8, right: 8, background: C.danger, color: C.white, fontSize: 10, fontWeight: 700, padding: '2px 6px', borderRadius: 3 }}>Esgotado</span>}
      </div>
      <div style={{ padding: '10px 12px' }}>
        <div style={{ fontSize: 13, color: C.gray800, lineHeight: 1.4, height: 36, overflow: 'hidden', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}>{p.title}</div>
        <div style={{ fontSize: 22, fontWeight: 300, color: C.gray800, marginTop: 6 }}>R$ {Number(p.price).toLocaleString('pt-BR')}</div>
        <div style={{ fontSize: 11, color: C.success, fontWeight: 600 }}>{installments}x R$ {(p.price / installments).toFixed(0)} sem juros</div>
        <div style={{ fontSize: 11, color: C.warning, marginTop: 3 }}>{'★'.repeat(Math.floor(stars))}{'☆'.repeat(5 - Math.floor(stars))} <span style={{ color: C.gray400 }}>({reviews})</span></div>
        {p.stock > 0 && (
          <button type="button" onClick={add}
            style={{ marginTop: 8, width: '100%', padding: '6px', border: `1px solid ${C.action}`, background: adding ? C.success : C.actionLt, color: adding ? C.white : C.action, borderRadius: 4, cursor: 'pointer', fontSize: 12, fontWeight: 700, fontFamily: T.sans, transition: 'all 200ms' }}>
            {adding ? '✓ Adicionado' : 'Adicionar ao carrinho'}
          </button>
        )}
      </div>
    </a>
  );
}

function BuyerHome() {
  const { data, loading, error, reload } = useApi(() => MeliSim.listProducts({ size: 20 }), []);
  const [b, setB] = React.useState(0);
  const banners = [
    { bg: '#2D3277', color: '#FFE600', title: 'Ofertas Imperdíveis', sub: 'Até 50% em eletrônicos', icon: '⚡' },
    { bg: '#FFE600', color: '#2D3277', title: 'Frete Grátis', sub: 'Em milhares de produtos acima de R$ 299', icon: '🚚' },
    { bg: '#00A650', color: '#fff', title: 'iPhone 15 Pro', sub: '12x sem juros', icon: '📱' },
  ];
  React.useEffect(() => { const t = setInterval(() => setB(x => (x + 1) % 3), 4000); return () => clearInterval(t); }, []);
  const bn = banners[b];

  const products = data?.items || [];

  return (
    <div style={{ minHeight: '100vh', background: C.pageBg }}>
      <div style={{ background: bn.bg, padding: '40px 32px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', transition: 'background 0.5s', position: 'relative', minHeight: 200 }}>
        <div>
          <div style={{ fontSize: 38, fontWeight: 800, color: bn.color, letterSpacing: '-0.02em' }}>{bn.title}</div>
          <div style={{ fontSize: 18, color: bn.color, opacity: 0.85, marginTop: 8 }}>{bn.sub}</div>
          <a href="11-buyer-search.html" style={{ display: 'inline-block', marginTop: 18, background: bn.color, color: bn.bg, border: 'none', padding: '12px 26px', borderRadius: 6, fontWeight: 800, fontSize: 15, fontFamily: T.sans, cursor: 'pointer', textDecoration: 'none' }}>Comprar agora</a>
        </div>
        <div style={{ fontSize: 96, opacity: 0.9 }}>{bn.icon}</div>
        <div style={{ position: 'absolute', bottom: 14, left: '50%', transform: 'translateX(-50%)', display: 'flex', gap: 6 }}>
          {banners.map((_, i) => <div key={i} onClick={() => setB(i)} style={{ width: i === b ? 22 : 8, height: 8, borderRadius: 4, background: i === b ? bn.color : 'rgba(255,255,255,0.4)', cursor: 'pointer', transition: 'width 0.3s' }} />)}
        </div>
      </div>

      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '24px 16px' }}>
        {loading && <Loading label="Carregando catálogo do products-service…" height={400} />}
        {error && <ErrorState error={error} onRetry={reload} height={400} />}
        {!loading && !error && products.length === 0 && (
          <EmptyState icon="📦" title="Catálogo vazio" description="Nenhum produto cadastrado no products-service ainda. Cadastre via API ou rode test.sh." />
        )}
        {!loading && !error && products.length > 0 && (
          <>
            {[
              { title: '🔥 Mais Vendidos', items: products.slice(0, 4) },
              { title: '⚡ Ofertas do Dia', items: products.slice(4, 8) },
              { title: '📱 Eletrônicos em Destaque', items: products.filter(p => p.category === 'electronics').slice(0, 4) },
              { title: '🏠 Para sua casa', items: products.filter(p => p.category === 'home').slice(0, 4) },
            ].filter(s => s.items.length > 0).map(s => (
              <div key={s.title} style={{ marginBottom: 32 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
                  <h2 style={{ fontSize: 20, fontWeight: 800, color: C.blue }}>{s.title}</h2>
                  <a href="11-buyer-search.html" style={{ fontSize: 13, color: C.action, fontWeight: 600, textDecoration: 'none' }}>Ver todos →</a>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12 }}>
                  {s.items.map(p => <ProdCard key={p.id} p={p} />)}
                </div>
              </div>
            ))}
          </>
        )}
      </div>
    </div>
  );
}

Object.assign(window, { ProdCard, BuyerHome });
